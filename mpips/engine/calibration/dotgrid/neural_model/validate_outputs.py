import argparse
import csv
import os
import sys

import numpy as np
import torch
from PIL import Image

from .dataset import load_data, parse_coord
from .evaluate import compute_all_metrics, load_model
from .model import apply_compensation, compute_compensated_diameters
from .phantom import CENTER_MARKER_MODES, detect_center_marker
from ..paths import default_artifact_path

REQUIRED_OUTPUTS = [
    "advanced_metrics.txt",
    "metrics.txt",
    "compensated_coordinates.csv",
    "compensated_x_plot.png",
    "compensated_y_plot.png",
    "compensated_diameters_plot.png",
    "compensated_vertical_diameter_plot.png",
    "compensation_model.pth",
    "model_metadata.json",
]


def load_coordinate_csv(path):
    coords = []
    with open(path, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if row:
                coords.append([parse_coord(cell) for cell in row])
    return np.asarray(coords, dtype=np.float32)


def require(condition, message, failures):
    if not condition:
        failures.append(message)


def check_file_outputs(output_dir, failures):
    for filename in REQUIRED_OUTPUTS:
        path = os.path.join(output_dir, filename)
        require(os.path.isfile(path), f"Missing output: {path}", failures)
        if os.path.isfile(path):
            require(os.path.getsize(path) > 0, f"Empty output: {path}", failures)


def check_calibrated_image(
    image_path, calibrated_path, failures, allow_expanded_calibrated=False
):
    if not calibrated_path:
        return
    require(
        os.path.isfile(calibrated_path),
        f"Missing calibrated image: {calibrated_path}",
        failures,
    )
    if not os.path.isfile(calibrated_path):
        return

    calibrated = Image.open(calibrated_path)
    require(
        calibrated.size[0] > 0 and calibrated.size[1] > 0,
        "Calibrated image has invalid size",
        failures,
    )

    if image_path and os.path.isfile(image_path):
        raw = Image.open(image_path)
        if not allow_expanded_calibrated:
            require(
                calibrated.size == raw.size,
                f"Calibrated image size {calibrated.size} does not match raw image size {raw.size}",
                failures,
            )


def check_mask_image(calibrated_path, mask_path, failures):
    if not mask_path:
        return
    require(os.path.isfile(mask_path), f"Missing valid mask: {mask_path}", failures)
    if not os.path.isfile(mask_path):
        return

    mask = Image.open(mask_path)
    require(
        mask.size[0] > 0 and mask.size[1] > 0, "Valid mask has invalid size", failures
    )

    if calibrated_path and os.path.isfile(calibrated_path):
        calibrated = Image.open(calibrated_path)
        require(
            mask.size == calibrated.size,
            f"Valid mask size {mask.size} does not match calibrated image size {calibrated.size}",
            failures,
        )


def validate_outputs(
    coords_path,
    diams_path,
    model_path,
    output_dir,
    image_path=None,
    calibrated_path=None,
    mask_path=None,
    hidden_dim=64,
    csv_tolerance=0.01,
    min_straightness_reduction=50.0,
    min_reprojection_reduction=50.0,
    min_spacing_reduction=30.0,
    min_diameter_reduction=0.0,
    center_marker_mode="auto",
    center_marker_min_ratio=1.5,
    allow_expanded_calibrated=False,
):
    failures = []
    check_file_outputs(output_dir, failures)
    check_calibrated_image(
        image_path,
        calibrated_path,
        failures,
        allow_expanded_calibrated=allow_expanded_calibrated,
    )
    check_mask_image(calibrated_path, mask_path, failures)

    coords, diams = load_data(coords_path, diams_path)
    metal_ball_mask, marker_metadata = detect_center_marker(
        diams,
        mode=center_marker_mode,
        min_ratio=center_marker_min_ratio,
    )
    model = load_model(model_path, hidden_dim=hidden_dim)
    norm_scale = torch.max(coords)

    with torch.no_grad():
        coords_comp = apply_compensation(model, coords, norm_scale)
        diams_comp = compute_compensated_diameters(model, coords, diams, norm_scale)

    before = compute_all_metrics(
        coords.numpy(), diams.numpy(), diameter_mask=metal_ball_mask
    )
    after = compute_all_metrics(
        coords_comp.numpy(), diams_comp.numpy(), diameter_mask=metal_ball_mask
    )

    csv_path = os.path.join(output_dir, "compensated_coordinates.csv")
    if os.path.isfile(csv_path):
        csv_coords = load_coordinate_csv(csv_path)
        require(
            csv_coords.shape == tuple(coords_comp.shape),
            f"Compensated CSV shape {csv_coords.shape} does not match model output {tuple(coords_comp.shape)}",
            failures,
        )
        if csv_coords.shape == tuple(coords_comp.shape):
            max_diff = float(np.max(np.abs(csv_coords - coords_comp.numpy())))
            require(
                max_diff <= csv_tolerance,
                f"Compensated CSV is stale or inconsistent: max diff {max_diff:.6f}px > {csv_tolerance}px",
                failures,
            )

    def reduction(before_value, after_value):
        return (before_value - after_value) / abs(before_value) * 100.0

    straightness_reduction = reduction(before["col_rmse"], after["col_rmse"])
    reprojection_reduction = reduction(before["reproj"], after["reproj"])
    spacing_x_reduction = reduction(before["spacing_x_std"], after["spacing_x_std"])
    spacing_y_reduction = reduction(before["spacing_y_std"], after["spacing_y_std"])
    diameter_reduction = reduction(before["diam_std"], after["diam_std"])

    require(
        straightness_reduction >= min_straightness_reduction,
        f"Straightness reduction too low: {straightness_reduction:.2f}%",
        failures,
    )
    require(
        reprojection_reduction >= min_reprojection_reduction,
        f"Reprojection reduction too low: {reprojection_reduction:.2f}%",
        failures,
    )
    require(
        min(spacing_x_reduction, spacing_y_reduction) >= min_spacing_reduction,
        f"Spacing reduction too low: x={spacing_x_reduction:.2f}%, y={spacing_y_reduction:.2f}%",
        failures,
    )
    require(
        diameter_reduction >= min_diameter_reduction,
        f"Diameter reduction too low: {diameter_reduction:.2f}%",
        failures,
    )

    print("Validation metrics:")
    print(
        f"  Straightness RMSE: {before['col_rmse']:.4f}px -> {after['col_rmse']:.4f}px ({straightness_reduction:.2f}% reduction)"
    )
    print(
        f"  Reprojection RMSE: {before['reproj']:.4f}px -> {after['reproj']:.4f}px ({reprojection_reduction:.2f}% reduction)"
    )
    print(
        f"  Spacing StdDev X: {before['spacing_x_std']:.4f}px -> {after['spacing_x_std']:.4f}px ({spacing_x_reduction:.2f}% reduction)"
    )
    print(
        f"  Spacing StdDev Y: {before['spacing_y_std']:.4f}px -> {after['spacing_y_std']:.4f}px ({spacing_y_reduction:.2f}% reduction)"
    )
    print(
        f"  Metal-ball Diameter StdDev: {before['diam_std']:.4f}px -> {after['diam_std']:.4f}px ({diameter_reduction:.2f}% reduction)"
    )
    if marker_metadata["detected_marker_count"]:
        row, col = marker_metadata["marker_index_1based"]
        print(f"  Center marker excluded from diameter metrics: row {row}, col {col}")

    if failures:
        print("\nValidation failed:")
        for failure in failures:
            print(f"  - {failure}")
        return False

    print("\nValidation passed.")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Validate generated neural model outputs."
    )
    parser.add_argument(
        "--coords", default=default_artifact_path("output/grid_coordinates.csv")
    )
    parser.add_argument(
        "--diams", default=default_artifact_path("output/grid_diameters.csv")
    )
    parser.add_argument(
        "--model",
        default=default_artifact_path("output/neural_model/compensation_model.pth"),
    )
    parser.add_argument(
        "--out-dir", default=default_artifact_path("output/neural_model")
    )
    parser.add_argument(
        "--image", default=default_artifact_path("data/lowanu-bed-kalibrasi.tiff")
    )
    parser.add_argument(
        "--calibrated",
        default=default_artifact_path("output/neural_model/calibrated_image.tiff"),
    )
    parser.add_argument(
        "--mask",
        default=default_artifact_path("output/neural_model/calibrated_valid_mask.png"),
    )
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--csv-tolerance", type=float, default=0.01)
    parser.add_argument(
        "--center-marker-mode", choices=CENTER_MARKER_MODES, default="auto"
    )
    parser.add_argument("--center-marker-min-ratio", type=float, default=1.5)
    parser.add_argument("--allow-expanded-calibrated", action="store_true")
    args = parser.parse_args()

    ok = validate_outputs(
        args.coords,
        args.diams,
        args.model,
        args.out_dir,
        image_path=args.image,
        calibrated_path=args.calibrated,
        mask_path=args.mask,
        hidden_dim=args.hidden_dim,
        csv_tolerance=args.csv_tolerance,
        center_marker_mode=args.center_marker_mode,
        center_marker_min_ratio=args.center_marker_min_ratio,
        allow_expanded_calibrated=args.allow_expanded_calibrated,
    )
    sys.exit(0 if ok else 1)
