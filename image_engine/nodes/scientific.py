import os
import cv2
import numpy as np
import tempfile
import scipy.ndimage as ndimage
from typing import Dict, Any
from skimage.restoration import denoise_wavelet

from image_engine.nodes.base import BaseNode
from image_engine.nodes.bit_depth import (
    clip_to_input_dtype,
    normalize_to_uint8,
    scale_unit_to_dtype,
)
from app.core.storage import download_image


class NonLocalMeansNode(BaseNode):
    """
    Smooths images based on patch similarity using Non-Local Means (NLM) denoising.
    """

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        image = inputs.get("input_image")
        if image is None:
            raise ValueError("NonLocalMeansNode requires 'input_image' input.")

        h = float(params.get("h", 3.0))
        template_window_size = int(params.get("template_window_size", 7))
        search_window_size = int(params.get("search_window_size", 21))

        # Ensure window sizes are odd
        if template_window_size % 2 == 0:
            template_window_size += 1
        if search_window_size % 2 == 0:
            search_window_size += 1

        working = image if image.dtype == np.uint8 else normalize_to_uint8(image)

        if len(working.shape) == 2:
            denoised = cv2.fastNlMeansDenoising(
                working,
                None,
                h=h,
                templateWindowSize=template_window_size,
                searchWindowSize=search_window_size,
            )
        elif len(working.shape) == 3:
            channels = working.shape[2]
            if channels == 3:
                denoised = cv2.fastNlMeansDenoisingColored(
                    working,
                    None,
                    h=h,
                    hColor=h,
                    templateWindowSize=template_window_size,
                    searchWindowSize=search_window_size,
                )
            elif channels == 4:
                # Separate BGR and alpha
                bgr = cv2.cvtColor(working, cv2.COLOR_BGRA2BGR)
                alpha = working[:, :, 3]
                denoised_bgr = cv2.fastNlMeansDenoisingColored(
                    bgr,
                    None,
                    h=h,
                    hColor=h,
                    templateWindowSize=template_window_size,
                    searchWindowSize=search_window_size,
                )
                denoised = cv2.merge([denoised_bgr, alpha])
            else:
                raise ValueError(f"Unsupported channel size in NLM: {channels}")
        else:
            raise ValueError("Invalid image dimensions.")

        if image.dtype == np.uint8:
            return {"output_image": denoised}

        return {
            "output_image": scale_unit_to_dtype(denoised.astype(float) / 255.0, image)
        }


class HomomorphicFilterNode(BaseNode):
    """
    Frequency domain filter that separates illumination and
    reflectance to correct lighting.
    """

    def _filter_channel(
        self, img: np.ndarray, gl: float, gh: float, d0: float
    ) -> np.ndarray:
        # Log transform to separate illumination and reflectance
        img_log = np.log1p(img.astype(float))

        # FFT
        rows, cols = img.shape
        img_fft = np.fft.fft2(img_log)
        img_fft_shift = np.fft.fftshift(img_fft)

        # Gaussian High-Pass Filter mask
        u = np.arange(rows) - rows / 2
        v = np.arange(cols) - cols / 2
        U, V = np.meshgrid(u, v, indexing="ij")
        D2 = U**2 + V**2

        # H(u,v) = (gh - gl) * (1 - exp(-D2 / (2 * D0^2))) + gl
        H = (gh - gl) * (1.0 - np.exp(-D2 / (2.0 * (d0**2)))) + gl

        # Apply filter in shift frequency domain
        filtered_fft_shift = img_fft_shift * H

        # Inverse FFT
        filtered_fft = np.fft.ifftshift(filtered_fft_shift)
        filtered_log = np.fft.ifft2(filtered_fft)
        filtered_log = np.real(filtered_log)

        # Exponentiate back
        filtered = np.expm1(filtered_log)

        return filtered

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        image = inputs.get("input_image")
        if image is None:
            raise ValueError("HomomorphicFilterNode requires 'input_image' input.")

        gl = float(params.get("low_frequency_gain", 0.5))
        gh = float(params.get("high_frequency_gain", 1.5))
        d0 = float(params.get("cutoff_frequency", 30.0))

        if len(image.shape) == 2:
            filtered = clip_to_input_dtype(
                self._filter_channel(image, gl, gh, d0), image
            )
        elif len(image.shape) == 3:
            channels = []
            for c in range(image.shape[2]):
                channel = image[:, :, c]
                channels.append(
                    clip_to_input_dtype(
                        self._filter_channel(channel, gl, gh, d0), channel
                    )
                )
            filtered = cv2.merge(channels)
        else:
            raise ValueError("Invalid image dimensions.")

        return {"output_image": filtered}


class WaveletDenoisingNode(BaseNode):
    """Multiscale image denoising using discrete wavelet transform (DWT)."""

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        image = inputs.get("input_image")
        if image is None:
            raise ValueError("WaveletDenoisingNode requires 'input_image' input.")

        wavelet = str(params.get("wavelet", "db1"))
        mode = str(params.get("mode", "soft"))

        # skimage's denoise_wavelet expects floats [0, 1]
        img_float = normalize_to_uint8(image).astype(float) / 255.0
        channel_axis = -1 if len(image.shape) == 3 else None

        denoised = denoise_wavelet(
            img_float,
            wavelet=wavelet,
            mode=mode,
            channel_axis=channel_axis,
            rescale_sigma=True,
        )

        if image.dtype == np.uint8:
            return {"output_image": np.clip(denoised * 255.0, 0, 255).astype(np.uint8)}

        return {"output_image": scale_unit_to_dtype(denoised, image)}


