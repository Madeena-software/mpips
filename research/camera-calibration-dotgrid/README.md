# Camera Calibration Dot Grid Compensator

This repository contains tools and scripts for advanced camera lens calibration and target deformation correction using a physical dot grid target.

Traditional camera calibration often relies on the Brown-Conrady polynomial model, which can struggle with complex, non-linear deformations in the physical calibration target itself. This project explores both traditional visualization techniques and an advanced **Physics-Informed Neural Network (PINN)** approach to learn and correct these distortions end-to-end.

## Project Structure

- **`data/`**: Contains the raw, uncalibrated high-resolution TIFF images (e.g., `lowanu-bed-kalibrasi.tiff`).
- **`src/`**: Contains the primary Python source code.
  - **Legacy Scripts**: Scripts like `extract_grid.py`, `plot_actual_coordinates.py`, and `plot_diameter.py` are used to extract and visualize the initial, distorted dot coordinate and diameter data from the raw images.
  - **`neural_model/`**: Contains the advanced PyTorch neural network implementation for end-to-end distortion compensation.
  - **`opencv_baseline/`**: Runs an OpenCV Brown-Conrady calibration baseline from the same extracted dot grid and compares it with the neural result.
- **`output/`**: Stores the extracted CSV data (`grid_coordinates.csv`, `grid_diameters.csv`) and all generated plots. The `output/neural_model/` subdirectory contains the final calibrated TIFF image and advanced evaluation metrics. The `output/opencv_baseline/` subdirectory contains the OpenCV undistorted image, calibration parameters, and comparison report.
- **`references/`**: Contains the academic literature and papers (e.g., Kelei Wang's papers on neural compensation) that form the mathematical basis for this project.

## Getting Started

1. Activate the Python virtual environment:
   ```bash
   source venv/bin/activate
   ```
2. Install dependencies when creating a fresh environment:
   ```bash
   pip install -r requirements.txt
   ```
3. For traditional extraction and visualization, run the scripts in the `src/` directory.
4. Run the neural compensation pipeline plus the OpenCV comparison:
   ```bash
   venv/bin/python src/neural_model/run_pipeline.py
   ```
   See `src/neural_model/README.md` for details and quality/runtime options.

To regenerate only the OpenCV baseline and comparison report:

```bash
venv/bin/python src/opencv_baseline/calibrate_and_compare.py
```

The main comparison is written to `output/opencv_baseline/comparison_report.md`.

To apply the neural correction without clipping corrected edge content, use the
expanded canvas mode:

```bash
venv/bin/python src/neural_model/warp_image.py --canvas-mode expanded
```

The expanded TIFF is larger than the source image and is accompanied by metadata
that records the output coordinate offset.

## Methodology

This project builds upon recent research in end-to-end neural compensation. Rather than estimating strict radial/tangential polynomials, it uses a Multi-Layer Perceptron (MLP) to learn a continuous compensation field that improves grid straightness, spacing consistency, and same-size metal-ball diameter consistency. The oversized center nut is treated as a fiducial marker: its coordinate remains in the grid, but its diameter is excluded from diameter loss, metrics, and plots.

The OpenCV baseline is intentionally kept as a parametric single-view Brown-Conrady comparison. It is useful for quantifying how far a standard OpenCV calibration gets on this dot grid, while the neural model remains the method used for residual lens and target deformation compensation.
