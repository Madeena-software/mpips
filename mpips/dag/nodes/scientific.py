import os
import cv2
import numpy as np
import tempfile
import scipy.ndimage as ndimage
from typing import Dict, Any, List, Tuple
from skimage.restoration import denoise_wavelet

from mpips.dag.nodes.base import BaseNode
from mpips.processing.bit_depth import (
    clip_to_input_dtype,
    normalize_to_uint8,
    scale_unit_to_dtype,
)
from mpips.storage import download_image


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


class LevelingNode(BaseNode):
    """Rescales brightness so the input image's mean matches a reference mean.

    Promoted from the "Global Brightness Leveling" step in
    research/leveling.py, which equalizes intensity drift across a batch of
    radiographs by comparing each image's mean against a baseline mean
    established from the batch's first image. Here the baseline is passed
    in as ``target_mean`` instead of being tracked across a batch, since
    nodes execute one image at a time. The current mean is measured within
    an ROI (x_start/y_start/width/height; width/height of 0 extends to the
    image edge, so the default ROI is the whole image), then the resulting
    scale factor is applied to the whole image.
    """

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        image = inputs.get("input_image")
        if image is None:
            raise ValueError("LevelingNode requires 'input_image' input.")

        target_mean = float(params.get("target_mean", 0.0))
        if target_mean < 0:
            raise ValueError(
                "target_mean must be a non-negative reference brightness "
                "(the mean of the batch's baseline image's ROI)."
            )

        h, w = image.shape[:2]
        x_start = max(0, min(w - 1, int(params.get("x_start", 0))))
        y_start = max(0, min(h - 1, int(params.get("y_start", 0))))
        width = int(params.get("width", 0))
        height = int(params.get("height", 0))
        roi_w = (w - x_start) if width <= 0 else max(1, min(w - x_start, width))
        roi_h = (h - y_start) if height <= 0 else max(1, min(h - y_start, height))
        roi = image[y_start : y_start + roi_h, x_start : x_start + roi_w]

        current_mean = float(np.mean(roi))
        if current_mean <= 0:
            return {"output_image": image.copy()}

        scale_factor = target_mean / current_mean
        leveled = image.astype(np.float64) * scale_factor

        return {"output_image": clip_to_input_dtype(leveled, image)}


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
    """Fast Adaptive Bi-dimensional Empirical Mode Decomposition.

    Decomposes a single image into up to MAX_IMFS bi-dimensional intrinsic
    mode functions (BIMFs, highest frequency first) plus a residual, each
    exposed as its own named output slot (bimf_1..bimf_10, residual) so a
    DAG can route each component to a different downstream node — e.g. a
    PACE-2.0-style pipeline selectively denoises low-energy BIMFs while
    leaving high-energy ones untouched, then recombines through a Merge
    node. Slots beyond num_imfs are simply left unpopulated.
    """

    MAX_IMFS = 10

    def _decompose_channel(
        self, residue: np.ndarray, num_imfs: int
    ) -> Tuple[List[np.ndarray], np.ndarray]:
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

        return imfs, current  # BIMFs (high -> low frequency), residual

    @staticmethod
    def _normalize(component: np.ndarray) -> np.ndarray:
        c_min = np.min(component)
        c_max = np.max(component)
        if c_max > c_min:
            return (component - c_min) / (c_max - c_min)  # type: ignore[no-any-return]
        return np.zeros_like(component)

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        image = inputs.get("input_image")
        if image is None:
            raise ValueError("FABEMDNode requires 'input_image' input.")

        num_imfs = max(1, min(int(params.get("num_imfs", 2)), self.MAX_IMFS))

        if len(image.shape) == 2:
            imfs, residual = self._decompose_channel(image, num_imfs)
            outputs = {
                f"bimf_{i + 1}": scale_unit_to_dtype(self._normalize(imf), image)
                for i, imf in enumerate(imfs)
            }
            outputs["residual"] = scale_unit_to_dtype(self._normalize(residual), image)
            return outputs

        if len(image.shape) == 3:
            channels = image.shape[2]
            per_channel = [
                self._decompose_channel(image[:, :, c], num_imfs)
                for c in range(channels)
            ]

            outputs = {}
            for i in range(num_imfs):
                outputs[f"bimf_{i + 1}"] = cv2.merge(
                    [
                        scale_unit_to_dtype(
                            self._normalize(per_channel[c][0][i]), image[:, :, c]
                        )
                        for c in range(channels)
                    ]
                )
            outputs["residual"] = cv2.merge(
                [
                    scale_unit_to_dtype(
                        self._normalize(per_channel[c][1]), image[:, :, c]
                    )
                    for c in range(channels)
                ]
            )
            return outputs

        raise ValueError("Invalid image dimensions.")
