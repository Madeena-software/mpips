import csv
import torch
import numpy as np


def parse_coord(s):
    s = s.strip("()")
    x_str, y_str = s.split(",")
    return [float(x_str), float(y_str)]


def format_coord(x, y):
    return f"({x:.2f}, {y:.2f})"


def load_data(coords_path, diams_path):
    coords = []
    with open(coords_path, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            coords.append([parse_coord(cell) for cell in row])

    diams = []
    with open(diams_path, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            diams.append([float(cell) for cell in row])

    # Convert to tensors
    coords_tensor = torch.tensor(coords, dtype=torch.float32)  # Shape: (rows, cols, 2)
    diams_tensor = torch.tensor(diams, dtype=torch.float32)  # Shape: (rows, cols)

    if coords_tensor.ndim != 3 or coords_tensor.shape[-1] != 2:
        raise ValueError(
            f"Expected coordinates with shape (rows, cols, 2), got {tuple(coords_tensor.shape)}"
        )
    if diams_tensor.ndim != 2:
        raise ValueError(
            f"Expected diameters with shape (rows, cols), got {tuple(diams_tensor.shape)}"
        )
    if coords_tensor.shape[:2] != diams_tensor.shape:
        raise ValueError(
            "Coordinate and diameter grids must have the same row/column shape: "
            f"{tuple(coords_tensor.shape[:2])} != {tuple(diams_tensor.shape)}"
        )

    return coords_tensor, diams_tensor


def save_coordinates(coords, output_path):
    if isinstance(coords, torch.Tensor):
        coords_np = coords.detach().cpu().numpy()
    else:
        coords_np = np.asarray(coords)

    if coords_np.ndim != 3 or coords_np.shape[-1] != 2:
        raise ValueError(
            f"Expected coordinates with shape (rows, cols, 2), got {coords_np.shape}"
        )

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        for row in coords_np:
            writer.writerow([format_coord(x, y) for x, y in row])
