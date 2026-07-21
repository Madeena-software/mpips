import argparse
import csv
import math
import os

import matplotlib.pyplot as plt


def parse_coord(s):
    # Parses the string format "(x, y)" back into a tuple of floats
    s = s.strip("()")
    x_str, y_str = s.split(",")
    return (float(x_str), float(y_str))


def calculate_horizontal_distance(p1, p2):
    # Just the absolute difference in X pixels
    return abs(p2[0] - p1[0])


def calculate_vertical_distance(p1, p2):
    # Just the absolute difference in Y pixels
    return abs(p2[1] - p1[1])


def main(csv_file, out1, out2):

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
    print(f"Loaded grid: {num_rows} rows x {num_cols} columns")

    # ---------------------------------------------------------
    # Plot 1: Horizontal Distances (Rows) using X difference
    # ---------------------------------------------------------
    plt.figure(figsize=(10, 6))
    for r in range(num_rows):
        distances = []
        for c in range(num_cols - 1):
            d = calculate_horizontal_distance(grid[r][c], grid[r][c + 1])
            distances.append(d)

        # X-axis is the column gap index (1 to 25)
        x_vals = range(1, num_cols)
        plt.scatter(x_vals, distances, alpha=0.5, color="blue", s=20)

        if r == num_rows // 2:
            for x, y in zip(x_vals, distances):
                plt.text(
                    x,
                    y + 0.5,
                    f"{x}-{x+1}",
                    fontsize=7,
                    ha="center",
                    va="bottom",
                    color="black",
                )

    plt.title("Horizontal Distortion (Overlay of All 19 Rows) - X Pixel Distance")
    plt.xlabel("Gap between Column N and N+1")
    plt.ylabel("Absolute X Pixel Difference |X2 - X1|")

    x_ticks = range(1, num_cols)
    plt.xticks(x_ticks, [f"{i}-{i+1}" for i in x_ticks], rotation=45, fontsize=8)

    plt.grid(True)
    plt.tight_layout()

    plt.savefig(out1)
    plt.close()

    # ---------------------------------------------------------
    # Plot 2: Vertical Distances (Columns) using Y difference
    # ---------------------------------------------------------
    plt.figure(figsize=(10, 6))
    for c in range(num_cols):
        distances = []
        for r in range(num_rows - 1):
            d = calculate_vertical_distance(grid[r][c], grid[r + 1][c])
            distances.append(d)

        # X-axis is the row gap index (1 to 18)
        x_vals = range(1, num_rows)
        plt.scatter(x_vals, distances, alpha=0.5, color="red", s=20)

        if c == num_cols // 2:
            for x, y in zip(x_vals, distances):
                plt.text(
                    x,
                    y + 0.5,
                    f"{x}-{x+1}",
                    fontsize=7,
                    ha="center",
                    va="bottom",
                    color="black",
                )

    plt.title("Vertical Distortion (Overlay of All 26 Columns) - Y Pixel Distance")
    plt.xlabel("Gap between Row N and N+1")
    plt.ylabel("Absolute Y Pixel Difference |Y2 - Y1|")

    x_ticks = range(1, num_rows)
    plt.xticks(x_ticks, [f"{i}-{i+1}" for i in x_ticks], rotation=45, fontsize=8)

    plt.grid(True)
    plt.tight_layout()

    plt.savefig(out2)
    plt.close()

    print(f"Saved {out1}")
    print(f"Saved {out2}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot distortion profile.")
    parser.add_argument(
        "--csv", required=True, help="Path to input grid_coordinates.csv"
    )
    parser.add_argument("--out1", required=True, help="Path to horizontal plot PNG")
    parser.add_argument("--out2", required=True, help="Path to vertical plot PNG")
    args = parser.parse_args()

    main(args.csv, args.out1, args.out2)
