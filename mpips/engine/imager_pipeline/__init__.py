"""Canonical MPIPS X-ray image processing pipeline.

This package provides the core processing modules used by the Madeena Node
Imager backend. The completed research implementation is preserved here as a
regular Python package with package-relative imports.

Install (editable) for local development::

    pip install -e '<repo-root>[imager]'

    from mpips.engine.imager_pipeline import complete_pipeline

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
