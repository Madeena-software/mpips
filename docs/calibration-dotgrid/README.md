# Camera Calibration Dot Grid Compensator

This package contains tools and scripts for advanced camera lens calibration and target deformation correction using a physical dot grid target.

Traditional camera calibration often relies on the Brown-Conrady polynomial model, which can struggle with complex, non-linear deformations in the physical calibration target itself. This project explores both traditional visualization techniques and an advanced **Physics-Informed Neural Network (PINN)** approach to learn and correct these distortions end-to-end.

## Project Structure

- **`artifacts/camera-calibration-dotgrid/data/`**: Contains the raw, uncalibrated high-resolution TIFF images.
- **`mpips.engine.calibration.dotgrid`**: Contains the primary Python source code.
  - **Legacy Scripts**: Scripts like `extract_grid.py`, `plot_actual_coordinates.py`, and `plot_diameter.py` are used to extract and visualize the initial, distorted dot coordinate and diameter data from the raw images.
  - **`neural_model/`**: Contains the advanced PyTorch neural network implementation for end-to-end distortion compensation.
  - **`opencv_baseline/`**: Runs an OpenCV Brown-Conrady calibration baseline from the same extracted dot grid and compares it with the neural result.
- **`artifacts/camera-calibration-dotgrid/output/`**: Stores extracted data, models, calibrated images, and generated plots.
- **`artifacts/camera-calibration-dotgrid/references/`**: Contains the academic literature that forms the mathematical basis for this project.

## Getting Started

1. Activate the Python virtual environment:
   ```bash
   source .venv/bin/activate
   ```
2. Install dependencies when creating a fresh environment:
   ```bash
   pip install -e '.[calibration]'
   ```
3. Import extraction and visualization from `mpips.engine.calibration.dotgrid`.
4. Run the neural compensation pipeline plus the OpenCV comparison:
   ```bash
   mpips-dotgrid
   ```
   See `docs/calibration-dotgrid/neural-model.md` for quality/runtime options.

To regenerate only the OpenCV baseline and comparison report:

```bash
python -m mpips.engine.calibration.dotgrid.opencv_baseline.calibrate_and_compare
```

The main comparison is written to `output/opencv_baseline/comparison_report.md`.

To apply the neural correction without clipping corrected edge content, use the
expanded canvas mode:

```bash
python -m mpips.engine.calibration.dotgrid.neural_model.warp_image --canvas-mode expanded
```

The expanded TIFF is larger than the source image and is accompanied by metadata
that records the output coordinate offset.

## Methodology

This project builds upon recent research in end-to-end neural compensation. Rather than estimating strict radial/tangential polynomials, it uses a Multi-Layer Perceptron (MLP) to learn a continuous compensation field that improves grid straightness, spacing consistency, and same-size metal-ball diameter consistency. The oversized center nut is treated as a fiducial marker: its coordinate remains in the grid, but its diameter is excluded from diameter loss, metrics, and plots.

The OpenCV baseline is intentionally kept as a parametric single-view Brown-Conrady comparison. It is useful for quantifying how far a standard OpenCV calibration gets on this dot grid, while the neural model remains the method used for residual lens and target deformation compensation.
