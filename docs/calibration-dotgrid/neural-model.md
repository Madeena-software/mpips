# Neural Calibration Model

This module implements a neural compensation system for correcting dot-grid target deformation and lens distortion in camera calibration images.

Unlike traditional parametric models such as Brown-Conrady, this model uses a Multi-Layer Perceptron (MLP) to produce a continuous spatial compensation field. It is trained from self-supervised geometric constraints on the extracted grid points: row/column straightness, spacing consistency, and metal-ball diameter consistency.

The phantom uses an oversized center nut as a fiducial marker. Its center coordinate remains part of the grid geometry, but its diameter is excluded from diameter loss, metrics, and plots by the default center-marker auto-detection.

## Files and Scripts

- **`dataset.py`**: Loads and validates extracted dot grid coordinates and diameters from CSV files, and writes compensated coordinates back to CSV.
- **`phantom.py`**: Detects the oversized center nut marker and returns the metal-ball mask used by training, evaluation, validation, and comparison reports.
- **`model.py`**: Defines `MLPCompensation`, shared forward/inverse compensation helpers, and losses for collinearity, grid spacing, SMIA-style edge balance, diameter compensation, and warp smoothness.
- **`train.py`**: Executes deterministic training, saves the best model weights, and writes `model_metadata.json`.
- **`evaluate.py`**: Regenerates every evaluation artifact from the current model, including:
  - **SMIA TV Distortion**
  - **Homography Reprojection Error (RMSE)**
  - **OpenCV Estimated Brown-Conrady Coefficients**
  - **Orthogonal Straightness RMSE**
  - **Metal-ball Diameter StdDev** with the center marker excluded when detected
  - **Horizontal/Vertical Spacing StdDev**
  It also writes `metrics.txt`, `advanced_metrics.txt`, `compensated_coordinates.csv`, and the compensated plot PNGs.
- **`warp_image.py`**: Applies the trained compensation field to the original high-resolution TIFF with OpenCV `remap`. The remap field is computed with an iterative inverse solve, which is more geometrically valid than subtracting the model offset once at the destination coordinate.
- **`validate_outputs.py`**: Checks that generated files exist, `compensated_coordinates.csv` matches the current model, metric reductions meet minimum thresholds, and the calibrated image shape matches the source image.
- **`../opencv_baseline/calibrate_and_compare.py`**: Runs OpenCV `calibrateCamera`, undistorts the dot coordinates and source image, then writes a side-by-side comparison against the neural result.
- **`run_pipeline.py`**: Runs train, evaluate, OpenCV comparison, warp, and validation in one command.

## Usage Workflow

Run the modules from the repository root after installing `.[calibration]`.

### One-command pipeline

```bash
mpips-dotgrid
```

This runs training, evaluation, OpenCV comparison, image warp, and output validation with the default baseline settings. By default, `--center-marker-mode auto` excludes the oversized center nut from diameter-only calculations when it is at least `1.5x` the median diameter of the grid.

### Individual steps

1. **Train the Model**:
   ```bash
   python -m mpips.engine.calibration.dotgrid.neural_model.train
   ```
   This reads `output/grid_coordinates.csv` and `output/grid_diameters.csv`, then writes:
   - `output/neural_model/compensation_model.pth`
   - `output/neural_model/model_metadata.json`

2. **Evaluate and Regenerate Artifacts**:
   ```bash
   python -m mpips.engine.calibration.dotgrid.neural_model.evaluate
   ```
   This writes the metrics, compensated coordinate CSV, and compensated plots into `output/neural_model/`.

3. **Run the OpenCV Comparison**:
   ```bash
   python -m mpips.engine.calibration.dotgrid.opencv_baseline.calibrate_and_compare
   ```
   This writes:
   - `output/opencv_baseline/comparison_report.md`
   - `output/opencv_baseline/comparison_metrics.csv`
   - `output/opencv_baseline/opencv_parameters.json`
   - `output/opencv_baseline/undistorted_coordinates.csv`
   - `output/opencv_baseline/undistorted_image.tiff`
   - `output/opencv_baseline/comparison_bar_metrics.png`

   The one-command pipeline also runs this step by default. Use `--skip-opencv-comparison` to omit it or `--opencv-skip-image` to skip writing the undistorted TIFF.

