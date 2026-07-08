"""madeena-imager — X-ray image processing pipeline.

This package provides the core processing modules used by the Madeena Node
Imager backend.  Individual modules are imported directly because they were
originally standalone scripts; each module is therefore importable at the
top-level once the package (or its parent directory) is on ``sys.path``.

Install (editable) for local development::

    pip install -e <repo-root>/imager-pipeline

Or import directly after ensuring the package directory is on ``sys.path``
(the backend's ``pipeline_processors.py`` handles this automatically).

Public modules
--------------
complete_pipeline
    Full X-ray image processing pipeline — FFC, wavelet denoising,
    auto-thresholding, inversion, contrast enhancement, CLAHE, and optional
    camera calibration.
wavelet_denoising
    2-D wavelet-transform denoising and background removal using PyWavelets.
imagej_replicator
    Pure-Python replicas of ImageJ processing functions: Enhance Contrast,
    CLAHE, Median Filter, and Hybrid Median Filter.
camera_calibration
    Fish-eye distortion calibration (circle-grid pattern) and undistortion
    using OpenCV.  Outputs/reads NPZ calibration files.
build_image_pairs
    Scan a folder tree and pair raw images with their dark / gain calibration
    counterparts based on detector type and acquisition parameters.
tiff_json_to_dcm
    Convert a processed TIFF image plus its JSON metadata sidecar to a
    minimal DICOM file.
process_without_ffc
    Simplified pipeline that skips the flat-field correction step; useful for
    images that do not require FFC.
"""
