import matplotlib.pyplot as plt
import os
from pathlib import Path


from mpips.pipelines.config import ImagerPipelineConfig


# Load environment variables from .env file
def load_env_config():
    """Load configuration derived from canonical ImagerPipelineConfig model."""
    configured_env = os.environ.get("MPIPS_RADIOGRAPHY_ENV")
    env_candidates = [
        configured_env,
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.path.dirname(__file__), ".env"),
    ]
    env_path = next(
        (path for path in env_candidates if path and os.path.exists(path)), ""
    )

    env_dict = dict(os.environ)
    if env_path and os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    env_dict[key.strip()] = value.strip()

    typed_config = ImagerPipelineConfig.from_env(env_dict)
    config = typed_config.to_legacy_engine_dict()

    # Preserve non-pipeline runtime options from env if specified
    for extra_key in (
        "USE_GPU",
        "USE_IMAGEJ",
        "NUM_WORKERS",
        "RAW_PATH",
        "DARK_PATH",
        "FLAT_PATH",
        "OUTPUT_DIR",
    ):
        if extra_key in env_dict:
            raw_val = env_dict[extra_key]
            if extra_key in ("USE_GPU", "USE_IMAGEJ"):
                config[extra_key] = raw_val.lower() in ("1", "true", "yes", "on")
            elif extra_key == "NUM_WORKERS":
                config[extra_key] = int(raw_val) if raw_val else None
            else:
                config[extra_key] = raw_val

    return config


# Global config loaded once
CONFIG = load_env_config()


def get_debug_flag():
    return CONFIG["DEBUG"]


def get_use_gpu_flag():
    return CONFIG["USE_GPU"]


def get_use_imagej_flag():
    return CONFIG["USE_IMAGEJ"]


def save_histogram(image, out_path, title=None):
    if get_debug_flag():
        plt.figure(figsize=(8, 4))
        plt.hist(image.ravel(), bins=256, color="blue", alpha=0.7)
        if title:
            plt.title(title)
        plt.xlabel("Pixel Value")
        plt.ylabel("Count")
        plt.tight_layout()
        plt.savefig(out_path)
        plt.close()
        print(f"[DEBUG] Saved histogram: {out_path}")


"""
Complete X-ray Image Processing Pipeline with GPU Acceleration

Processing steps:
1. Crop and rotate by detector type (BED/TRX)
2. Denoise dark, gain, raw using wavelet (sym4, level=3, BayesShrink, soft)
3. Calculate FFC with GPU acceleration
4. Normalize to 16-bit range (scale max value to 65535)
5. Auto Thresholding (background separation)
6. Invert
7. Enhance Contrast like ImageJ (saturated pixels=10%, Normalize, Equalize histogram)
8. Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)

GPU Acceleration:
- CuPy for array operations (FFC, normalization, thresholding, contrast enhancement)
- Parallel batch processing using multiprocessing
"""

import cv2
import numpy as np
import os
import re
import math
from pathlib import Path
from scipy.signal import find_peaks
from scipy.ndimage import gaussian_filter1d, median_filter
from multiprocessing import Pool, cpu_count
import skimage.restoration
import skimage.filters

# ============================================================================
# CONSTANTS - Bit depth values
# ============================================================================
MAX_8BIT = 255
MAX_16BIT = 65535
MAX_18BIT = 262143
MAX_20BIT = 1048575

# GPU acceleration with CuPy
try:
    import cupy as cp

    CUPY_AVAILABLE = True
except ImportError:
    CUPY_AVAILABLE = False
    cp = np  # Fallback to NumPy

# Check if GPU should be used (must have CuPy AND .env flag enabled)
GPU_AVAILABLE = CUPY_AVAILABLE and get_use_gpu_flag()

if GPU_AVAILABLE:
    print("✓ GPU acceleration enabled (CuPy + USE_GPU=True)")
elif CUPY_AVAILABLE and not get_use_gpu_flag():
    print("✗ GPU acceleration disabled (USE_GPU=False in .env)")
else:
    print("✗ GPU acceleration not available (CuPy not installed)")

# Import wavelet denoising
try:
    from mpips.processing.wavelet import WaveletDenoiser

    WAVELET_AVAILABLE = True
except ImportError:
    WAVELET_AVAILABLE = False
    print(
        "Warning: wavelet_denoising module not available. Wavelet denoising disabled."
    )

# Import ImageJ replicator
try:
    from mpips.processing.imagej import ImageJReplicator

    IMAGEJ_MODULE_AVAILABLE = True
except ImportError:
    IMAGEJ_MODULE_AVAILABLE = False
    print(
        "Warning: imagej_replicator module not available. ImageJ processing disabled."
    )


