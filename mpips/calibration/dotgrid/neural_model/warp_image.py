# mypy: disable-error-code=no-untyped-def
# mypy: disable-error-code=no-untyped-call
# mypy: disable-error-code=var-annotated
# mypy: disable-error-code=assignment

import argparse
import json
import os

import cv2
import numpy as np
import torch

from .dataset import load_data
from .model import MLPCompensation, apply_compensation, invert_compensation_points
from ..paths import default_artifact_path

INTERPOLATION = {
    "nearest": cv2.INTER_NEAREST,
    "linear": cv2.INTER_LINEAR,
    "cubic": cv2.INTER_CUBIC,
}

BORDER_MODE = {
    "constant": cv2.BORDER_CONSTANT,
    "replicate": cv2.BORDER_REPLICATE,
    "reflect": cv2.BORDER_REFLECT,
}

CANVAS_MODE = ("fixed", "expanded")


def load_model(model_path, hidden_dim=64, device="cpu"):
    model = MLPCompensation(hidden_dim=hidden_dim).to(device)
    try:
        state_dict = torch.load(model_path, map_location=device, weights_only=True)
    except TypeError:
        state_dict = torch.load(model_path, map_location=device)
    model.load_state_dict(state_dict)
    model.eval()
    return model


def resolve_device(device):
    if device == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return device


def compute_valid_mask(map_x, map_y, width, height):
    return (map_x >= 0) & (map_x <= width - 1) & (map_y >= 0) & (map_y <= height - 1)


def ensure_parent_dir(path):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def largest_valid_rectangle(valid_mask):
    height, width = valid_mask.shape
    heights = np.zeros(width, dtype=np.int32)
    best_area = 0
    best_rect = (0, 0, width, height)

    for y in range(height):
        heights = (heights + 1) * valid_mask[y]
        stack = []
        for x in range(width + 1):
            current_height = int(heights[x]) if x < width else 0
            start = x
            while stack and stack[-1][1] > current_height:
                start, rect_height = stack.pop()
                rect_width = x - start
                area = rect_width * rect_height
                if area > best_area:
                    best_area = area
                    best_rect = (start, y - rect_height + 1, rect_width, rect_height)
            stack.append((start, current_height))

    return best_rect


