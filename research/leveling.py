import gc
from pathlib import Path
import cv2
import cupy as cp
import numpy as np
import tifffile as tiff
from cupyx.scipy.ndimage import median_filter, uniform_filter

# ==============================================================================
# CONFIGURATION SETTINGS
# ==============================================================================
CALIBRATION_FILE = Path("img/calibration_params.npz")
INPUT_DIR = Path("img/coal")
OUTPUT_DIR = Path("img/level")

# Define a bounding box (y1, y2, x1, x2) in pixels that stays completely
# inside the clear background / open beam area to calculate intensity drift.
BACKGROUND_ROI = (918, 1018, 1050, 1150)

# ==============================================================================
# PIPELINE FUNCTIONS
# ==============================================================================


def crop_image(image, roi):
    """Crops an image matrix using an ROI bounding box (x, y, w, h)."""
    x, y, w, h = roi
    return image[y : y + h, x : x + w]


def undistort(mtx, dist, image):
    """Applies geometric distortion correction using a native float32 remapping matrix."""
    h, w = image.shape[:2]
    # Re-calculate camera matrix and retrieve post-rotation bounding box
    newcameramtx, roi_rotate = cv2.getOptimalNewCameraMatrix(
        mtx, dist, (w, h), 1, (w, h)
    )

    # Build transformation map coordinate lookup tables
    mapx, mapy = cv2.initUndistortRectifyMap(
        mtx, dist, None, newcameramtx, (w, h), cv2.CV_32FC1
    )

    # Remap the float32 array coordinates smoothly via bilinear interpolation
    undistorted_image = cv2.remap(image, mapx, mapy, cv2.INTER_LINEAR)

    # Crop the image to isolate valid pixels
    return crop_image(undistorted_image, roi_rotate)


# ==============================================================================
# MAIN BATCH PROCESSING PIPELINE
# ==============================================================================


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Read raw reference files
    reference_gain = cv2.imread(
        str(INPUT_DIR / "GAIN.tiff"), cv2.IMREAD_UNCHANGED
    )
    reference_dark = cv2.imread(
        str(INPUT_DIR / "DARK.tiff"), cv2.IMREAD_UNCHANGED
    )

    if reference_gain is None:
        raise FileNotFoundError(
            f"Could not read gain reference: {INPUT_DIR / 'GAIN.tiff'}"
        )
    if reference_dark is None:
        raise FileNotFoundError(
            f"Could not read dark reference: {INPUT_DIR / 'DARK.tiff'}"
        )

    print("Pre-filtering reference images on GPU...")
    # 2. Pre-process and filter references ONCE on GPU to save processing time
    gain_gpu = cp.asarray(reference_gain, dtype=cp.float32)
    gain_gpu = median_filter(gain_gpu, 3)
    gain_filtered = uniform_filter(gain_gpu, 7)

    dark_gpu = cp.asarray(reference_dark, dtype=cp.float32)
    dark_gpu = median_filter(dark_gpu, 3)
    dark_filtered = uniform_filter(dark_gpu, 7)

    # Calculate pre-filtered gain-dark denominator once
    gaindark = cp.subtract(gain_filtered, dark_filtered)
    gaindark[gaindark <= 0] = 0.0

    # Clean up temporary GPU references (Keep dark_filtered alive for the loop)
    del gain_gpu, dark_gpu, gain_filtered
    cp.get_default_memory_pool().free_all_blocks()

    # 3. Load geometric camera calibration matrices
    with np.load(CALIBRATION_FILE) as params:
        mtx = params["mtx"]
        dist = params["dist"]

    reference_roi_mean = None
    processed_count = 0

    print("Beginning batch processing...")
    for image_path in sorted(INPUT_DIR.glob("*.tif*")):
        # Skip reference files in the loop
        if image_path.name.upper() in {"GAIN.TIFF", "DARK.TIFF"}:
            continue

        source_image = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
        if source_image is None:
            print(f"Skipping unreadable image: {image_path.name}")
            continue

        # 4. Streamlined In-Loop FFC Math
        proj_gpu = cp.asarray(source_image, dtype=cp.float32)
        proj_gpu = median_filter(proj_gpu, 3)
        proj_filtered = uniform_filter(proj_gpu, 7)

        projdark = cp.subtract(proj_filtered, dark_filtered)
        projdark[projdark <= 0] = 0.0

        # True ImageJ matching forward division logic
        intensity_gpu = cp.where(projdark > 0, gaindark / projdark, 0.0)

        # 5. Global Brightness Leveling
        y1, y2, x1, x2 = BACKGROUND_ROI
        roi_zone = intensity_gpu[y1:y2, x1:x2]
        current_roi_mean = float(cp.mean(roi_zone))

        if reference_roi_mean is None:
            # The very first image sets the target baseline brightness level
            reference_roi_mean = current_roi_mean
            print(
                f"Baseline brightness ROI mean established: {reference_roi_mean:.4f}"
            )
        else:
            if current_roi_mean > 0:
                # Compute and apply correction scaling ratio
                scale_factor = reference_roi_mean / current_roi_mean
                intensity_gpu *= scale_factor

        # 6. Pull corrected array back to CPU NumPy
        ffc_numpy = intensity_gpu.get()

        # 7. Apply spatial distortion correction
        corrected_image = undistort(mtx, dist, ffc_numpy)

        # 8. Save directly to float32 OME-TIFF
        output_path = OUTPUT_DIR / image_path.name
        tiff.imwrite(str(output_path), corrected_image, imagej=True)

        processed_count += 1
        print(f"Saved leveled float32 image [{processed_count}]: {output_path}")

        # 9. Complete garbage collection cycle to keep memory low
        del (
            source_image,
            proj_gpu,
            proj_filtered,
            projdark,
            intensity_gpu,
            ffc_numpy,
            corrected_image,
        )
        cp.get_default_memory_pool().free_all_blocks()
        gc.collect()

    print(
        f"\nDone! Processed {processed_count} image(s) into pure float32 format at: {OUTPUT_DIR}"
    )


if __name__ == "__main__":
    main()