# Check if ImageJ should be used (must have module AND .env flag enabled)
IMAGEJ_AVAILABLE = IMAGEJ_MODULE_AVAILABLE and get_use_imagej_flag()

if IMAGEJ_AVAILABLE:
    print("✓ ImageJ processing enabled (imagej_replicator + USE_IMAGEJ=True)")
elif IMAGEJ_MODULE_AVAILABLE and not get_use_imagej_flag():
    print("✗ ImageJ processing disabled (USE_IMAGEJ=False in .env)")
else:
    print("✗ ImageJ processing not available (imagej_replicator not installed)")


def denoise_wavelet(image, wavelet="sym4", level=3, method="BayesShrink", mode="soft"):
    """
    Denoise image using wavelet transform.

    Args:
        image: Input image
        wavelet: Wavelet type (default: 'sym4')
        level: Decomposition level (default: 3)
        method: Thresholding method (default: 'BayesShrink')
        mode: Thresholding mode (default: 'soft')

    Returns:
        Denoised image
    """
    if not WAVELET_AVAILABLE:
        print("  Warning: Wavelet denoising not available, returning original image")
        return image

    denoiser = WaveletDenoiser(wavelet=wavelet, level=level)
    return denoiser.denoise_wavelet(image, method=method, mode=mode)


def flat_field_correction(raw_image, dark_image, flat_image):
    """
    Perform flat-field correction on a radiograph image with GPU acceleration.
    Images are already denoised before this step.

    Formula: corrected = (raw - dark) / (flat - dark) * mean(flat - dark)

    Args:
        raw_image: The raw radiograph image to be corrected
        dark_image: The dark frame (image taken with no X-ray exposure)
        flat_image: The flat field image (uniform exposure)

    Returns:
        Flat-field corrected image
    """
    if GPU_AVAILABLE:
        # GPU-accelerated version with CuPy
        raw_32 = cp.asarray(raw_image, dtype=cp.float32)
        dark_32 = cp.asarray(dark_image, dtype=cp.float32)
        flat_32 = cp.asarray(flat_image, dtype=cp.float32)

        # Calculate (flat - dark)
        flat_minus_dark = cp.maximum(0, flat_32 - dark_32)

        # Calculate mean of (flat - dark)
        mean_value = cp.mean(flat_minus_dark)

        # Calculate (raw - dark)
        raw_minus_dark = cp.maximum(0, raw_32 - dark_32)

        # Calculate (raw - dark) / (flat - dark)
        corrected = cp.zeros_like(raw_minus_dark)
        mask = flat_minus_dark != 0
        corrected[mask] = raw_minus_dark[mask] / flat_minus_dark[mask]

        # Multiply by mean to restore intensity scale
        corrected = corrected * mean_value

        # Clip negative values
        corrected = cp.clip(corrected, 0, None)

        # Convert back to CPU and original dtype
        corrected_cpu = cp.asnumpy(corrected)
    else:
        from mpips.processing.correction import flat_field_correction

        return flat_field_correction(raw_image, dark_image, flat_image)

    # Keep as float32 if input is float, otherwise convert back to original dtype
    if raw_image.dtype == np.float32:
        return corrected_cpu.astype(np.float32)
    elif raw_image.dtype == np.uint8:
        corrected_cpu = np.clip(corrected_cpu, 0, MAX_8BIT).astype(np.uint8)
    elif raw_image.dtype == np.uint16:
        corrected_cpu = np.clip(corrected_cpu, 0, MAX_16BIT).astype(np.uint16)
    else:
        corrected_cpu = corrected_cpu.astype(raw_image.dtype)

    return corrected_cpu


def normalize_to_max_value(image, saturated_pixels=None):
    """
    Stretch image histogram to use the full dynamic range using ImageJ's method.

    Uses ImageJ's histogram threshold counting approach (more advanced than percentile)
    to determine optimal stretch range, then applies LUT-based normalization.

    Args:
        image: Input image (uint8 or uint16)
        saturated_pixels: Percentage of pixels to saturate (0-100)
            Default from config: NORMALIZE_SATURATED_PIXELS

    Returns:
        Contrast-stretched image with full dynamic range (same dtype as input)
    """
    if saturated_pixels is None:
        saturated_pixels = CONFIG["NORMALIZE_SATURATED_PIXELS"]

    if not IMAGEJ_AVAILABLE:
        print("  Warning: ImageJ normalization not available, returning original image")
        return image

    # Ensure image is in correct format (uint8 or uint16)
    if image.dtype == np.float32 or image.dtype == np.float64:
        # Convert float to uint16
        image_uint16 = np.clip(image, 0, MAX_16BIT).astype(np.uint16)
    else:
        image_uint16 = image

    # Use ImageJ enhance_contrast with normalize=True, equalize=False
    result = ImageJReplicator.enhance_contrast(
        image_uint16,
        saturated_pixels=saturated_pixels,
        equalize=False,
        normalize=True,
        classic_equalization=False,
    )

    return result


