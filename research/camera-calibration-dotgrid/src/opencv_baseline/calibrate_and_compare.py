import argparse
import csv
import json
import os
import sys
from pathlib import Path

import cv2
import matplotlib
import numpy as np
import torch

matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parents[2]
NEURAL_MODEL_DIR = REPO_ROOT / "src" / "neural_model"
if str(NEURAL_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(NEURAL_MODEL_DIR))

from dataset import load_data, save_coordinates
from evaluate import compute_all_metrics, load_model
from model import apply_compensation, compute_compensated_diameters
from phantom import CENTER_MARKER_MODES, detect_center_marker

METRIC_SPECS = [
    ("reproj", "Homography reprojection RMSE", "px", False),
    ("col_rmse", "Orthogonal straightness RMSE", "px", False),
    ("smia_v", "SMIA vertical distortion", "%", True),
    ("smia_h", "SMIA horizontal distortion", "%", True),
    ("spacing_x_std", "Horizontal spacing StdDev", "px", False),
    ("spacing_y_std", "Vertical spacing StdDev", "px", False),
    ("diam_std", "Metal-ball Diameter StdDev", "px", False),
]


def image_size_from_file(image_path, fallback_size):
    if not image_path:
        return fallback_size

    image = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError(f"Unable to read image: {image_path}")

    height, width = image.shape[:2]
    return width, height


def make_object_points(rows, cols, object_spacing):
    objp = np.zeros((rows * cols, 3), np.float32)
    objp[:, :2] = (
        np.mgrid[0:cols, 0:rows].T.reshape(-1, 2).astype(np.float32) * object_spacing
    )
    return objp


def calibrate_opencv(coords_np, image_size, object_spacing=30.0, fix_aspect=False):
    rows, cols = coords_np.shape[:2]
    objp = make_object_points(rows, cols, object_spacing)
    objpoints = [objp]
    imgpoints = [coords_np.reshape(-1, 1, 2).astype(np.float32)]

    width, height = image_size
    camera_matrix = np.array(
        [[width, 0.0, width / 2.0], [0.0, width, height / 2.0], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )
    flags = cv2.CALIB_USE_INTRINSIC_GUESS | cv2.CALIB_FIX_PRINCIPAL_POINT
    flag_names = ["CALIB_USE_INTRINSIC_GUESS", "CALIB_FIX_PRINCIPAL_POINT"]
    if fix_aspect:
        flags |= cv2.CALIB_FIX_ASPECT_RATIO
        flag_names.append("CALIB_FIX_ASPECT_RATIO")

    try:
        (
            rms,
            camera_matrix,
            dist_coeffs,
            rvecs,
            tvecs,
            std_intrinsics,
            std_extrinsics,
            per_view_errors,
        ) = cv2.calibrateCameraExtended(
            objpoints,
            imgpoints,
            image_size,
            camera_matrix,
            None,
            flags=flags,
        )
    except AttributeError:
        rms, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
            objpoints,
            imgpoints,
            image_size,
            camera_matrix,
            None,
            flags=flags,
        )
        std_intrinsics = None
        std_extrinsics = None
        per_view_errors = np.array([[rms]], dtype=np.float64)

    projected, _ = cv2.projectPoints(
        objp, rvecs[0], tvecs[0], camera_matrix, dist_coeffs
    )
    projected = projected.reshape(rows, cols, 2)

    return {
        "rms": float(rms),
        "camera_matrix": camera_matrix,
        "dist_coeffs": dist_coeffs,
        "rvec": rvecs[0],
        "tvec": tvecs[0],
        "projected_points": projected,
        "std_intrinsics": std_intrinsics,
        "std_extrinsics": std_extrinsics,
        "per_view_errors": per_view_errors,
        "flags": int(flags),
        "flag_names": flag_names,
        "object_spacing": float(object_spacing),
    }