class FlatFieldCorrectionNode(BaseNode):
    """Corrects uneven sensor sensitivity using flat and dark calibration frames."""

    def _read_frame(
        self, key_or_url: str, default_val: float, shape: tuple[int, ...]
    ) -> np.ndarray:
        if not key_or_url:
            return np.ones(shape) * default_val

        # Create temporary file to download image
        fd, temp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        try:
            is_url = key_or_url.startswith("http://") or key_or_url.startswith(
                "https://"
            )
            download_image(key_or_url, temp_path, is_presigned_url=is_url)
            img = cv2.imread(temp_path, cv2.IMREAD_UNCHANGED)
            if img is None:
                raise ValueError(
                    f"Could not load flat-field calibration image: {key_or_url}"
                )
            # Ensure shape matches
            if img.shape[:2] != shape[:2]:
                img = cv2.resize(img, (shape[1], shape[0]))
            return img.astype(float)
        except Exception as e:
            raise ValueError(
                f"Flat-Field Correction failed to read frame '{key_or_url}': {str(e)}"
            )
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        image = inputs.get("input_image")
        if image is None:
            raise ValueError("FlatFieldCorrectionNode requires 'input_image' input.")

        img_float = image.astype(float)

        dark_image = inputs.get("dark_field_image")
        if dark_image is not None:
            dark_float = dark_image.astype(float)
            # Ensure shape matches
            if dark_float.shape[:2] != image.shape[:2]:
                dark_float = cv2.resize(dark_float, (image.shape[1], image.shape[0]))
        else:
            dark_key = params.get("dark_field_key", "")
            dark_float = self._read_frame(dark_key, 0.0, image.shape)

        flat_image = inputs.get("flat_field_image")
        if flat_image is not None:
            flat_float = flat_image.astype(float)
            # Ensure shape matches
            if flat_float.shape[:2] != image.shape[:2]:
                flat_float = cv2.resize(flat_float, (image.shape[1], image.shape[0]))
        else:
            flat_key = params.get("flat_field_key", "")
            flat_float = self._read_frame(flat_key, 255.0, image.shape)

        # C = (img_float - dark_float) / (flat_float - dark_float)
        # * mean(flat_float - dark_float)
        diff_F_D = flat_float - dark_float
        diff_F_D[diff_F_D == 0] = 1e-5  # avoid division by zero

        diff_I_D = img_float - dark_float
        mean_diff = np.mean(diff_F_D)

        corrected_float = (diff_I_D / diff_F_D) * mean_diff
        corrected = clip_to_input_dtype(corrected_float, image)

        return {"output_image": corrected}


class CameraCalibrationNode(BaseNode):
    """Corrects lens distortion using camera matrix files (.npz)."""

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        image = inputs.get("input_image")
        if image is None:
            raise ValueError("CameraCalibrationNode requires 'input_image' input.")

        cal_key = params.get("calibration_file_key", "")
        if not cal_key:
            # Bypass calibration if key is empty
            return {"output_image": image}

        fd, temp_path = tempfile.mkstemp(suffix=".npz")
        os.close(fd)
        try:
            is_url = cal_key.startswith("http://") or cal_key.startswith("https://")
            download_image(cal_key, temp_path, is_presigned_url=is_url)

            with np.load(temp_path) as data:
                # Load camera matrix
                if "mtx" in data:
                    mtx = data["mtx"]
                elif "camera_matrix" in data:
                    mtx = data["camera_matrix"]
                else:
                    raise KeyError(
                        "Camera matrix (mtx/camera_matrix) "
                        "not found in calibration file."
                    )

                # Load distortion coefficients
                if "dist" in data:
                    dist = data["dist"]
                elif "dist_coefs" in data:
                    dist = data["dist_coefs"]
                else:
                    raise KeyError(
                        "Distortion coefficients (dist/dist_coefs) "
                        "not found in calibration file."
                    )

            h, w = image.shape[:2]
            newcameramtx, _ = cv2.getOptimalNewCameraMatrix(
                mtx, dist, (w, h), 1, (w, h)
            )
            undistorted = cv2.undistort(image, mtx, dist, None, newcameramtx)
            return {"output_image": undistorted}
        except Exception as e:
            raise ValueError(f"Camera Calibration failed: {str(e)}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class FABEMDNode(BaseNode):
    """Fast Adaptive Bi-dimensional Empirical Mode Decomposition."""

    def _decompose_channel(self, residue: np.ndarray, num_imfs: int) -> np.ndarray:
        current = residue.astype(float)
        imfs = []

        for i in range(num_imfs):
            window_size = 3 + 2 * i  # odd sizes: 3, 5, 7...
            upper = ndimage.maximum_filter(current, size=window_size)
            lower = ndimage.minimum_filter(current, size=window_size)
            mean_env = (upper + lower) / 2.0

            imf = current - mean_env
            imfs.append(imf)
            current = mean_env

        # Return first IMF scaled to 0..1
        first_imf = imfs[0]
        f_min = np.min(first_imf)
        f_max = np.max(first_imf)
        if f_max > f_min:
            out = (first_imf - f_min) / (f_max - f_min)
        else:
            out = np.zeros_like(first_imf)
        return out  # type: ignore[no-any-return]

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        image = inputs.get("input_image")
        if image is None:
            raise ValueError("FABEMDNode requires 'input_image' input.")

        num_imfs = int(params.get("num_imfs", 2))

        if len(image.shape) == 2:
            decomposed = scale_unit_to_dtype(
                self._decompose_channel(image, num_imfs), image
            )
        elif len(image.shape) == 3:
            channels = []
            for c in range(image.shape[2]):
                channel = image[:, :, c]
                channels.append(
                    scale_unit_to_dtype(
                        self._decompose_channel(channel, num_imfs), channel
                    )
                )
            decomposed = cv2.merge(channels)
        else:
            raise ValueError("Invalid image dimensions.")

        return {"output_image": decomposed}