def crop_and_rotate_by_detector(image, detector_type):
    """
    Crop and rotate image based on detector type.
    Crop values are read from .env file (CROP_TOP, CROP_BOTTOM, CROP_LEFT, CROP_RIGHT).

    Args:
        image: Input image
        detector_type: 'BED' or 'TRX'

    Returns:
        Cropped and rotated image
    """
    from mpips.processing.geometry import crop_and_rotate

    return crop_and_rotate(
        image,
        detector_type,
        crop_top=CONFIG["CROP_TOP"],
        crop_bottom=CONFIG["CROP_BOTTOM"],
        crop_left=CONFIG["CROP_LEFT"],
        crop_right=CONFIG["CROP_RIGHT"],
    )


def detect_detector_type(filename):
    """
    Detect detector type from filename.

    Args:
        filename: Image filename

    Returns:
        'TRX' or 'BED'
    """
    filename_upper = filename.upper()

    # TRX detector: Thorax, Humeri, Cervical, Clavikula
    trx_keywords = ["THORAX", "HUMERI", "HUMERUS", "CERVICAL", "CLAVIKULA", "CLAVICULA"]
    if any(keyword in filename_upper for keyword in trx_keywords):
        return "TRX"
    else:
        return "BED"


def auto_threshold_detection(image, filename=None, output_dir=None):
    from mpips.processing.thresholding import detect_threshold

    return detect_threshold(
        image,
        method=CONFIG.get("THRESHOLD_METHOD", "auto").lower(),
        debug=get_debug_flag(),
        filename=filename,
        output_dir=output_dir,
    )


def apply_threshold_separation(image, threshold):
    """
    Separate content from background and normalize content to full range.
    GPU-accelerated when CuPy is available.
    Works with float32 [0,1] range.

    Args:
        image: Input image (float32 [0,1])
        threshold: Threshold value (in same range as image)

    Returns:
        Processed image with background set to 1.0, content normalized to [0,1]
    """
    if GPU_AVAILABLE:
        # GPU path with CuPy
        img_gpu = cp.asarray(image, dtype=cp.float32)

        # Create mask for content (pixels <= threshold)
        content_mask = img_gpu <= threshold

        # Extract content pixels for min/max calculation
        content_pixels = img_gpu[content_mask]
        if content_pixels.size > 0:
            content_min = float(cp.min(content_pixels))
            content_max = float(cp.max(content_pixels))
        else:
            content_min = float(cp.min(img_gpu))
            content_max = float(cp.max(img_gpu))

        # Normalize content to full range [0, 1]
        if content_max > content_min:
            img_normalized = (img_gpu - content_min) / (content_max - content_min)
        else:
            img_normalized = img_gpu

        # Set background to 1.0 (white), content to normalized values
        result_gpu = cp.where(content_mask, img_normalized, 1.0)
        result_gpu = cp.clip(result_gpu, 0, 1.0)

        # Transfer back to CPU
        result = cp.asnumpy(result_gpu).astype(np.float32)
    else:
        from mpips.processing.thresholding import (
            apply_threshold_separation as processing_apply_threshold_separation,
        )

        return processing_apply_threshold_separation(image, threshold)

    return result


def invert_image(image):
    """
    Invert the image colors.
    Works with float32 [0,1] range.
    """
    from mpips.processing.intensity import invert_image as process_invert_image

    return process_invert_image(image)


def apply_advanced_median_filter(image, filter_type="hybrid_imagej", radius=2):
    from mpips.processing.filtering import apply_median_filter

    return apply_median_filter(
        image,
        filter_type=filter_type,
        radius=radius,
        imagej_available=IMAGEJ_AVAILABLE,
    )


def _get_filter_description(filter_type):
    """Get description of filter type for informational output."""
    descriptions = {
        "standard": "Traditional scipy median filter (square kernel)",
        "bilateral": "Edge-preserving bilateral filter (good for bone details)",
        "adaptive": "Adaptive median filter (best for salt-pepper noise)",
        "nlm": "Non-local means denoising (preserves textures)",
        "morphological": "Morphological median (shape-preserving)",
        "hybrid_imagej": "ImageJ Hybrid 2D Median (BEST FOR X-RAY - edge preserving)",
        "circular_imagej": "ImageJ circular kernel median (natural shape preservation)",
    }
    return descriptions.get(filter_type, "Unknown filter type")


