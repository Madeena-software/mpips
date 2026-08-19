"""Canonical threshold-detection operation."""

import os
from typing import Any, cast

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks

MAX_16BIT = 65535


def apply_threshold_separation(image: np.ndarray, threshold: float) -> np.ndarray:
    """Separate content from background using the accepted NumPy behavior."""
    # Create mask for content (pixels <= threshold)
    content_mask = image <= threshold

    # Extract content pixels
    content_only = image.copy()
    content_only[~content_mask] = 0

    # Get min/max of content
    content_pixels = image[content_mask]
    if len(content_pixels) > 0:
        content_min = content_pixels.min()
        content_max = content_pixels.max()
    else:
        content_min = image.min()
        content_max = image.max()

    # Normalize content to full range [0, 1]
    if content_max > content_min:
        content_normalized = (
            (content_only - content_min) / (content_max - content_min)
        ).astype(np.float32)
    else:
        content_normalized = content_only.astype(np.float32)

    # Set background to 1.0 (white)
    return np.where(content_mask, content_normalized, 1.0).astype(np.float32)


def detect_threshold(
    image: np.ndarray,
    method: str = "auto",
    *,
    debug: bool = False,
    filename: str | None = None,
    output_dir: str | None = None,
) -> float:
    threshold_method = method.lower()
    debug_enabled = debug
    """
    Detect optimal threshold for background separation.
    Uses 5 methods with priority on secondary peak (background noise level).
    Updated to match auto_threshold_detection.py and work with float32 [0,1] range.

    Args:
        image: Input image (float32 [0,1])
        filename: Optional filename for debug output naming
        output_dir: Optional directory to save debug histogram files

    Returns:
        threshold: Optimal threshold value (in same range as image)
    """
    # Calculate histogram with higher resolution (512 bins instead of 256)
    hist, bins = np.histogram(
        image.flatten(), bins=512, range=(image.min(), image.max())
    )
    bin_centers = (bins[:-1] + bins[1:]) / 2

    # Smooth histogram
    hist_smooth = gaussian_filter1d(hist.astype(float), sigma=3)

    # Debug: Show all candidate thresholds and plot them (only if DEBUG=True)
    if debug_enabled:
        import matplotlib.pyplot as plt

        plt.figure(figsize=(10, 5))
        plt.plot(bin_centers, hist, label="Histogram", alpha=0.5)
        plt.plot(bin_centers, hist_smooth, label="Smoothed", linewidth=2)

    # Method 1: Percentile (25%)
    threshold_25 = np.percentile(image, 25)
    if debug_enabled:
        plt.axvline(
            threshold_25,
            color="orange",
            linestyle="--",
            label=f"Percentile 25% ({threshold_25:.4f})",
        )

    # Method 2: valley detection between first two peaks (higher sensitivity:
    # 0.1 prominence)
    peaks, _ = find_peaks(hist_smooth, prominence=hist_smooth.max() * 0.1)
    if len(peaks) >= 2:
        valley_range = (bin_centers >= bin_centers[peaks[0]]) & (
            bin_centers <= bin_centers[peaks[1]]
        )
        if np.any(valley_range):
            valley_idx = np.argmin(hist_smooth[valley_range])
            threshold_valley = bin_centers[valley_range][valley_idx]
        else:
            threshold_valley = threshold_25
    else:
        threshold_valley = threshold_25
    if debug_enabled:
        plt.axvline(
            threshold_valley,
            color="green",
            linestyle="--",
            label=f"Valley ({threshold_valley:.4f})",
        )

    # Method 3: Knee detection (inflection point in CDF)
    cumsum = np.cumsum(hist)
    cumsum_norm = cumsum / cumsum[-1]
    gradient = np.gradient(cumsum_norm)
    gradient_smooth = gaussian_filter1d(gradient, sigma=5)
    second_deriv = np.gradient(gradient_smooth)

    inflection_candidates = np.where(
        np.abs(second_deriv) > np.percentile(np.abs(second_deriv), 90)
    )[0]
    if len(inflection_candidates) > 0:
        threshold_knee = bin_centers[inflection_candidates[0]]
    else:
        threshold_knee = threshold_25
    if debug_enabled:
        plt.axvline(
            threshold_knee,
            color="blue",
            linestyle="--",
            label=f"Knee ({threshold_knee:.4f})",
        )

    # Method 4: Otsu's method (convert to uint16 first for OpenCV)
    threshold_otsu: Any
    if image.dtype == np.float32:
        # Convert to uint16 for Otsu
        image_uint16 = (image * MAX_16BIT).clip(0, MAX_16BIT).astype(np.uint16)
        _, threshold_otsu_uint16 = cv2.threshold(
            image_uint16, 0, MAX_16BIT, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        threshold_otsu = (
            threshold_otsu_uint16 / MAX_16BIT
        )  # Convert back to float32 range
    else:
        _, threshold_otsu = cv2.threshold(
            image, 0, MAX_16BIT, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
    # Ensure threshold_otsu is a scalar for formatting/plotting
    if isinstance(threshold_otsu, np.ndarray):
        if threshold_otsu.size == 1:
            threshold_otsu_val = float(threshold_otsu.flat[0])
        else:
            threshold_otsu_val = float(
                threshold_otsu.ravel()[0]
            )  # Take first value if array has multiple elements
    else:
        threshold_otsu_val = float(threshold_otsu)
    if debug_enabled:
        plt.axvline(
            threshold_otsu_val,
            color="purple",
            linestyle="--",
            label=f"Otsu ({threshold_otsu_val:.4f})",
        )

    # Method 5: Secondary peak detection (background noise level)
    threshold_secondary = None
    img_range = image.max() - image.min()
    adaptive_min = image.min() + img_range * 0.40
    adaptive_max = image.min() + img_range * 0.90

    # For float32 range, scale the fixed search values from uint16 range
    if image.dtype == np.float32:
        search_min = min(adaptive_min, 700.0 / MAX_16BIT)
        search_max = max(adaptive_max, min(image.max(), 950.0 / MAX_16BIT))
    else:
        search_min = min(adaptive_min, 700)
        search_max = max(adaptive_max, min(image.max(), 950))

    search_mask = (bin_centers >= search_min) & (bin_centers <= search_max)

    if np.any(search_mask):
        hist_search = hist_smooth[search_mask]
        bins_search = bin_centers[search_mask]

        peaks_secondary, properties = find_peaks(
            hist_search, prominence=hist_smooth.max() * 0.01
        )

        if len(peaks_secondary) > 0:
            most_prominent_idx = np.argmax(properties["prominences"])
            peak_position = bins_search[peaks_secondary[most_prominent_idx]]
            prominence = properties["prominences"][most_prominent_idx]  # noqa: F841

            # Find valley before secondary peak
            if image.dtype == np.float32:
                valley_search_start = max(peak_position * 0.5, 400.0 / MAX_16BIT)
            else:
                valley_search_start = max(peak_position * 0.5, 400)

            valley_mask = (bin_centers >= valley_search_start) & (
                bin_centers < peak_position
            )
            if np.any(valley_mask):
                hist_before_peak = hist_smooth[valley_mask]
                bins_before_peak = bin_centers[valley_mask]
                valley_idx = np.argmin(hist_before_peak)
                threshold_secondary = bins_before_peak[valley_idx]

    # Results dictionary
    thresholds = {
        "percentile_25": threshold_25,
        "valley": threshold_valley,
        "knee": threshold_knee,
        "otsu": threshold_otsu,
    }

    if threshold_secondary is not None:
        thresholds["secondary_peak"] = threshold_secondary
        if debug_enabled:
            plt.axvline(
                threshold_secondary,
                color="red",
                linestyle="--",
                label=f"Secondary Peak ({threshold_secondary:.4f})",
            )

    # Choose threshold based on .env setting
    # Supported methods: auto, valley, otsu, knee, percentile_25, secondary_peak
    if threshold_method == "valley":
        threshold_auto = threshold_valley
        selected_method = "valley (.env)"
    elif threshold_method == "otsu":
        threshold_auto = threshold_otsu_val
        selected_method = "otsu (.env)"
    elif threshold_method == "knee":
        threshold_auto = threshold_knee
        selected_method = "knee (.env)"
    elif threshold_method == "percentile_25":
        threshold_auto = threshold_25
        selected_method = "percentile_25 (.env)"
    elif threshold_method == "secondary_peak" and threshold_secondary is not None:
        threshold_auto = threshold_secondary
        selected_method = "secondary_peak (.env)"
    elif threshold_method == "auto" or threshold_method is None:
        # Auto mode: intelligent selection based on image characteristics
        # Priority: valley first (if bimodal), then secondary_peak, then otsu,
        # then percentile
        if len(peaks) >= 2:
            # Bimodal histogram: valley is most reliable
            threshold_auto = threshold_valley
            selected_method = "valley (auto)"
        elif threshold_secondary is not None:
            # Use secondary_peak if valley detection failed but secondary peak exists
            threshold_auto = threshold_secondary
            selected_method = "secondary_peak (auto-fallback)"
        elif threshold_otsu_val > 0:
            # Fallback to Otsu for unimodal distributions
            threshold_auto = threshold_otsu_val
            selected_method = "otsu (auto-fallback)"
        else:
            # Ultimate fallback: percentile
            threshold_auto = threshold_25
            selected_method = "percentile_25 (auto-fallback)"
    else:
        # Unknown method in .env, use safe fallback
        if image.dtype == np.float32:
            threshold_auto = 650.0 / MAX_16BIT  # Scale to [0,1] range
        else:
            threshold_auto = 650
        selected_method = f"fixed (unknown method: {threshold_method})"

    # Debug: Print all candidate thresholds and which was selected (only if DEBUG=True)
    if debug_enabled:
        print(f"[DEBUG][THRESHOLDS] Percentile 25%: {threshold_25:.6f}")
        print(f"[DEBUG][THRESHOLDS] Valley: {threshold_valley:.6f}")
        print(f"[DEBUG][THRESHOLDS] Knee: {threshold_knee:.6f}")
        print(f"[DEBUG][THRESHOLDS] Otsu: {threshold_otsu_val:.6f}")
        if threshold_secondary is not None:
            print(f"[DEBUG][THRESHOLDS] Secondary Peak: {threshold_secondary:.6f}")
        print(
            f"[DEBUG][THRESHOLDS] Selected: {threshold_auto:.6f} "
            f"(method: {selected_method})"
        )

        # Save histogram with all candidate thresholds marked
        plt.axvline(
            threshold_auto,
            color="black",
            linestyle="-",
            linewidth=2,
            label=f"Selected ({threshold_auto:.4f})",
        )
        plt.legend()
        plt.tight_layout()
        # Include filename in debug output to avoid overwriting
        debug_filename = (
            f"debug_histogram_thresholds_{filename}.png"
            if filename
            else "debug_histogram_thresholds.png"
        )
        # Save to output_dir if provided, otherwise save to current directory
        if output_dir:
            debug_filepath = os.path.join(output_dir, debug_filename)
        else:
            debug_filepath = debug_filename
        plt.savefig(debug_filepath)
        plt.close()
        print(f"[DEBUG] Saved threshold histogram: {debug_filepath}")

    return cast(float, threshold_auto)
