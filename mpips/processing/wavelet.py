"""Canonical wavelet denoising for radiography arrays."""

import warnings
from typing import Any, cast

import numpy as np

try:
    import pywt

    PYWT_AVAILABLE = True
except ImportError:
    PYWT_AVAILABLE = False
    print("PyWavelets not installed. Install with: pip install PyWavelets")


class WaveletDenoiser:
    """Wavelet-based denoising for X-ray images."""

    def __init__(self, wavelet: str = "db4", level: int | None = None) -> None:
        """
        Initialize wavelet denoiser.

        Args:
            wavelet: Wavelet type ('db4', 'db8', 'sym4', 'coif1', 'bior4.4')
            level: Decomposition level (None = auto)
        """
        if not PYWT_AVAILABLE:
            raise ImportError(
                "PyWavelets required. Install with: pip install PyWavelets"
            )

        self.wavelet = wavelet
        self.level = level

    def denoise_wavelet(
        self,
        image: np.ndarray,
        method: str = "BayesShrink",
        mode: str = "soft",
    ) -> np.ndarray:
        """
        Denoise image using wavelet transform.

        Args:
            image: Input grayscale image (float32 [0,1], uint8, or uint16)
            method: 'BayesShrink', 'VisuShrink', or 'manual'
            mode: 'soft' or 'hard' thresholding

        Returns:
            Denoised image (same type and range as input)
        """
        # Handle different input types
        if image.dtype == np.float32 or image.dtype == np.float64:
            # Already normalized
            image_norm = image.astype(np.float64)
            is_float_input = True
            is_16bit = False
        else:
            is_float_input = False
            is_16bit = image.dtype == np.uint16

            # Normalize to [0, 1] for wavelet processing
            if is_16bit:
                image_norm = image.astype(np.float64) / 65535.0
            else:
                image_norm = image.astype(np.float64) / 255.0

        # Determine decomposition level if not specified
        if self.level is None:
            max_level = pywt.dwt_max_level(min(image_norm.shape), self.wavelet)
            level = min(max_level, 3)  # Cap at 3 levels to preserve details
        else:
            level = self.level

        print(
            f"  → Wavelet: {self.wavelet}, Level: {level}, "
            f"Method: {method}, Mode: {mode}"
        )

        # Perform wavelet decomposition
        coeffs = pywt.wavedec2(image_norm, self.wavelet, level=level)

        # Estimate noise from finest scale (highest frequency)
        # Using Median Absolute Deviation (MAD)
        sigma = self._estimate_noise(coeffs[1][0])

        # Threshold coefficients (suppress warnings from pywt)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=RuntimeWarning)
            coeffs_thresh = self._threshold_coeffs(coeffs, sigma, method, mode)

        # Reconstruct image
        denoised_norm = pywt.waverec2(coeffs_thresh, self.wavelet)

        # Handle size mismatch due to wavelet decomposition
        denoised_norm = denoised_norm[: image_norm.shape[0], : image_norm.shape[1]]

        # Denormalize and clip to valid range
        denoised_norm = np.clip(denoised_norm, 0, 1)

        # Replace any NaN or inf values with 0
        denoised_norm = np.nan_to_num(denoised_norm, nan=0.0, posinf=1.0, neginf=0.0)

        # Return in same format as input
        if is_float_input:
            return cast(np.ndarray, denoised_norm.astype(np.float32))
        elif is_16bit:
            denoised = (denoised_norm * 65535).astype(np.uint16)
        else:
            denoised = (denoised_norm * 255).astype(np.uint8)

        return cast(np.ndarray, denoised)

    def _estimate_noise(self, detail_coeffs: np.ndarray) -> Any:
        """Estimate noise level using MAD (Median Absolute Deviation)."""
        sigma = np.median(np.abs(detail_coeffs)) / 0.6745
        return sigma

    def _threshold_coeffs(
        self, coeffs: list[Any], sigma: Any, method: str, mode: str
    ) -> list[Any]:
        """Apply thresholding to wavelet coefficients."""
        coeffs_thresh = [coeffs[0]]  # Keep approximation coefficients

        for i in range(1, len(coeffs)):
            # Each level has 3 detail components (cH, cV, cD)
            detail = list(coeffs[i])

            for j in range(3):
                if method == "VisuShrink":
                    # Universal threshold
                    n = detail[j].size
                    threshold = sigma * np.sqrt(2 * np.log(n))

                elif method == "BayesShrink":
                    # Adaptive threshold based on signal variance
                    # (softer to preserve details)
                    var_y = np.var(detail[j])
                    var_x = max(var_y - sigma**2, 0)
                    if var_x > 0:
                        threshold = sigma**2 / (np.sqrt(var_x) + 1e-10)
                        threshold = (
                            threshold * 0.5
                        )  # Reduce threshold to keep more details
                    else:
                        threshold = sigma * 0.5

                else:  # manual
                    threshold = 3 * sigma

                # Apply thresholding
                if mode == "soft":
                    detail[j] = pywt.threshold(detail[j], threshold, mode="soft")
                else:
                    detail[j] = pywt.threshold(detail[j], threshold, mode="hard")

            coeffs_thresh.append(tuple(detail))

        return coeffs_thresh

    def multilevel_denoise(
        self, image: np.ndarray, levels: list[int] = [3, 4, 5]
    ) -> np.ndarray:
        """
        Apply multi-level wavelet denoising and combine results.

        Args:
            image: Input image
            levels: List of decomposition levels to try

        Returns:
            Combined denoised image
        """
        results = []

        for lvl in levels:
            original_level = self.level
            self.level = lvl
            denoised = self.denoise_wavelet(image, method="BayesShrink", mode="soft")
            results.append(denoised.astype(np.float32))
            self.level = original_level

        # Average the results
        combined = np.mean(results, axis=0)

        if image.dtype == np.uint16:
            combined = combined.astype(np.uint16)
        else:
            combined = combined.astype(np.uint8)

        return cast(np.ndarray, combined)