def undistort_points(points_np, camera_matrix, dist_coeffs, output_camera_matrix):
    points = points_np.reshape(-1, 1, 2).astype(np.float32)
    corrected = cv2.undistortPoints(
        points,
        camera_matrix,
        dist_coeffs,
        P=output_camera_matrix,
    )
    return corrected.reshape(points_np.shape)


def compute_undistorted_diameters(
    coords_np, diams_np, camera_matrix, dist_coeffs, output_camera_matrix
):
    half = diams_np[..., None] / 2.0
    left = coords_np.copy()
    right = coords_np.copy()
    top = coords_np.copy()
    bottom = coords_np.copy()

    left[..., 0] -= half[..., 0]
    right[..., 0] += half[..., 0]
    top[..., 1] -= half[..., 0]
    bottom[..., 1] += half[..., 0]

    boundary_points = np.stack([left, right, top, bottom], axis=0)
    undistorted = undistort_points(
        boundary_points,
        camera_matrix,
        dist_coeffs,
        output_camera_matrix,
    )
    left_u, right_u, top_u, bottom_u = undistorted
    diam_x = np.linalg.norm(right_u - left_u, axis=-1)
    diam_y = np.linalg.norm(bottom_u - top_u, axis=-1)
    return (diam_x + diam_y) / 2.0


def compute_neural_result(coords, diams, model_path, hidden_dim):
    if not model_path or not os.path.isfile(model_path):
        return None, None

    model = load_model(model_path, hidden_dim=hidden_dim)
    norm_scale = torch.max(coords)
    with torch.no_grad():
        coords_comp = apply_compensation(model, coords, norm_scale)
        diams_comp = compute_compensated_diameters(model, coords, diams, norm_scale)

    return coords_comp.detach().cpu().numpy(), diams_comp.detach().cpu().numpy()


