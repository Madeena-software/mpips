import argparse
import csv
import math
import os

import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D


def parse_coord(s):
    s = s.strip("()")
    x_str, y_str = s.split(",")
    return (float(x_str), float(y_str))


def main(csv_file, out1):
    # Load the 2D matrix
    grid = []
    with open(csv_file, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            grid.append([parse_coord(cell) for cell in row])

    num_rows = len(grid)
    num_cols = len(grid[0])

    # ---------------------------------------------------------
    # Plot 3D Surface: Horizontal Euclidean Distance
    # Z = Distance from (r, c) to (r, c+1)
    # ---------------------------------------------------------
    X = np.arange(1, num_cols)  # 1 to 25
    Y = np.arange(1, num_rows + 1)  # 1 to 19
    X, Y = np.meshgrid(X, Y)

    Z = np.zeros((num_rows, num_cols - 1))

    for r in range(num_rows):
        for c in range(num_cols - 1):
            x1, y1 = grid[r][c]
            x2, y2 = grid[r][c + 1]
            dist = math.hypot(x2 - x1, y2 - y1)
            Z[r, c] = dist

    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection="3d")
    surf = ax.plot_surface(X, Y, Z, cmap="viridis", edgecolor="k", alpha=0.8)

    ax.set_title("3D Surface: Horizontal Euclidean Distance between Dots")
    ax.set_xlabel("Column Gap Index (X)")
    ax.set_ylabel("Row Index (Y)")
    ax.set_zlabel("Euclidean Distance (pixels)")
    fig.colorbar(surf, shrink=0.5, aspect=5)

    plt.savefig(out1, dpi=150)
    plt.close()

    # ---------------------------------------------------------
    # Plot 3D Surface: Total Deformation from Center (Bowl)
    # Z = Distance of dot from mathematical perfect center
    # ---------------------------------------------------------
    # (Optional extra plot just in case they meant total deviation)

    print(f"Saved {out1}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Plot 3D horizontal euclidean distance."
    )
    parser.add_argument(
        "--csv", required=True, help="Path to input grid_coordinates.csv"
    )
    parser.add_argument("--output", required=True, help="Path to output plot PNG")
    args = parser.parse_args()

    main(args.csv, args.output)
