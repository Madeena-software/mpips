import argparse
import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

NEURAL_MODEL_DIR = Path(__file__).resolve().parent / "neural_model"
if str(NEURAL_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(NEURAL_MODEL_DIR))

from phantom import CENTER_MARKER_MODES, detect_center_marker


def main(csv_file, out1, out2, center_marker_mode="auto", center_marker_min_ratio=1.5):

    # Load the 2D matrix
    grid_diams = []
    with open(csv_file, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            grid_diams.append([float(cell) for cell in row])

    num_rows = len(grid_diams)
    num_cols = len(grid_diams[0])
    print(f"Loaded diameter grid: {num_rows} rows x {num_cols} columns")
    diam_array = np.asarray(grid_diams, dtype=np.float64)
    metal_ball_mask, marker_metadata = detect_center_marker(
        diam_array,
        mode=center_marker_mode,
        min_ratio=center_marker_min_ratio,
    )
    if marker_metadata["detected_marker_count"]:
        row, col = marker_metadata["marker_index_1based"]
        print(
            "Center marker highlighted and excluded from metal-ball plots: "
            f"row {row}, col {col}"
        )

    # ---------------------------------------------------------
    # Plot 1: Horizontal Diameter (Rows)
    # ---------------------------------------------------------
    plt.figure(figsize=(10, 6))
    for r in range(num_rows):
        col_indices = np.where(metal_ball_mask[r])[0]
        plt.scatter(
            col_indices + 1,
            diam_array[r, col_indices],
            alpha=0.5,
            color="green",
            s=20,
        )
    if marker_metadata["detected_marker_count"]:
        marker_row, marker_col = marker_metadata["marker_index_0based"]
        plt.scatter(
            [marker_col + 1],
            [diam_array[marker_row, marker_col]],
            color="red",
            s=55,
            label="Center marker",
            zorder=3,
        )
        plt.legend()

    plt.title("Horizontal Metal-ball Diameter Profile (Center Marker Highlighted)")
    plt.xlabel("Column Number")
    plt.ylabel("Dot Diameter (pixels)")
    plt.xticks(range(1, num_cols + 1))
    plt.grid(True)

    plt.savefig(out1)
    plt.close()

    # ---------------------------------------------------------
    # Plot 2: Vertical Diameter (Columns)
    # ---------------------------------------------------------
    plt.figure(figsize=(10, 6))
    for c in range(num_cols):
        row_indices = np.where(metal_ball_mask[:, c])[0]
        plt.scatter(
            row_indices + 1,
            diam_array[row_indices, c],
            alpha=0.5,
            color="purple",
            s=20,
        )
    if marker_metadata["detected_marker_count"]:
        marker_row, marker_col = marker_metadata["marker_index_0based"]
        plt.scatter(
            [marker_row + 1],
            [diam_array[marker_row, marker_col]],
            color="red",
            s=55,
            label="Center marker",
            zorder=3,
        )
        plt.legend()

    plt.title("Vertical Metal-ball Diameter Profile (Center Marker Highlighted)")
    plt.xlabel("Row Number")
    plt.ylabel("Dot Diameter (pixels)")
    plt.xticks(range(1, num_rows + 1))
    plt.grid(True)

    plt.savefig(out2)
    plt.close()

    print(f"Saved {out1}")
    print(f"Saved {out2}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot diameter profile.")
    parser.add_argument("--csv", required=True, help="Path to input grid_diameters.csv")
    parser.add_argument("--out1", required=True, help="Path to horizontal plot PNG")
    parser.add_argument("--out2", required=True, help="Path to vertical plot PNG")
    parser.add_argument(
        "--center-marker-mode", choices=CENTER_MARKER_MODES, default="auto"
    )
    parser.add_argument("--center-marker-min-ratio", type=float, default=1.5)
    args = parser.parse_args()

    main(
        args.csv,
        args.out1,
        args.out2,
        center_marker_mode=args.center_marker_mode,
        center_marker_min_ratio=args.center_marker_min_ratio,
    )