4. **Warp the Image**:
   ```bash
   python -m mpips.engine.calibration.dotgrid.neural_model.warp_image --step 4 --iterations 10
   ```
   This reads `data/lowanu-bed-kalibrasi.tiff` and writes:
   - `output/neural_model/calibrated_image.tiff`
   - `output/neural_model/calibrated_valid_mask.png`

   Use `--step 1` for dense inverse mapping when maximum geometric fidelity matters more than runtime.

   To preserve edge content that would otherwise leave the original `4096x3000`
   frame, write an expanded canvas:
   ```bash
   python -m mpips.engine.calibration.dotgrid.neural_model.warp_image \
     --canvas-mode expanded \
     --out output/neural_model/calibrated_image_expanded.tiff \
     --mask-out output/neural_model/calibrated_valid_mask_expanded.png
   ```
   This also writes `output/neural_model/calibrated_image_expanded_metadata.json`
   unless `--metadata-out` is provided. The metadata records the corrected-domain
   origin offset needed to interpret output pixel coordinates.

5. **Validate Outputs**:
   ```bash
   python -m mpips.engine.calibration.dotgrid.neural_model.validate_outputs
   ```
   This fails with a non-zero exit code if generated artifacts are stale, missing, or below the minimum quality thresholds.

## Current Baseline

The current regenerated baseline reduces:

- Homography reprojection RMSE from `23.9444 px` to `2.2589 px`
- Orthogonal straightness RMSE from `13.7757 px` to `1.2281 px`
- SMIA vertical distortion from `-1.9521%` to `0.3578%`
- SMIA horizontal distortion from `0.2687%` to `0.2046%`
- Horizontal spacing StdDev from `6.4361 px` to `1.7401 px`
- Vertical spacing StdDev from `5.3181 px` to `1.3863 px`
- Metal-ball Diameter StdDev from `1.5121 px` to `1.2038 px`

The center nut marker is detected at row `10`, column `13` in the current `19 x 26` grid and is excluded from the metal-ball diameter metric.

The warped image still has black borders where the corrected field samples outside the source image. The default warp reports the out-of-bounds fraction during execution.

## Current OpenCV Comparison

The OpenCV Brown-Conrady baseline is generated from the same extracted dot grid. The current comparison report shows:

- OpenCV calibration RMS reprojection error: `2.5476 px`
- Homography reprojection RMSE: raw `23.9444 px`, OpenCV `2.7912 px`, neural `2.2589 px`
- Orthogonal straightness RMSE: raw `13.7757 px`, OpenCV `9.0741 px`, neural `1.2281 px`
- Horizontal spacing StdDev: raw `6.4361 px`, OpenCV `1.8824 px`, neural `1.7401 px`
- Vertical spacing StdDev: raw `5.3181 px`, OpenCV `1.8058 px`, neural `1.3863 px`
- Metal-ball Diameter StdDev: raw `1.5121 px`, OpenCV `1.3542 px`, neural `1.2038 px`

Because this OpenCV baseline uses one image/view, the fitted focal length and distortion coefficients should be treated as a comparison baseline rather than a fully constrained production camera calibration.

## Handling Black Borders

Black borders are expected when corrected destination pixels map outside the raw source image. The full-size TIFF keeps the original `4096x3000` frame, which is usually the safest output for measurement pipelines.

Options:

- Keep the full image and use `calibrated_valid_mask.png` to ignore invalid pixels.
- Use expanded canvas when edge content must remain visible:
  ```bash
  python -m mpips.engine.calibration.dotgrid.neural_model.warp_image --canvas-mode expanded
  ```
  The current model writes about `4147x3060` with origin `(-133, 75)` when using
  the default expanded bounds settings. This avoids clipping the bottom phantom row while
  preserving pixel scale; consumers must read the metadata JSON for the output
  coordinate offset.
- Generate a no-border crop:
  ```bash
  python -m mpips.engine.calibration.dotgrid.neural_model.warp_image --crop-valid
  ```
  This writes `output/neural_model/calibrated_image_cropped.tiff`.
- Hide borders for visual inspection only:
  ```bash
  python -m mpips.engine.calibration.dotgrid.neural_model.warp_image --border-mode replicate
  ```
  This fills invalid pixels from the nearest source edge; it should not be treated as real calibrated image data.
