import argparse
import csv
import os

import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D


def parse_coord(s):
    s = s.strip("()")
    x_str, y_str = s.split(",")
    return (float(x_str), float(y_str))


def main(csv_file, out):

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

    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection="3d")

    # Plot the mesh
    # To make it a wireframe, we plot lines for each row and each column

    # Plot rows
    for r in range(num_rows):
        x_vals = [grid[r][c][0] for c in range(num_cols)]
        y_vals = [grid[r][c][1] for c in range(num_cols)]
        z_vals = [0] * num_cols
        ax.plot(x_vals, y_vals, z_vals, color="blue", alpha=0.6, linewidth=1)
        ax.scatter(x_vals, y_vals, z_vals, color="black", s=5)

    # Plot columns
    for c in range(num_cols):
        x_vals = [grid[r][c][0] for r in range(num_rows)]
        y_vals = [grid[r][c][1] for r in range(num_rows)]
        z_vals = [0] * num_rows
        ax.plot(x_vals, y_vals, z_vals, color="blue", alpha=0.6, linewidth=1)

    ax.set_title("3D Floating Mesh of Actual Pixel Coordinates")
    ax.set_xlabel("X Pixel Coordinate")
    ax.set_ylabel("Y Pixel Coordinate")
    ax.set_zlabel("Z (Flat Plane = 0)")

    # Invert Y axis to match image coordinates (Y=0 is top)
    ax.invert_yaxis()

    # Fix the Z axis limits so it looks like a flat plane
    ax.set_zlim(-1, 1)

    # Adjust viewing angle for a nice 3D perspective
    ax.view_init(elev=45, azim=-45)

    plt.savefig(out, dpi=150)
    plt.close()

    print(f"Saved {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot 3D flat mesh.")
    parser.add_argument(
        "--csv", required=True, help="Path to input grid_coordinates.csv"
    )
    parser.add_argument("--output", required=True, help="Path to output plot PNG")
    args = parser.parse_args()

    main(args.csv, args.output)
