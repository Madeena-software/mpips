import argparse
import os

import cv2
import matplotlib
import numpy as np
import torch

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from dataset import load_data, save_coordinates
from model import MLPCompensation, apply_compensation, compute_compensated_diameters
from phantom import CENTER_MARKER_MODES, detect_center_marker


def load_model(model_path, hidden_dim=64):
    model = MLPCompensation(hidden_dim=hidden_dim)
    try:
        state_dict = torch.load(model_path, map_location="cpu", weights_only=True)
    except TypeError:
        state_dict = torch.load(model_path, map_location="cpu")
    model.load_state_dict(state_dict)
    model.eval()
    return model


def compute_smia(coords_np):
    rows, cols = coords_np.shape[:2]
    mid_col = cols // 2
    mid_row = rows // 2

    b_h = coords_np[-1, mid_col, 1] - coords_np[0, mid_col, 1]
    a_h = (
        (coords_np[-1, 0, 1] - coords_np[0, 0, 1])
        + (coords_np[-1, -1, 1] - coords_np[0, -1, 1])
    ) / 2.0
    smia_v = (a_h - b_h) / b_h * 100.0 if b_h != 0 else np.nan

    b_w = coords_np[mid_row, -1, 0] - coords_np[mid_row, 0, 0]
    a_w = (
        (coords_np[0, -1, 0] - coords_np[0, 0, 0])
        + (coords_np[-1, -1, 0] - coords_np[-1, 0, 0])
    ) / 2.0
    smia_h = (a_w - b_w) / b_w * 100.0 if b_w != 0 else np.nan
    return smia_v, smia_h