def build_inverse_maps(
    model,
    output_width,
    output_height,
    norm_scale,
    step=4,
    iterations=10,
    batch_size=262144,
    device="cpu",
    dst_origin=(0.0, 0.0),
    source_width=None,
    source_height=None,
):
    if step < 1:
        raise ValueError("step must be >= 1")

    if source_width is None:
        source_width = output_width
    if source_height is None:
        source_height = output_height

    xs = np.arange(0, output_width, step, dtype=np.float32)
    ys = np.arange(0, output_height, step, dtype=np.float32)
    map_x_coarse = np.empty((len(ys), len(xs)), dtype=np.float32)
    map_y_coarse = np.empty((len(ys), len(xs)), dtype=np.float32)

    rows_per_batch = max(1, batch_size // len(xs))
    residual_sum = 0.0
    residual_count = 0
    residual_max = 0.0

    x_tensor = torch.from_numpy(xs + float(dst_origin[0])).to(device)
    norm_scale_tensor = torch.as_tensor(norm_scale, dtype=torch.float32, device=device)

    with torch.no_grad():
        for y_start in range(0, len(ys), rows_per_batch):
            y_end = min(y_start + rows_per_batch, len(ys))
            y_tensor = torch.from_numpy(ys[y_start:y_end] + float(dst_origin[1])).to(
                device
            )
            grid_y, grid_x = torch.meshgrid(y_tensor, x_tensor, indexing="ij")
            dst_points = torch.stack((grid_x.reshape(-1), grid_y.reshape(-1)), dim=1)

            src_points = invert_compensation_points(
                model,
                dst_points,
                norm_scale_tensor,
                iterations=iterations,
            )
            residual = torch.linalg.norm(
                apply_compensation(model, src_points, norm_scale_tensor) - dst_points,
                dim=1,
            )

            residual_sum += float(torch.sum(residual).cpu())
            residual_count += int(residual.numel())
            residual_max = max(residual_max, float(torch.max(residual).cpu()))

            src_np = src_points.reshape(y_end - y_start, len(xs), 2).cpu().numpy()
            map_x_coarse[y_start:y_end] = src_np[..., 0]
            map_y_coarse[y_start:y_end] = src_np[..., 1]

    if step == 1:
        map_x = map_x_coarse
        map_y = map_y_coarse
    else:
        map_x = cv2.resize(
            map_x_coarse,
            (output_width, output_height),
            interpolation=cv2.INTER_LINEAR,
        )
        map_y = cv2.resize(
            map_y_coarse,
            (output_width, output_height),
            interpolation=cv2.INTER_LINEAR,
        )

    valid = compute_valid_mask(map_x, map_y, source_width, source_height)
    stats = {
        "inverse_residual_mean_px": (
            residual_sum / residual_count if residual_count else float("nan")
        ),
        "inverse_residual_max_px": residual_max,
        "out_of_bounds_fraction": float(1.0 - np.mean(valid)),
        "step": step,
        "iterations": iterations,
        "dst_origin_xy": [float(dst_origin[0]), float(dst_origin[1])],
        "source_size": {"width": int(source_width), "height": int(source_height)},
        "output_size": {"width": int(output_width), "height": int(output_height)},
    }
    return map_x, map_y, stats


def _axis_samples(length, sample_step):
    values = np.arange(0, length, sample_step, dtype=np.float32)
    last = np.array([length - 1], dtype=np.float32)
    return np.unique(np.concatenate([values, last]))


def estimate_expanded_canvas(
    model,
    source_width,
    source_height,
    norm_scale,
    coords=None,
    sample_step=8,
    margin=8,
    batch_size=262144,
    device="cpu",
):
    if sample_step < 1:
        raise ValueError("expanded bounds sample step must be >= 1")
    if margin < 0:
        raise ValueError("expanded margin must be >= 0")

    xs = _axis_samples(source_width, sample_step)
    ys = _axis_samples(source_height, sample_step)
    grid_x, grid_y = np.meshgrid(xs, ys)
    samples = [np.stack((grid_x.reshape(-1), grid_y.reshape(-1)), axis=1)]
    if coords is not None:
        if hasattr(coords, "detach"):
            coords_np = coords.detach().cpu().numpy()
        else:
            coords_np = np.asarray(coords)
        samples.append(coords_np.reshape(-1, 2).astype(np.float32))

    points_np = np.concatenate(samples, axis=0).astype(np.float32)
    norm_scale_tensor = torch.as_tensor(norm_scale, dtype=torch.float32, device=device)

    mins = np.array([np.inf, np.inf], dtype=np.float64)
    maxs = np.array([-np.inf, -np.inf], dtype=np.float64)
    with torch.no_grad():
        for start in range(0, len(points_np), batch_size):
            batch = torch.from_numpy(points_np[start : start + batch_size]).to(device)
            corrected = apply_compensation(model, batch, norm_scale_tensor)
            corrected_np = corrected.detach().cpu().numpy()
            mins = np.minimum(mins, corrected_np.min(axis=0))
            maxs = np.maximum(maxs, corrected_np.max(axis=0))

    origin = np.floor(mins - margin).astype(int)
    max_pixel = np.ceil(maxs + margin).astype(int)
    size = (max_pixel - origin + 1).astype(int)

    return {
        "origin_xy": [int(origin[0]), int(origin[1])],
        "output_size": {"width": int(size[0]), "height": int(size[1])},
        "estimated_corrected_bounds_xyxy": [
            float(mins[0]),
            float(mins[1]),
            float(maxs[0]),
            float(maxs[1]),
        ],
        "sample_step": int(sample_step),
        "margin_px": int(margin),
        "sample_count": int(len(points_np)),
    }


def warp_image(
    image_path,
    model_path,
    coords_path,
    diams_path,
    output_path,
    step=4,
    iterations=10,
    interpolation="linear",
    border_mode="constant",
    border_value=0,
    batch_size=262144,
    hidden_dim=64,
    device="auto",
    mask_path=None,
    crop_valid=False,
    crop_output_path=None,
    canvas_mode="fixed",
    expanded_bounds_step=4,
    expanded_margin=16,
    metadata_path=None,
):
    if canvas_mode not in CANVAS_MODE:
        raise ValueError(f"Unsupported canvas mode: {canvas_mode}")

    device = resolve_device(device)
    print(f"Using device: {device}")

    print("Loading image...")
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"Could not load image at {image_path}")

    height, width = img.shape[:2]
    print(f"Image loaded. Size: {width}x{height}")

    print("Loading model...")
    coords, _ = load_data(coords_path, diams_path)
    norm_scale = float(torch.max(coords).item())
    model = load_model(model_path, hidden_dim=hidden_dim, device=device)

    output_width = width
    output_height = height
    dst_origin = (0, 0)
    expanded_canvas = None
    if canvas_mode == "expanded":
        print("Estimating expanded output canvas...")
        expanded_canvas = estimate_expanded_canvas(
            model,
            width,
            height,
            norm_scale,
            coords=coords,
            sample_step=expanded_bounds_step,
            margin=expanded_margin,
            batch_size=batch_size,
            device=device,
        )
        dst_origin = tuple(expanded_canvas["origin_xy"])
        output_width = expanded_canvas["output_size"]["width"]
        output_height = expanded_canvas["output_size"]["height"]
        print(
            "Expanded canvas: "
            f"origin=({dst_origin[0]}, {dst_origin[1]}), "
            f"size={output_width}x{output_height}"
        )

    print("Generating inverse remap field...")
    map_x, map_y, stats = build_inverse_maps(
        model,
        output_width,
        output_height,
        norm_scale,
        step=step,
        iterations=iterations,
        batch_size=batch_size,
        device=device,
        dst_origin=dst_origin,
        source_width=width,
        source_height=height,
    )
    stats["canvas_mode"] = canvas_mode
    if expanded_canvas:
        stats["expanded_canvas"] = expanded_canvas
    print(
        "Inverse residual: "
        f"mean={stats['inverse_residual_mean_px']:.4f}px, "
        f"max={stats['inverse_residual_max_px']:.4f}px, "
        f"out_of_bounds={stats['out_of_bounds_fraction'] * 100:.2f}%"
    )

    print("Applying cv2.remap...")
    calibrated_img = cv2.remap(
        img,
        map_x,
        map_y,
        INTERPOLATION[interpolation],
        borderMode=BORDER_MODE[border_mode],
        borderValue=border_value,
    )

    valid_mask = compute_valid_mask(map_x, map_y, width, height)
    if mask_path:
        print("Saving valid mask...")
        ensure_parent_dir(mask_path)
        cv2.imwrite(mask_path, valid_mask.astype(np.uint8) * 255)

    print("Saving calibrated image...")
    ensure_parent_dir(output_path)
    cv2.imwrite(output_path, calibrated_img)

    if crop_valid:
        if not crop_output_path:
            root, ext = os.path.splitext(output_path)
            crop_output_path = f"{root}_cropped{ext}"
        x, y, crop_width, crop_height = largest_valid_rectangle(valid_mask)
        cropped_img = calibrated_img[y : y + crop_height, x : x + crop_width]
        print(
            "Saving valid crop: "
            f"x={x}, y={y}, width={crop_width}, height={crop_height}"
        )
        ensure_parent_dir(crop_output_path)
        cv2.imwrite(crop_output_path, cropped_img)
        stats["valid_crop"] = {
            "x": int(x),
            "y": int(y),
            "width": int(crop_width),
            "height": int(crop_height),
        }

    if metadata_path is None and canvas_mode == "expanded":
        root, _ = os.path.splitext(output_path)
        metadata_path = f"{root}_metadata.json"

    if metadata_path:
        stats["metadata_path"] = metadata_path
        print(f"Saving warp metadata to {metadata_path}...")
        ensure_parent_dir(metadata_path)
        with open(metadata_path, "w") as f:
            json.dump(stats, f, indent=2)
            f.write("\n")

    print(f"Success! Calibrated image saved to {output_path}")
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Warp a calibration image with the neural compensation model."
    )
    parser.add_argument(
        "--image", default=default_artifact_path("data/lowanu-bed-kalibrasi.tiff")
    )
    parser.add_argument(
        "--model",
        default=default_artifact_path("output/neural_model/compensation_model.pth"),
    )
    parser.add_argument(
        "--coords", default=default_artifact_path("output/grid_coordinates.csv")
    )
    parser.add_argument(
        "--diams", default=default_artifact_path("output/grid_diameters.csv")
    )
    parser.add_argument(
        "--out",
        default=default_artifact_path("output/neural_model/calibrated_image.tiff"),
    )
    parser.add_argument(
        "--step",
        type=int,
        default=4,
        help="Inverse map sampling step. Use 1 for dense mapping.",
    )
    parser.add_argument(
        "--iterations", type=int, default=10, help="Fixed-point inverse iterations."
    )
    parser.add_argument("--batch-size", type=int, default=262144)
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    parser.add_argument(
        "--interpolation", default="linear", choices=sorted(INTERPOLATION)
    )
    parser.add_argument(
        "--border-mode", default="constant", choices=sorted(BORDER_MODE)
    )
    parser.add_argument("--border-value", type=float, default=0)
    parser.add_argument(
        "--mask-out",
        default=default_artifact_path("output/neural_model/calibrated_valid_mask.png"),
    )
    parser.add_argument("--canvas-mode", choices=CANVAS_MODE, default="fixed")
    parser.add_argument(
        "--expanded-bounds-step",
        type=int,
        default=4,
        help="Source-grid sampling step for expanded canvas bounds.",
    )
    parser.add_argument(
        "--expanded-margin",
        type=int,
        default=16,
        help="Extra output pixels added around expanded canvas bounds.",
    )
    parser.add_argument(
        "--metadata-out",
        default=None,
        help=(
            "Write warp metadata JSON. Defaults to *_metadata.json for expanded canvas."
        ),
    )
    parser.add_argument(
        "--crop-valid",
        action="store_true",
        help="Also write the largest all-valid crop without black border.",
    )
    parser.add_argument(
        "--crop-out",
        default=default_artifact_path(
            "output/neural_model/calibrated_image_cropped.tiff"
        ),
    )
    args = parser.parse_args()

    warp_image(
        args.image,
        args.model,
        args.coords,
        args.diams,
        args.out,
        step=args.step,
        iterations=args.iterations,
        interpolation=args.interpolation,
        border_mode=args.border_mode,
        border_value=args.border_value,
        batch_size=args.batch_size,
        hidden_dim=args.hidden_dim,
        device=args.device,
        mask_path=args.mask_out,
        crop_valid=args.crop_valid,
        crop_output_path=args.crop_out,
        canvas_mode=args.canvas_mode,
        expanded_bounds_step=args.expanded_bounds_step,
        expanded_margin=args.expanded_margin,
        metadata_path=args.metadata_out,
    )