def undistort_image(image_path, output_path, mask_path, camera_matrix, dist_coeffs):
    image = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError(f"Unable to read image: {image_path}")

    height, width = image.shape[:2]
    map_x, map_y = cv2.initUndistortRectifyMap(
        camera_matrix,
        dist_coeffs,
        None,
        camera_matrix,
        (width, height),
        cv2.CV_32FC1,
    )
    corrected = cv2.remap(
        image,
        map_x,
        map_y,
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    valid_mask = (
        (map_x >= 0.0) & (map_x <= width - 1) & (map_y >= 0.0) & (map_y <= height - 1)
    )

    cv2.imwrite(str(output_path), corrected)
    cv2.imwrite(str(mask_path), valid_mask.astype(np.uint8) * 255)
    return float(1.0 - np.mean(valid_mask))


def metric_reduction(raw_value, corrected_value, compare_abs=False):
    if compare_abs:
        raw_value = abs(raw_value)
        corrected_value = abs(corrected_value)
    if raw_value == 0 or not np.isfinite(raw_value) or not np.isfinite(corrected_value):
        return np.nan
    return (raw_value - corrected_value) / abs(raw_value) * 100.0


def format_number(value, decimals=4):
    if value is None or not np.isfinite(value):
        return "nan"
    return f"{value:.{decimals}f}"


def format_pct(value):
    if value is None or not np.isfinite(value):
        return "nan"
    return f"{value:.2f}%"


def dist_coeff_dict(dist_coeffs):
    names = ["k1", "k2", "p1", "p2", "k3", "k4", "k5", "k6"]
    coeffs = dist_coeffs.flatten()
    return {
        names[i] if i < len(names) else f"c{i + 1}": float(value)
        for i, value in enumerate(coeffs)
    }


def write_parameters_json(path, calibration, image_size, grid_shape, invalid_fraction):
    payload = {
        "opencv_version": cv2.__version__,
        "image_size": {"width": int(image_size[0]), "height": int(image_size[1])},
        "grid_shape": {"rows": int(grid_shape[0]), "cols": int(grid_shape[1])},
        "object_spacing": calibration["object_spacing"],
        "rms_reprojection_error_px": calibration["rms"],
        "camera_matrix": calibration["camera_matrix"].tolist(),
        "distortion_coefficients": dist_coeff_dict(calibration["dist_coeffs"]),
        "rotation_vector": calibration["rvec"].flatten().tolist(),
        "translation_vector": calibration["tvec"].flatten().tolist(),
        "flags": calibration["flag_names"],
        "per_view_errors": calibration["per_view_errors"].flatten().tolist(),
        "invalid_pixel_fraction": (
            None if invalid_fraction is None else float(invalid_fraction)
        ),
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def comparison_rows(raw_metrics, opencv_metrics, neural_metrics):
    rows = []
    for key, label, unit, compare_abs in METRIC_SPECS:
        opencv_reduction = metric_reduction(
            raw_metrics[key], opencv_metrics[key], compare_abs=compare_abs
        )
        neural_value = neural_metrics[key] if neural_metrics else None
        neural_reduction = (
            metric_reduction(raw_metrics[key], neural_value, compare_abs=compare_abs)
            if neural_metrics
            else np.nan
        )
        rows.append(
            {
                "metric": key,
                "label": label,
                "unit": unit,
                "raw": raw_metrics[key],
                "opencv": opencv_metrics[key],
                "neural": neural_value,
                "opencv_reduction_pct": opencv_reduction,
                "neural_reduction_pct": neural_reduction,
            }
        )
    return rows


def write_comparison_csv(path, rows):
    fieldnames = [
        "metric",
        "label",
        "unit",
        "raw",
        "opencv",
        "neural",
        "opencv_reduction_pct",
        "neural_reduction_pct",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_report(
    path,
    rows,
    calibration,
    image_size,
    grid_shape,
    invalid_fraction,
    neural_available,
    marker_metadata=None,
):
    coeffs = dist_coeff_dict(calibration["dist_coeffs"])
    neural_header = "Neural" if neural_available else "Neural"
    invalid_text = (
        "not computed" if invalid_fraction is None else f"{invalid_fraction:.6f}"
    )
    lines = [
        "# OpenCV Calibration Comparison",
        "",
        "This report compares the raw dot-grid extraction, an OpenCV Brown-Conrady calibration baseline, and the existing neural compensation result.",
        "",
        "## Calibration Setup",
        "",
        f"- Image size: {image_size[0]} x {image_size[1]} px",
        f"- Grid shape: {grid_shape[0]} rows x {grid_shape[1]} columns",
        f"- Object spacing used for OpenCV: {calibration['object_spacing']:.4f}",
        f"- OpenCV RMS reprojection error: {calibration['rms']:.6f} px",
        f"- OpenCV flags: {', '.join(calibration['flag_names'])}",
        f"- OpenCV undistorted image invalid pixel fraction: {invalid_text}",
    ]
    if marker_metadata and marker_metadata.get("detected_marker_count"):
        row, col = marker_metadata["marker_index_1based"]
        diameter = marker_metadata["raw_marker_diameter"]
        lines.append(
            f"- Center marker excluded from diameter metrics: row {row}, col {col} "
            f"(raw diameter {diameter:.2f} px)"
        )

    lines.extend(
        [
            "",
            "## Metric Comparison",
            "",
            f"| Metric | Raw | OpenCV | {neural_header} | OpenCV change vs raw | Neural change vs raw |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )

    for row in rows:
        unit = row["unit"]
        raw_value = format_number(row["raw"])
        opencv_value = format_number(row["opencv"])
        neural_value = format_number(row["neural"]) if neural_available else "n/a"
        lines.append(
            f"| {row['label']} ({unit}) | {raw_value} | {opencv_value} | "
            f"{neural_value} | {format_pct(row['opencv_reduction_pct'])} | "
            f"{format_pct(row['neural_reduction_pct']) if neural_available else 'n/a'} |"
        )

    if not neural_available:
        lines.extend(
            [
                "",
                "Neural metrics were not computed because the neural model file was not found.",
            ]
        )

    lines.extend(
        [
            "",
            "## OpenCV Parameters",
            "",
            "Camera matrix:",
            "",
            "```text",
            np.array2string(calibration["camera_matrix"], precision=8),
            "```",
            "",
            "Distortion coefficients:",
            "",
            "```text",
            ", ".join(f"{key}={value:.8e}" for key, value in coeffs.items()),
            "```",
            "",
            "## Interpretation Notes",
            "",
            "- OpenCV is used here as a single-view parametric Brown-Conrady baseline.",
            "- With only one calibration view, OpenCV intrinsics and distortion coefficients can be under-constrained; use them as baseline diagnostics, not as final production camera parameters.",
            "- The neural result uses the repository's existing learned compensation field and can model residual target/lens deformation beyond the OpenCV polynomial fit.",
            "- Diameter StdDev is computed from same-size metal balls only; the oversized center nut marker is excluded when detected.",
            "- Lower values are better for every table metric. SMIA changes are computed from absolute distortion magnitude.",
        ]
    )

    with open(path, "w") as f:
        f.write("\n".join(lines))
        f.write("\n")


def plot_metric_comparison(path, rows, neural_available):
    selected = [
        row
        for row in rows
        if row["metric"]
        in {"reproj", "col_rmse", "spacing_x_std", "spacing_y_std", "diam_std"}
    ]
    labels = [
        "Reproj\nRMSE",
        "Straight\nRMSE",
        "Spacing X\nStdDev",
        "Spacing Y\nStdDev",
        "Metal-ball\nDiameter\nStdDev",
    ]

    raw = [row["raw"] for row in selected]
    opencv = [row["opencv"] for row in selected]
    neural = [row["neural"] for row in selected] if neural_available else None

    x = np.arange(len(selected))
    width = 0.25 if neural_available else 0.35

    plt.figure(figsize=(11, 6))
    plt.bar(x - width, raw, width, label="Raw", color="#7a7a7a")
    plt.bar(x, opencv, width, label="OpenCV", color="#2f80ed")
    if neural_available:
        plt.bar(x + width, neural, width, label="Neural", color="#8e44ad")

    plt.title("Calibration Metric Comparison")
    plt.ylabel("Pixels")
    plt.xticks(x, labels)
    plt.grid(axis="y", alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path)
    plt.close()


def run_opencv_comparison(
    coords_path="output/grid_coordinates.csv",
    diams_path="output/grid_diameters.csv",
    image_path="data/lowanu-bed-kalibrasi.tiff",
    neural_model_path="output/neural_model/compensation_model.pth",
    output_dir="output/opencv_baseline",
    image_size=(4096, 3000),
    object_spacing=30.0,
    hidden_dim=64,
    fix_aspect=False,
    write_image=True,
    center_marker_mode="auto",
    center_marker_min_ratio=1.5,
):
    os.makedirs(output_dir, exist_ok=True)

    coords, diams = load_data(coords_path, diams_path)
    coords_np = coords.detach().cpu().numpy()
    diams_np = diams.detach().cpu().numpy()
    metal_ball_mask, marker_metadata = detect_center_marker(
        diams,
        mode=center_marker_mode,
        min_ratio=center_marker_min_ratio,
    )
    resolved_image_size = image_size_from_file(image_path, image_size)

    calibration = calibrate_opencv(
        coords_np,
        resolved_image_size,
        object_spacing=object_spacing,
        fix_aspect=fix_aspect,
    )
    camera_matrix = calibration["camera_matrix"]
    dist_coeffs = calibration["dist_coeffs"]

    opencv_coords = undistort_points(
        coords_np,
        camera_matrix,
        dist_coeffs,
        camera_matrix,
    )
    opencv_diams = compute_undistorted_diameters(
        coords_np,
        diams_np,
        camera_matrix,
        dist_coeffs,
        camera_matrix,
    )

    neural_coords, neural_diams = compute_neural_result(
        coords,
        diams,
        neural_model_path,
        hidden_dim,
    )

    raw_metrics = compute_all_metrics(
        coords_np,
        diams_np,
        image_size=resolved_image_size,
        diameter_mask=metal_ball_mask,
    )
    opencv_metrics = compute_all_metrics(
        opencv_coords,
        opencv_diams,
        image_size=resolved_image_size,
        diameter_mask=metal_ball_mask,
    )
    neural_metrics = (
        compute_all_metrics(
            neural_coords,
            neural_diams,
            image_size=resolved_image_size,
            diameter_mask=metal_ball_mask,
        )
        if neural_coords is not None
        else None
    )

    save_coordinates(
        opencv_coords, os.path.join(output_dir, "undistorted_coordinates.csv")
    )
    save_coordinates(
        calibration["projected_points"],
        os.path.join(output_dir, "opencv_projected_coordinates.csv"),
    )

    invalid_fraction = None
    if write_image:
        invalid_fraction = undistort_image(
            image_path,
            os.path.join(output_dir, "undistorted_image.tiff"),
            os.path.join(output_dir, "undistorted_valid_mask.png"),
            camera_matrix,
            dist_coeffs,
        )

    rows = comparison_rows(raw_metrics, opencv_metrics, neural_metrics)
    write_comparison_csv(os.path.join(output_dir, "comparison_metrics.csv"), rows)
    write_parameters_json(
        os.path.join(output_dir, "opencv_parameters.json"),
        calibration,
        resolved_image_size,
        coords_np.shape[:2],
        invalid_fraction,
    )
    write_report(
        os.path.join(output_dir, "comparison_report.md"),
        rows,
        calibration,
        resolved_image_size,
        coords_np.shape[:2],
        invalid_fraction,
        neural_metrics is not None,
        marker_metadata,
    )
    plot_metric_comparison(
        os.path.join(output_dir, "comparison_bar_metrics.png"),
        rows,
        neural_metrics is not None,
    )

    print(f"OpenCV comparison complete. Results saved to {output_dir}")
    print(f"OpenCV RMS reprojection error: {calibration['rms']:.6f}px")
    for row in rows:
        if row["metric"] in {"reproj", "col_rmse"}:
            print(
                f"{row['label']}: raw={row['raw']:.4f}, "
                f"opencv={row['opencv']:.4f}, "
                f"neural={format_number(row['neural'])}"
            )

    return {
        "raw": raw_metrics,
        "opencv": opencv_metrics,
        "neural": neural_metrics,
        "calibration": calibration,
        "rows": rows,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run an OpenCV Brown-Conrady calibration baseline and compare it with the neural result."
    )
    parser.add_argument("--coords", default="output/grid_coordinates.csv")
    parser.add_argument("--diams", default="output/grid_diameters.csv")
    parser.add_argument("--image", default="data/lowanu-bed-kalibrasi.tiff")
    parser.add_argument(
        "--neural-model", default="output/neural_model/compensation_model.pth"
    )
    parser.add_argument("--out-dir", default="output/opencv_baseline")
    parser.add_argument("--image-width", type=int, default=4096)
    parser.add_argument("--image-height", type=int, default=3000)
    parser.add_argument("--object-spacing", type=float, default=30.0)
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--fix-aspect", action="store_true")
    parser.add_argument("--skip-image", action="store_true")
    parser.add_argument(
        "--center-marker-mode", choices=CENTER_MARKER_MODES, default="auto"
    )
    parser.add_argument("--center-marker-min-ratio", type=float, default=1.5)
    args = parser.parse_args()

    run_opencv_comparison(
        coords_path=args.coords,
        diams_path=args.diams,
        image_path=args.image,
        neural_model_path=args.neural_model,
        output_dir=args.out_dir,
        image_size=(args.image_width, args.image_height),
        object_spacing=args.object_spacing,
        hidden_dim=args.hidden_dim,
        fix_aspect=args.fix_aspect,
        write_image=not args.skip_image,
        center_marker_mode=args.center_marker_mode,
        center_marker_min_ratio=args.center_marker_min_ratio,
    )


if __name__ == "__main__":
    main()