def compute_reprojection_error(coords_np):
    rows, cols = coords_np.shape[:2]
    spacing_x = (coords_np[rows // 2, -1, 0] - coords_np[rows // 2, 0, 0]) / (cols - 1)
    spacing_y = (coords_np[-1, cols // 2, 1] - coords_np[0, cols // 2, 1]) / (rows - 1)
    ideal_grid = np.zeros_like(coords_np)
    for r in range(rows):
        for c in range(cols):
            ideal_grid[r, c] = [c * spacing_x, r * spacing_y]

    pts_src = coords_np.reshape(-1, 2).astype(np.float32)
    pts_dst = ideal_grid.reshape(-1, 2).astype(np.float32)
    homography, _ = cv2.findHomography(pts_src, pts_dst)
    if homography is None:
        return np.nan

    pts_src_hom = np.concatenate([pts_src, np.ones((len(pts_src), 1))], axis=1)
    proj_pts = (homography @ pts_src_hom.T).T
    proj_pts = proj_pts[:, :2] / proj_pts[:, 2:3]
    return np.sqrt(np.mean(np.sum((proj_pts - pts_dst) ** 2, axis=1)))


def estimate_brown_conrady(coords_np, image_size):
    rows, cols = coords_np.shape[:2]
    objp = np.zeros((rows * cols, 3), np.float32)
    objp[:, :2] = np.mgrid[0:cols, 0:rows].T.reshape(-1, 2) * 30.0

    imgpoints = [coords_np.reshape(-1, 2).astype(np.float32)]
    objpoints = [objp]

    width, height = image_size
    camera_matrix = np.array(
        [[width, 0, width / 2], [0, width, height / 2], [0, 0, 1]],
        dtype=np.float32,
    )
    flags = cv2.CALIB_USE_INTRINSIC_GUESS | cv2.CALIB_FIX_PRINCIPAL_POINT
    try:
        _, _, dist, _, _ = cv2.calibrateCamera(
            objpoints, imgpoints, (width, height), camera_matrix, None, flags=flags
        )
        dist = dist.flatten()
        return dist[0], dist[1], dist[4]
    except cv2.error:
        return np.nan, np.nan, np.nan


def _diameter_values(diams_np, diameter_mask=None):
    if diameter_mask is None:
        return np.asarray(diams_np).reshape(-1)

    mask = np.asarray(diameter_mask, dtype=bool)
    if mask.shape != diams_np.shape:
        raise ValueError(
            f"Diameter mask shape {mask.shape} does not match diameters {diams_np.shape}"
        )
    values = np.asarray(diams_np)[mask]
    if values.size == 0:
        raise ValueError("Diameter mask excludes every diameter")
    return values


def compute_all_metrics(
    coords_np, diams_np, image_size=(4096, 3000), diameter_mask=None
):
    row_y_var = [np.var(coords_np[r, :, 1]) for r in range(coords_np.shape[0])]
    col_x_var = [np.var(coords_np[:, c, 0]) for c in range(coords_np.shape[1])]
    col_rmse = np.sqrt(np.mean(col_x_var + row_y_var))

    row_dx = coords_np[:, 1:, 0] - coords_np[:, :-1, 0]
    col_dy = coords_np[1:, :, 1] - coords_np[:-1, :, 1]
    smia_v, smia_h = compute_smia(coords_np)
    reproj_rmse = compute_reprojection_error(coords_np)
    k1, k2, k3 = estimate_brown_conrady(coords_np, image_size)
    diam_values = _diameter_values(diams_np, diameter_mask=diameter_mask)

    return {
        "col_rmse": float(col_rmse),
        "smia_v": float(smia_v),
        "smia_h": float(smia_h),
        "reproj": float(reproj_rmse),
        "k1": float(k1),
        "k2": float(k2),
        "k3": float(k3),
        "diam_std": float(np.std(diam_values)),
        "diam_mean": float(np.mean(diam_values)),
        "diam_count": int(diam_values.size),
        "spacing_x_mean": float(np.mean(row_dx)),
        "spacing_x_std": float(np.std(row_dx)),
        "spacing_y_mean": float(np.mean(col_dy)),
        "spacing_y_std": float(np.std(col_dy)),
    }


def improvement_pct(before, after):
    if before == 0 or not np.isfinite(before) or not np.isfinite(after):
        return np.nan
    return (before - after) / abs(before) * 100.0


def format_center_marker_note(marker_metadata):
    if marker_metadata and marker_metadata.get("detected_marker_count"):
        row, col = marker_metadata["marker_index_1based"]
        diameter = marker_metadata["raw_marker_diameter"]
        return (
            "Diameter metrics use metal balls only; "
            f"center marker excluded at row {row}, col {col} "
            f"(raw diameter {diameter:.2f}px)."
        )
    return "Diameter metrics include all detected circles."


def write_basic_metrics(path, before, after, marker_metadata=None):
    straightness_improvement = improvement_pct(before["col_rmse"], after["col_rmse"])
    diameter_improvement = improvement_pct(before["diam_std"], after["diam_std"])
    spacing_x_improvement = improvement_pct(
        before["spacing_x_std"], after["spacing_x_std"]
    )
    spacing_y_improvement = improvement_pct(
        before["spacing_y_std"], after["spacing_y_std"]
    )

    metrics_str = f"""--- BEFORE CALIBRATION (Raw Extraction) ---
Orthogonal Straightness RMSE: {before['col_rmse']:.4f} pixels
Metal-ball Diameter StdDev: {before['diam_std']:.4f} pixels (Mean: {before['diam_mean']:.2f}px, N: {before['diam_count']})
Horizontal Spacing StdDev: {before['spacing_x_std']:.4f} pixels (Mean: {before['spacing_x_mean']:.2f}px)
Vertical Spacing StdDev: {before['spacing_y_std']:.4f} pixels (Mean: {before['spacing_y_mean']:.2f}px)

--- AFTER CALIBRATION (Neural Compensation) ---
Orthogonal Straightness RMSE: {after['col_rmse']:.4f} pixels
Metal-ball Diameter StdDev: {after['diam_std']:.4f} pixels (Mean: {after['diam_mean']:.2f}px, N: {after['diam_count']})
Horizontal Spacing StdDev: {after['spacing_x_std']:.4f} pixels (Mean: {after['spacing_x_mean']:.2f}px)
Vertical Spacing StdDev: {after['spacing_y_std']:.4f} pixels (Mean: {after['spacing_y_mean']:.2f}px)

--- IMPROVEMENT ---
Straightness Error Reduced By: {straightness_improvement:.2f}%
Metal-ball Diameter Variance Reduced By: {diameter_improvement:.2f}%
Horizontal Spacing Error Reduced By: {spacing_x_improvement:.2f}%
Vertical Spacing Error Reduced By: {spacing_y_improvement:.2f}%

{format_center_marker_note(marker_metadata)}
"""
    with open(path, "w") as f:
        f.write(metrics_str)


def write_advanced_metrics(path, before, after, marker_metadata=None):
    reproj_improvement = improvement_pct(before["reproj"], after["reproj"])
    straightness_improvement = improvement_pct(before["col_rmse"], after["col_rmse"])
    diameter_improvement = improvement_pct(before["diam_std"], after["diam_std"])
    spacing_x_improvement = improvement_pct(
        before["spacing_x_std"], after["spacing_x_std"]
    )
    spacing_y_improvement = improvement_pct(
        before["spacing_y_std"], after["spacing_y_std"]
    )

    metrics_str = f"""==================================================
ADVANCED CALIBRATION METRICS
==================================================

1. SMIA TV Distortion (Percentage)
   Before : Vertical = {before['smia_v']:.4f}% | Horizontal = {before['smia_h']:.4f}%
   After  : Vertical = {after['smia_v']:.4f}% | Horizontal = {after['smia_h']:.4f}%

2. Reprojection Error (Homography RMSE)
   Before : {before['reproj']:.4f} pixels
   After  : {after['reproj']:.4f} pixels
   Change : {reproj_improvement:.2f}% reduction

3. Brown-Conrady Radial Distortion Coefficients (Estimated via OpenCV)
   Before : k1 = {before['k1']:.4e} | k2 = {before['k2']:.4e} | k3 = {before['k3']:.4e}
   After  : k1 = {after['k1']:.4e} | k2 = {after['k2']:.4e} | k3 = {after['k3']:.4e}
   Note   : These coefficients are a diagnostic fit only; the neural model does not use k1/k2/k3 internally.

4. Collinearity Error (Orthogonal Straightness RMSE)
   Before : {before['col_rmse']:.4f} pixels
   After  : {after['col_rmse']:.4f} pixels
   Change : {straightness_improvement:.2f}% reduction

5. Target Deformation (Metal-ball Diameter StdDev)
   Before : {before['diam_std']:.4f} pixels (Mean: {before['diam_mean']:.2f}px, N: {before['diam_count']})
   After  : {after['diam_std']:.4f} pixels (Mean: {after['diam_mean']:.2f}px, N: {after['diam_count']})
   Change : {diameter_improvement:.2f}% reduction

6. Grid Spacing Consistency (StdDev)
   Horizontal Before/After : {before['spacing_x_std']:.4f}px -> {after['spacing_x_std']:.4f}px ({spacing_x_improvement:.2f}% reduction)
   Vertical Before/After   : {before['spacing_y_std']:.4f}px -> {after['spacing_y_std']:.4f}px ({spacing_y_improvement:.2f}% reduction)

{format_center_marker_note(marker_metadata)}
==================================================
"""
    with open(path, "w") as f:
        f.write(metrics_str)
    print(metrics_str)


def plot_compensated_x(coords_np, output_path):
    rows, cols = coords_np.shape[:2]
    plt.figure(figsize=(10, 6))
    for c in range(cols):
        plt.plot(range(rows), coords_np[:, c, 0], marker="o", markersize=3)
    plt.title("Compensated X Coordinates (Columns)")
    plt.xlabel("Row Index")
    plt.ylabel("X Position (Pixels)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def plot_compensated_y(coords_np, output_path):
    rows, cols = coords_np.shape[:2]
    plt.figure(figsize=(10, 6))
    for r in range(rows):
        plt.plot(range(cols), coords_np[r, :, 1], marker="o", markersize=3)
    plt.title("Compensated Y Coordinates (Rows)")
    plt.xlabel("Column Index")
    plt.ylabel("Y Position (Pixels)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def plot_diameter_hist(
    before_diams, after_diams, output_path, diameter_mask=None, marker_metadata=None
):
    before_values = _diameter_values(before_diams, diameter_mask=diameter_mask)
    after_values = _diameter_values(after_diams, diameter_mask=diameter_mask)

    plt.figure(figsize=(10, 6))
    bins = np.linspace(
        min(float(np.min(before_values)), float(np.min(after_values))),
        max(float(np.max(before_values)), float(np.max(after_values))),
        30,
    )
    plt.hist(before_values, bins=bins, alpha=0.45, color="gray", label="Before")
    plt.hist(after_values, bins=bins, alpha=0.65, color="purple", label="After")
    plt.axvline(
        float(np.mean(after_values)),
        color="red",
        linestyle="--",
        label=f"Mean = {np.mean(after_values):.2f}",
    )
    note = ""
    if marker_metadata and marker_metadata.get("detected_marker_count"):
        row, col = marker_metadata["marker_index_1based"]
        note = f"\nCenter marker excluded: row {row}, col {col}"
    plt.title(
        "Metal-ball Diameters Distribution (Before vs After)"
        f"\nStdDev: {np.std(after_values):.4f}px{note}"
    )
    plt.xlabel("Diameter (Pixels)")
    plt.ylabel("Frequency")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def plot_vertical_diameter_profile(
    after_diams, output_path, diameter_mask=None, marker_metadata=None
):
    rows, cols = after_diams.shape
    if diameter_mask is None:
        diameter_mask = np.ones(after_diams.shape, dtype=bool)
    else:
        diameter_mask = np.asarray(diameter_mask, dtype=bool)
        if diameter_mask.shape != after_diams.shape:
            raise ValueError(
                f"Diameter mask shape {diameter_mask.shape} does not match diameters {after_diams.shape}"
            )

    plt.figure(figsize=(10, 6))
    plotted_label = False
    for c in range(cols):
        row_indices = np.where(diameter_mask[:, c])[0]
        if row_indices.size:
            plt.scatter(
                row_indices + 1,
                after_diams[row_indices, c],
                alpha=0.5,
                color="purple",
                s=20,
                label="Metal balls" if not plotted_label else None,
            )
            plotted_label = True

    if marker_metadata and marker_metadata.get("detected_marker_count"):
        marker_row, marker_col = marker_metadata["marker_index_0based"]
        plt.scatter(
            [marker_row + 1],
            [after_diams[marker_row, marker_col]],
            color="red",
            s=55,
            label="Center marker",
            zorder=3,
        )

    plt.title("Compensated Metal-ball Diameter Profile (Center Marker Highlighted)")
    plt.xlabel("Row Number")
    plt.ylabel("Dot Diameter (pixels)")
    plt.xticks(range(1, rows + 1))
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def evaluate_model(
    model_path,
    coords_path,
    diams_path,
    output_dir,
    image_size=(4096, 3000),
    hidden_dim=64,
    center_marker_mode="auto",
    center_marker_min_ratio=1.5,
):
    os.makedirs(output_dir, exist_ok=True)
    coords, diams = load_data(coords_path, diams_path)
    metal_ball_mask, marker_metadata = detect_center_marker(
        diams,
        mode=center_marker_mode,
        min_ratio=center_marker_min_ratio,
    )
    norm_scale = torch.max(coords)

    model = load_model(model_path, hidden_dim=hidden_dim)

    with torch.no_grad():
        coords_comp = apply_compensation(model, coords, norm_scale)
        diams_comp = compute_compensated_diameters(model, coords, diams, norm_scale)

    coords_np = coords.detach().cpu().numpy()
    diams_np = diams.detach().cpu().numpy()
    coords_comp_np = coords_comp.detach().cpu().numpy()
    diams_comp_np = diams_comp.detach().cpu().numpy()

    before = compute_all_metrics(
        coords_np, diams_np, image_size=image_size, diameter_mask=metal_ball_mask
    )
    after = compute_all_metrics(
        coords_comp_np,
        diams_comp_np,
        image_size=image_size,
        diameter_mask=metal_ball_mask,
    )

    save_coordinates(
        coords_comp_np, os.path.join(output_dir, "compensated_coordinates.csv")
    )
    write_basic_metrics(
        os.path.join(output_dir, "metrics.txt"), before, after, marker_metadata
    )
    write_advanced_metrics(
        os.path.join(output_dir, "advanced_metrics.txt"), before, after, marker_metadata
    )
    plot_compensated_x(
        coords_comp_np, os.path.join(output_dir, "compensated_x_plot.png")
    )
    plot_compensated_y(
        coords_comp_np, os.path.join(output_dir, "compensated_y_plot.png")
    )
    plot_diameter_hist(
        diams_np,
        diams_comp_np,
        os.path.join(output_dir, "compensated_diameters_plot.png"),
        diameter_mask=metal_ball_mask,
        marker_metadata=marker_metadata,
    )
    plot_vertical_diameter_profile(
        diams_comp_np,
        os.path.join(output_dir, "compensated_vertical_diameter_plot.png"),
        diameter_mask=metal_ball_mask,
        marker_metadata=marker_metadata,
    )

    print(f"Evaluation complete. Results saved to {output_dir}")
    return before, after


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate neural compensation model.")
    parser.add_argument("--coords", default="output/grid_coordinates.csv")
    parser.add_argument("--diams", default="output/grid_diameters.csv")
    parser.add_argument("--model", default="output/neural_model/compensation_model.pth")
    parser.add_argument("--out-dir", default="output/neural_model")
    parser.add_argument("--image-width", type=int, default=4096)
    parser.add_argument("--image-height", type=int, default=3000)
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument(
        "--center-marker-mode", choices=CENTER_MARKER_MODES, default="auto"
    )
    parser.add_argument("--center-marker-min-ratio", type=float, default=1.5)
    args = parser.parse_args()

    evaluate_model(
        args.model,
        args.coords,
        args.diams,
        args.out_dir,
        image_size=(args.image_width, args.image_height),
        hidden_dim=args.hidden_dim,
        center_marker_mode=args.center_marker_mode,
        center_marker_min_ratio=args.center_marker_min_ratio,
    )
