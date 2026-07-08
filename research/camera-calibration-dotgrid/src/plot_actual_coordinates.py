import argparse
import csv
import os

import matplotlib.pyplot as plt


def parse_coord(s):
    s = s.strip("()")
    x_str, y_str = s.split(",")
    return (float(x_str), float(y_str))


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

    # ---------------------------------------------------------
    # Plot 1: Actual Y-Coordinates (Showing Row Bowing)
    # ---------------------------------------------------------
    plt.figure(figsize=(10, 8))
    for r in range(num_rows):
        y_coords = [grid[r][c][1] for c in range(num_cols)]
        x_vals = range(1, num_cols + 1)
        plt.plot(x_vals, y_coords, marker="o", markersize=4, label=f"Row {r+1}")

    plt.title("Actual Y-Coordinates of Each Row (Notice the Bowing)")
    plt.xlabel("Column Number (1 to 26)")
    plt.ylabel("Y Pixel Coordinate (0 is Top of Image)")
    plt.xticks(range(1, num_cols + 1))
    # Invert Y axis so it visually matches the image (Y=0 at top)
    plt.gca().invert_yaxis()
    plt.grid(True)

    plt.savefig(out1)
    plt.close()

    # ---------------------------------------------------------
    # Plot 2: Actual X-Coordinates (Showing Column Bowing)
    # ---------------------------------------------------------
    plt.figure(figsize=(10, 8))
    for c in range(num_cols):
        x_coords = [grid[r][c][0] for r in range(num_rows)]
        x_vals = range(1, num_rows + 1)
        plt.plot(x_vals, x_coords, marker="o", markersize=4)

    plt.title("Actual X-Coordinates of Each Column (Notice the Bowing)")
    plt.xlabel("Row Number (1 to 19)")
    plt.ylabel("X Pixel Coordinate (0 is Left of Image)")
    plt.xticks(range(1, num_rows + 1))
    plt.grid(True)

    plt.savefig(out2)
    plt.close()

    print(f"Saved {out1}")
    print(f"Saved {out2}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot actual coordinates.")
    parser.add_argument(
        "--csv", required=True, help="Path to input grid_coordinates.csv"
    )
    parser.add_argument(
        "--out1", required=True, help="Path to actual Y coordinates plot"
    )
    parser.add_argument(
        "--out2", required=True, help="Path to actual X coordinates plot"
    )
    args = parser.parse_args()

    main(args.csv, args.out1, args.out2)