def process_single_image(
    raw_path,
    dark_path,
    flat_path,
    output_path,
    detector_type=None,
    map_x=None,
    map_y=None,
):
    """
    Process a single image through the complete pipeline.

    Pipeline:
    1. Denoise dark, gain, raw using wavelet
    2. Calculate FFC
    3. Neural Calibration Remap (if map_x and map_y provided)
    4. Crop and rotate
    5. Auto Thresholding
    6. Invert
    7. Enhance Contrast (ImageJ method: saturated=0.35%, normalize)
    8. CLAHE (ImageJ method: block_size=127, max_slope=1.5)

    Args:
        raw_path: Path to raw image
        dark_path: Path to dark calibration image
        flat_path: Path to flat/gain calibration image
        output_path: Path to save final result
        detector_type: 'BED' or 'TRX' (if None, auto-detect from filename)
        map_x: X-coordinates for remap
        map_y: Y-coordinates for remap

    Returns:
        True if successful, False otherwise
    """
    print(f"\nProcessing: {os.path.basename(raw_path)}")

    # Detect detector type if not provided
    if detector_type is None:
        detector_type = detect_detector_type(os.path.basename(raw_path))
        print(f"  Detected detector: {detector_type}")

    # Load images
    print("  [1/10] Loading images...")
    raw_image = cv2.imread(raw_path, cv2.IMREAD_UNCHANGED)
    dark_image = cv2.imread(dark_path, cv2.IMREAD_UNCHANGED)
    flat_image = cv2.imread(flat_path, cv2.IMREAD_UNCHANGED)

    if raw_image is None or dark_image is None or flat_image is None:
        print("  ERROR: Failed to load one or more images")
        return False

    print(f"    Raw: {raw_image.shape}, dtype: {raw_image.dtype}")

    # Save histogram for loaded raw image
    debug_dir = os.path.dirname(output_path)
    image_id = os.path.splitext(os.path.basename(raw_path))[0]
    save_histogram(
        raw_image,
        os.path.join(debug_dir, f"histogram_raw_{image_id}.png"),
        title="Raw Image Histogram",
    )

    # Convert to float32 immediately after loading
    raw_image = raw_image.astype(np.float32) / MAX_16BIT
    dark_image = dark_image.astype(np.float32) / MAX_16BIT
    flat_image = flat_image.astype(np.float32) / MAX_16BIT

    # Step 1: Denoise using wavelet (on full-size arrays)
    wavelet_type = CONFIG["WAVELET_TYPE"]
    wavelet_level = CONFIG["WAVELET_LEVEL"]
    wavelet_method = CONFIG["WAVELET_METHOD"]
    wavelet_mode = CONFIG["WAVELET_MODE"]
    print(
        f"  [1/10] Denoising images (wavelet: {wavelet_type}, level={wavelet_level}, {wavelet_method}, {wavelet_mode})..."
    )
    if CONFIG.get("USE_DENOISE", True):
        dark_denoised = denoise_wavelet(
            dark_image,
            wavelet=wavelet_type,
            level=wavelet_level,
            method=wavelet_method,
            mode=wavelet_mode,
        )
        flat_denoised = denoise_wavelet(
            flat_image,
            wavelet=wavelet_type,
            level=wavelet_level,
            method=wavelet_method,
            mode=wavelet_mode,
        )
        raw_denoised = denoise_wavelet(
            raw_image,
            wavelet=wavelet_type,
            level=wavelet_level,
            method=wavelet_method,
            mode=wavelet_mode,
        )
    else:
        dark_denoised = dark_image
        flat_denoised = flat_image
        raw_denoised = raw_image

    save_histogram(
        raw_denoised,
        os.path.join(debug_dir, f"histogram_denoised_{image_id}.png"),
        title="Denoised Raw Histogram",
    )

    # Step 2: FFC with matched dimensions
    print("  [2/10] Applying Flat-Field Correction...")
    ffc_result = flat_field_correction(raw_denoised, dark_denoised, flat_denoised)
    print(f"    FFC output range: {ffc_result.min()} - {ffc_result.max()}")

    save_histogram(
        ffc_result / ffc_result.max() if ffc_result.max() > 0 else ffc_result,
        os.path.join(debug_dir, f"histogram_ffc_{image_id}.png"),
        title="FFC Result Histogram (Normalized 0-1)",
    )

    # Step 3: Neural calibration remap
    valid_remap_mask = None
    if map_x is not None and map_y is not None:
        print("  [3/10] Applying neural calibration remap...")
        source_height, source_width = ffc_result.shape[:2]
        valid_remap_mask = (
            (map_x >= 0)
            & (map_x <= source_width - 1)
            & (map_y >= 0)
            & (map_y <= source_height - 1)
        ).astype(np.uint8)
        ffc_result = cv2.remap(
            ffc_result,
            map_x.astype(np.float32),
            map_y.astype(np.float32),
            cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        )
        print(f"    Remapped shape: {ffc_result.shape}")
    else:
        print("  [3/10] Neural calibration skipped (no remap provided)")

    # Step 4: Crop and rotate images
    if CONFIG.get("USE_CROP_ROTATE", True):
        print(f"  [4/10] Cropping and rotating ({detector_type})...")

        ffc_result = crop_and_rotate_by_detector(ffc_result, detector_type)
        if valid_remap_mask is not None:
            valid_remap_mask = (
                crop_and_rotate_by_detector(valid_remap_mask, detector_type) > 0
            )

        crop_info = f"top={CONFIG['CROP_TOP']}, bottom={CONFIG['CROP_BOTTOM']}, left={CONFIG['CROP_LEFT']}, right={CONFIG['CROP_RIGHT']}"
        if detector_type == "TRX":
            print(f"    Image: cropped ({crop_info}), rotated 90° CCW")
        else:
            print(f"    Image: cropped ({crop_info})")

        print(f"    Final shape: {ffc_result.shape}")
    else:
        print("  [4/10] Cropping and rotation skipped (USE_CROP_ROTATE=False)")

    save_histogram(
        ffc_result / ffc_result.max() if ffc_result.max() > 0 else ffc_result,
        os.path.join(debug_dir, f"histogram_cropped_{image_id}.png"),
        title="Cropped FFC Histogram",
    )

    # Step 5: Normalize to configurable bit depth (optional)
    if CONFIG.get("USE_NORMALIZE", False):
        print(f"  [5/10] Normalizing to max value {MAX_16BIT}...")
        normalized_result = normalize_to_max_value(
            ffc_result, CONFIG["NORMALIZE_SATURATED_PIXELS"]
        )
        print(
            f"    Normalized range: {normalized_result.min()} - {normalized_result.max()}"
        )

        save_histogram(
            normalized_result / MAX_16BIT,
            os.path.join(debug_dir, f"histogram_normalized_{image_id}.png"),
            title=f"Normalized Result Histogram (max={MAX_16BIT})",
        )
    else:
        print("  [5/10] Normalization skipped (USE_NORMALIZE=False)")
        normalized_result = ffc_result.copy()
        if get_debug_flag():
            print(
                "    [DEBUG] Normalization step was skipped. Passing FFC result forward."
            )

    # Step 6: Auto Thresholding (optional)
    threshold_method = CONFIG.get("THRESHOLD_METHOD", "auto").lower()
    if threshold_method in ["none", "off", "skip", "no"]:
        print("  [6/10] Thresholding skipped (THRESHOLD_METHOD set to 'none'/'off')")
        threshold_result = normalized_result.copy()
        if get_debug_flag():
            print(
                "    [DEBUG] Thresholding step was skipped. Passing normalized result forward."
            )
    else:
        print("  [6/10] Auto Thresholding...")
        threshold = auto_threshold_detection(
            normalized_result, filename=image_id, output_dir=debug_dir
        )
        if get_debug_flag():
            print(f"    [DEBUG] Detected threshold: {threshold:.6f}")
            # Debug: pixel counts below/above threshold
            below = np.count_nonzero(normalized_result <= threshold)
            above = np.count_nonzero(normalized_result > threshold)
            total = normalized_result.size
            print(f"    [DEBUG] Pixels <= threshold: {below} ({below/total:.2%})")
            print(f"    [DEBUG] Pixels > threshold: {above} ({above/total:.2%})")
        threshold_result = apply_threshold_separation(normalized_result, threshold)
        if get_debug_flag():
            print(
                f"    [DEBUG] Thresholded min/max: {threshold_result.min()} - {threshold_result.max()}"
            )
            print(
                f"    [DEBUG] Thresholded nonzero count: {np.count_nonzero(threshold_result)}"
            )

        save_histogram(
            threshold_result,
            os.path.join(debug_dir, f"histogram_thresholded_{image_id}.png"),
            title="Thresholded Result Histogram",
        )

    # Step 7: Invert
    if CONFIG.get("USE_INVERT", True):
        print("  [7/10] Inverting image...")
        inverted = invert_image(threshold_result)
    else:
        print("  [7/10] Inversion skipped (USE_INVERT=False)")
        inverted = threshold_result

    save_histogram(
        inverted,
        os.path.join(debug_dir, f"histogram_inverted_{image_id}.png"),
        title="Inverted Result Histogram",
    )

    # Step 8: Enhance Contrast using ImageJ Replicator
    print("  [8/10] Enhancing contrast (ImageJ method)")
    if not CONFIG["USE_CONTRAST_ENHANCEMENT"]:
        print("    Skipping contrast enhancement (USE_CONTRAST_ENHANCEMENT=False)")
        enhanced_uint16 = (inverted * MAX_16BIT).clip(0, MAX_16BIT).astype(np.uint16)
    elif not IMAGEJ_AVAILABLE:
        print(
            "    Warning: ImageJ processing not available, skipping contrast enhancement"
        )
        enhanced_uint16 = (inverted * MAX_16BIT).clip(0, MAX_16BIT).astype(np.uint16)
    else:
        # Convert float32 [0,1] to uint16 for ImageJ processing
        inverted_uint16 = (inverted * MAX_16BIT).clip(0, MAX_16BIT).astype(np.uint16)

        # Apply ImageJ-style contrast enhancement
        enhanced = ImageJReplicator.enhance_contrast(
            inverted_uint16,
            saturated_pixels=CONFIG["CONTRAST_SATURATED_PIXELS"],
            normalize=CONFIG["CONTRAST_NORMALIZE"],
            equalize=CONFIG["CONTRAST_EQUALIZE"],
            classic_equalization=CONFIG["CONTRAST_CLASSIC_EQUALIZATION"],
        )

        # Convert back to uint16 if needed (enhance_contrast returns uint8 by default)
        if enhanced.dtype == np.uint8:
            enhanced_uint16 = (
                enhanced.astype(np.float32) / MAX_8BIT * MAX_16BIT
            ).astype(np.uint16)
        else:
            enhanced_uint16 = enhanced

        print(f"    Output range: {enhanced_uint16.min()} - {enhanced_uint16.max()}")

    save_histogram(
        enhanced_uint16,
        os.path.join(debug_dir, f"histogram_enhanced_{image_id}.png"),
        title="Enhanced Result Histogram",
    )

    # Step 9: Apply CLAHE using ImageJ Replicator
    # Parameter guide (ImageJ CLAHE style):
    #   blocksize: 127 = default ImageJ (127 pixels tile)
    #              63  = smaller tiles (more local detail)
    #              255 = larger tiles (more global/smooth)
    #   histogram_bins: 256 = default (full 8-bit range)
    #   max_slope: 1.0-2.0 = kontras ringan (untuk X-ray medis)
    #              3.0     = default ImageJ
    #              4.0+    = kontras kuat
    print("  [9/10] Applying CLAHE")
    if not CONFIG["USE_CLAHE"]:
        print("    Skipping CLAHE (USE_CLAHE=False)")
        final_result_uint16 = enhanced_uint16
    elif not IMAGEJ_AVAILABLE:
        print("    Warning: ImageJ processing not available, skipping CLAHE")
        final_result_uint16 = enhanced_uint16
    else:
        # Apply CLAHE using ImageJ-style parameters
        clahe_result = ImageJReplicator.apply_clahe(
            enhanced_uint16,
            blocksize=CONFIG["CLAHE_BLOCKSIZE"],
            histogram_bins=CONFIG["CLAHE_HISTOGRAM_BINS"],
            max_slope=CONFIG["CLAHE_MAX_SLOPE"],
            mask=None,
            fast=CONFIG["CLAHE_FAST"],
            composite=CONFIG["CLAHE_COMPOSITE"],
        )

        # Convert to uint16 if needed
        if clahe_result.dtype == np.uint8:
            final_result_uint16 = (
                clahe_result.astype(np.float32) / MAX_8BIT * MAX_16BIT
            ).astype(np.uint16)
        else:
            final_result_uint16 = clahe_result

        print(
            f"    Final output range: {final_result_uint16.min()} - {final_result_uint16.max()}"
        )

    save_histogram(
        final_result_uint16,
        os.path.join(debug_dir, f"histogram_clahe_{image_id}.png"),
        title="CLAHE Result Histogram",
    )

    # Step 10: Final wavelet denoise (optional, smooths out any artifacts from previous steps)
    if CONFIG.get("USE_FINAL_DENOISE", False):
        wavelet_type = CONFIG["WAVELET_TYPE"]
        wavelet_level = CONFIG["WAVELET_LEVEL"]
        wavelet_method = CONFIG["WAVELET_METHOD"]
        wavelet_mode = CONFIG["WAVELET_MODE"]
        print(
            f"  [10/10] Final denoise (wavelet: {wavelet_type}, level={wavelet_level}, {wavelet_method}, {wavelet_mode})..."
        )
        # Convert uint16 to float32 for wavelet denoising
        final_float = final_result_uint16.astype(np.float32) / MAX_16BIT
        final_denoised = denoise_wavelet(
            final_float,
            wavelet=wavelet_type,
            level=wavelet_level,
            method=wavelet_method,
            mode=wavelet_mode,
        )
        # Convert back to uint16
        final_result_uint16 = (
            (final_denoised * MAX_16BIT).clip(0, MAX_16BIT).astype(np.uint16)
        )
        print(
            f"    Final denoised range: {final_result_uint16.min()} - {final_result_uint16.max()}"
        )

        save_histogram(
            final_result_uint16,
            os.path.join(debug_dir, f"histogram_final_denoised_{image_id}.png"),
            title="Final Denoised Result Histogram",
        )
    else:
        print("  [10/10] Final denoise skipped (USE_FINAL_DENOISE=False)")

    # Step 11: Advanced Median filter (optional, reduces salt-and-pepper noise)
    if CONFIG.get("USE_MEDIAN_FILTER", False):
        radius = CONFIG.get("MEDIAN_FILTER_RADIUS", 2)
        filter_type = CONFIG.get("MEDIAN_FILTER_TYPE", "adaptive")
        print(
            f"  [11/11] Advanced median filter (type={filter_type}, radius={radius})..."
        )

        # Apply advanced median filtering
        final_result_uint16 = apply_advanced_median_filter(
            final_result_uint16, filter_type=filter_type, radius=radius
        )

        print(
            f"    Filtered range: {final_result_uint16.min()} - {final_result_uint16.max()}"
        )
        print(
            f"    Filter type: {filter_type.title()} - {_get_filter_description(filter_type)}"
        )

        save_histogram(
            final_result_uint16,
            os.path.join(
                debug_dir, f"histogram_median_filter_{filter_type}_{image_id}.png"
            ),
            title=f"{filter_type.title()} Median Filter Result Histogram",
        )
    else:
        print("  [11/11] Median filter skipped (USE_MEDIAN_FILTER=False)")

    if valid_remap_mask is not None:
        final_result_uint16[~valid_remap_mask] = 0

    # Save result
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cv2.imwrite(output_path, final_result_uint16)
    print(f"  ✓ Saved to: {output_path}")

    return True


