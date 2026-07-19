import os

file_path = "/var/www/mpips/mpips/engine/imager_pipeline/complete_pipeline.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Remove camera calibration imports and flags
content = content.replace("""        # Camera calibration
        "USE_CALIBRATION": False,
        "CALIBRATION_NPZ_PATH": "",
        "CALIBRATION_UNDISTORT_ALPHA": 0.0,""", "")

content = content.replace("""                        "CLAHE_FAST",
                        "CLAHE_COMPOSITE",
                        "USE_CALIBRATION",
                    ]:""", """                        "CLAHE_FAST",
                        "CLAHE_COMPOSITE",
                    ]:""")

content = content.replace("""                        "CONTRAST_SATURATED_PIXELS",
                        "NORMALIZE_SATURATED_PIXELS",
                        "CALIBRATION_UNDISTORT_ALPHA",
                    ]:""", """                        "CONTRAST_SATURATED_PIXELS",
                        "NORMALIZE_SATURATED_PIXELS",
                    ]:""")

content = content.replace("""# Import camera calibration
try:
    from .camera_calibration import undistort_image

    CALIBRATION_MODULE_AVAILABLE = True
except ImportError:
    CALIBRATION_MODULE_AVAILABLE = False
    print(
        "Warning: camera_calibration module not available. Camera calibration disabled."
    )""", "")

content = content.replace("""# Check if camera calibration should be used
CALIBRATION_AVAILABLE = (
    CALIBRATION_MODULE_AVAILABLE
    and CONFIG["USE_CALIBRATION"]
    and CONFIG["CALIBRATION_NPZ_PATH"]
    and os.path.exists(CONFIG["CALIBRATION_NPZ_PATH"])
)

if CALIBRATION_AVAILABLE:
    print(f"✓ Camera calibration enabled (NPZ: {CONFIG['CALIBRATION_NPZ_PATH']})")
elif CONFIG["USE_CALIBRATION"] and not CONFIG["CALIBRATION_NPZ_PATH"]:
    print("✗ Camera calibration disabled (CALIBRATION_NPZ_PATH not set)")
elif CONFIG["USE_CALIBRATION"] and not os.path.exists(CONFIG["CALIBRATION_NPZ_PATH"]):
    print(
        f"✗ Camera calibration disabled (NPZ file not found: {CONFIG['CALIBRATION_NPZ_PATH']})"
    )
elif not CALIBRATION_MODULE_AVAILABLE and CONFIG["USE_CALIBRATION"]:
    print("✗ Camera calibration disabled (camera_calibration module not available)")
else:
    print("✗ Camera calibration disabled (USE_CALIBRATION=False)")""", "")

# 2. Update docstring and signature of process_single_image
old_signature = """def process_single_image(
    raw_path, dark_path, flat_path, output_path, detector_type=None
):
    \"\"\"
    Process a single image through the complete pipeline.

    Pipeline:
    1. Crop and rotate all images (dark, gain, raw) by detector type
    2. Denoise dark, gain, raw using wavelet
    3. Calculate FFC
    4. Auto Thresholding
    5. Invert
    6. Enhance Contrast (ImageJ method: saturated=0.35%, normalize)
    7. CLAHE (ImageJ method: block_size=127, max_slope=1.5)

    Args:
        raw_path: Path to raw image
        dark_path: Path to dark calibration image
        flat_path: Path to flat/gain calibration image
        output_path: Path to save final result
        detector_type: 'BED' or 'TRX' (if None, auto-detect from filename)

    Returns:
        True if successful, False otherwise
    \"\"\""""

new_signature = """def process_single_image(
    raw_path, dark_path, flat_path, output_path, detector_type=None, map_x=None, map_y=None
):
    \"\"\"
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
    \"\"\""""
content = content.replace(old_signature, new_signature)

# 3. Replace steps 1 to 4 body
import re

old_steps_pattern = re.compile(
    r"    # Step 1: Apply camera calibration \(fish-eye correction\) before geometric transforms.*?# Step 4: FFC with matched dimensions\n    print\(\"  \[4/10\] Applying Flat-Field Correction\.\.\.\"\)\n    ffc_result = flat_field_correction\(raw_denoised, dark_denoised, flat_denoised\)\n    print\(f\"    FFC output range: \{ffc_result\.min\(\)\} - \{ffc_result\.max\(\)\}\"\)\n\n    save_histogram\(\n        ffc_result / ffc_result\.max\(\) if ffc_result\.max\(\) > 0 else ffc_result,\n        os\.path\.join\(debug_dir, f\"histogram_ffc_\{image_id\}\.png\"\),\n        title=\"FFC Result Histogram \(Normalized 0-1\)\",\n    \)\n",
    re.DOTALL
)

new_steps_code = """    # Step 1: Denoise using wavelet (on full-size arrays)
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
    if map_x is not None and map_y is not None:
        print("  [3/10] Applying neural calibration remap...")
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
    print(f"  [4/10] Cropping and rotating ({detector_type})...")

    ffc_result = crop_and_rotate_by_detector(ffc_result, detector_type)

    crop_info = f"top={CONFIG['CROP_TOP']}, bottom={CONFIG['CROP_BOTTOM']}, left={CONFIG['CROP_LEFT']}, right={CONFIG['CROP_RIGHT']}"
    if detector_type == "TRX":
        print(f"    Image: cropped ({crop_info}), rotated 90° CCW")
    else:
        print(f"    Image: cropped ({crop_info})")

    print(f"    Final shape: {ffc_result.shape}")

    save_histogram(
        ffc_result / ffc_result.max() if ffc_result.max() > 0 else ffc_result,
        os.path.join(debug_dir, f"histogram_cropped_{image_id}.png"),
        title="Cropped FFC Histogram",
    )
"""
if old_steps_pattern.search(content):
    content = old_steps_pattern.sub(new_steps_code, content)
else:
    print("ERROR: Did not find the steps 1-4 pattern.")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("SUCCESS: complete_pipeline.py updated.")