def process_worker(args):
    """
    Worker function for parallel processing.

    Args:
        args: Tuple of (raw_path, dark_path, flat_path, output_path, detector_type)

    Returns:
        Tuple of (success, filename)
    """
    raw_path, dark_path, flat_path, output_path, detector_type = args
    try:
        success = process_single_image(
            raw_path, dark_path, flat_path, output_path, detector_type
        )

        # Clean up GPU memory after each image to prevent memory buildup
        if GPU_AVAILABLE:
            cp.get_default_memory_pool().free_all_blocks()

        return (success, os.path.basename(raw_path))
    except Exception as e:
        print(f"✗ Error processing {os.path.basename(raw_path)}: {str(e)}")

        # Clean up GPU memory on error too
        if GPU_AVAILABLE:
            cp.get_default_memory_pool().free_all_blocks()

        return (False, os.path.basename(raw_path))


def batch_process_parallel(image_list, output_dir, num_workers=None):
    """
    Process multiple images in parallel using multiprocessing.

    Args:
        image_list: List of tuples (raw_path, dark_path, flat_path, detector_type)
        output_dir: Output directory for processed images
        num_workers: Number of parallel workers (default: from .env or auto)

    Returns:
        Statistics dict with success/failure counts
    """
    if num_workers is None:
        # Try to get from config first
        num_workers = CONFIG.get("NUM_WORKERS")

        if num_workers is None:
            # Use fewer workers when GPU is available to avoid GPU memory contention
            # GPU handles internal parallelism more efficiently than multiprocessing
            if GPU_AVAILABLE:
                num_workers = 4  # Optimal for GPU to avoid memory contention
            else:
                num_workers = max(1, cpu_count() - 1)

    print(f"\n{'='*70}")
    print(f"BATCH PROCESSING: {len(image_list)} images")
    print(f"Workers: {num_workers} parallel processes")
    print(f"GPU: {'Enabled' if GPU_AVAILABLE else 'Disabled'}")
    print(f"{'='*70}\n")

    # Prepare arguments for workers
    args_list = []
    for raw_path, dark_path, flat_path, detector_type in image_list:
        filename = os.path.basename(raw_path)

        # Use splitext to properly handle file extensions
        name_without_ext, ext = os.path.splitext(filename)

        # Create output filename with _processed suffix (allows tracking of re-processing)
        output_filename = f"{name_without_ext}_processed{ext}"

        output_path = os.path.join(output_dir, output_filename)
        args_list.append((raw_path, dark_path, flat_path, output_path, detector_type))

    # Process in parallel
    with Pool(processes=num_workers) as pool:
        results = pool.map(process_worker, args_list)

    # Collect statistics
    successful = sum(1 for success, _ in results if success)
    failed = len(results) - successful

    print(f"\n{'='*70}")
    print("BATCH PROCESSING COMPLETE")
    print(f"{'='*70}")
    print(f"Total images:           {len(results)}")
    print(f"Successfully processed: {successful}")
    print(f"Failed:                 {failed}")
    print(f"Output directory:       {output_dir}")
    print(f"{'='*70}\n")

    return {
        "total": len(results),
        "successful": successful,
        "failed": failed,
        "results": results,
    }


def main():
    """
    Main processing function.
    Configure your input/output paths here.
    """
    print("=" * 70)
    print("COMPLETE X-RAY IMAGE PROCESSING PIPELINE")
    print("=" * 70)
    print("\nProcessing steps:")
    print("  1. Crop & Rotate by detector type:")
    print("      - TRX: crop configurable pixels each side, rotate 90° CCW")
    print("      - BED: crop configurable pixels each side")
    print("  2. Denoise (wavelet: configurable type, level, method, mode)")
    print("  3. Flat-Field Correction (FFC) with GPU acceleration")
    print("  4. Auto Thresholding (background separation)")
    print("  5. Invert")
    print("  6. Enhance Contrast (ImageJ method: configurable saturated pixels)")
    print("  7. CLAHE (ImageJ method: configurable parameters)")
    print("  8. Advanced Median Filter (7 types: ImageJ Hybrid is BEST for X-ray)")
    print("\nAdvanced Median Filter Types:")
    print("  - hybrid_imagej: ImageJ Hybrid 2D (BEST FOR X-RAY - edge preserving)")
    print("  - circular_imagej: ImageJ circular kernel (natural shape preservation)")
    print("  - bilateral: Edge-preserving filter (good for bone details)")
    print("  - adaptive: Adaptive median (best for salt-pepper noise)")
    print("  - nlm: Non-local means (preserves textures)")
    print("  - morphological: Shape-preserving morphological median")
    print("  - standard: Traditional scipy median (square kernel)")
    print("\nOptimizations:")
    print("  - GPU acceleration for FFC and array operations (CuPy)")
    print("  - Parallel batch processing (multiprocessing)")
    print("  - Configurable via .env file")
    print("=" * 70)

    # Example 1: Single image processing
    # Load paths from .env or use defaults
    raw_path = CONFIG.get("RAW_PATH") or r"test\BED_1765259553954_rad.tiff"
    dark_path = CONFIG.get("DARK_PATH") or r"test\BED_1765259553954_dark.tiff"
    flat_path = CONFIG.get("FLAT_PATH") or r"test\BED_1765259553954_gain.tiff"
    output_dir = CONFIG.get("OUTPUT_DIR") or r"test\output"

    # Ensure paths use raw strings for proper Windows path handling
    raw_path = rf"{raw_path}" if raw_path and "\\" not in raw_path else raw_path
    dark_path = rf"{dark_path}" if dark_path and "\\" not in dark_path else dark_path
    flat_path = rf"{flat_path}" if flat_path and "\\" not in flat_path else flat_path
    output_dir = (
        rf"{output_dir}" if output_dir and "\\" not in output_dir else output_dir
    )

    # Construct output path with proper filename and extension
    raw_filename = os.path.splitext(os.path.basename(raw_path))[0]
    output_path = os.path.join(output_dir, f"{raw_filename}_processed.tiff")
    success = process_single_image(raw_path, dark_path, flat_path, output_path)
    print(f"\nSingle image processing {'succeeded' if success else 'failed'}")

    # Example 2: Batch processing
    # image_list = [
    #     ("raw1.tiff", "dark.tiff", "flat1.tiff", None),  # Auto-detect detector
    #     ("raw2.tiff", "dark.tiff", "flat2.tiff", "TRX"),
    #     ("raw3.tiff", "dark.tiff", "flat3.tiff", "BED"),
    # ]
    # output_dir = "path/to/output_folder"
    # stats = batch_process_parallel(image_list, output_dir, num_workers=8)

    print("\nTo use this script:")
    print("  1. For single image: Call process_single_image()")
    print("  2. For batch: Call batch_process_parallel()")
    print("  3. Uncomment examples in main() and modify paths")
    print("\nRecommended .env settings for X-ray:")
    print("  USE_MEDIAN_FILTER=True")
    print("  MEDIAN_FILTER_TYPE=hybrid_imagej")
    print("  MEDIAN_FILTER_RADIUS=2")


if __name__ == "__main__":
    main()
