import argparse
import csv
import math
import os

import cv2
import numpy as np


def extract_grid(image_path, output_dir):
    print(f"Processing image: {image_path}")

    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"Error: Could not load image at {image_path}")
        return

    # Thresholding
    _, thresh = cv2.threshold(img, 128, 255, cv2.THRESH_BINARY)

    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    dots = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 10:
            (x, y), radius = cv2.minEnclosingCircle(cnt)
            diameter = radius * 2

            # Calculate Circularity: 4 * pi * Area / (Perimeter^2)
            perimeter = cv2.arcLength(cnt, True)
            if perimeter > 0:
                circularity = (4 * math.pi * area) / (perimeter * perimeter)
            else:
                circularity = 0

            dots.append(
                {"x": x, "y": y, "diameter": diameter, "circularity": circularity}
            )

    print(f"Extracted {len(dots)} valid dots.")

    # Group dots into rows based on Y coordinate
    # Sort primarily by Y
    dots.sort(key=lambda d: d["y"])

    rows = []
    current_row = []
    current_y_avg = None

    for dot in dots:
        if current_y_avg is None:
            current_row.append(dot)
            current_y_avg = dot["y"]
        else:
            # If the Y difference is less than 50 pixels, it's the same row
            if abs(dot["y"] - current_y_avg) < 50:
                current_row.append(dot)
                current_y_avg = sum(d["y"] for d in current_row) / len(current_row)
            else:
                # Sort the completed row by X coordinate
                current_row.sort(key=lambda d: d["x"])
                rows.append(current_row)

                # Start new row
                current_row = [dot]
                current_y_avg = dot["y"]

    if current_row:
        current_row.sort(key=lambda d: d["x"])
        rows.append(current_row)

    print(f"Grouped into {len(rows)} rows.")
    for i, r in enumerate(rows):
        print(f"Row {i+1}: {len(r)} columns")

    # Prepare data for the 3 CSVs
    grid_coords = []
    grid_diams = []
    grid_circs = []

    for r in rows:
        row_coords = [f"({round(d['x'], 1)}, {round(d['y'], 1)})" for d in r]
        row_diams = [f"{round(d['diameter'], 2)}" for d in r]
        row_circs = [f"{round(d['circularity'], 4)}" for d in r]

        grid_coords.append(row_coords)
        grid_diams.append(row_diams)
        grid_circs.append(row_circs)

    # Write CSVs
    coord_file = os.path.join(output_dir, "grid_coordinates.csv")
    with open(coord_file, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(grid_coords)

    diam_file = os.path.join(output_dir, "grid_diameters.csv")
    with open(diam_file, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(grid_diams)

    circ_file = os.path.join(output_dir, "grid_circularity.csv")
    with open(circ_file, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(grid_circs)

    print(f"Saved {coord_file}")
    print(f"Saved {diam_file}")
    print(f"Saved {circ_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract grid from image.")
    parser.add_argument("--input", required=True, help="Path to input image")
    parser.add_argument(
        "--output_dir", required=True, help="Directory to save output CSVs"
    )
    args = parser.parse_args()

    extract_grid(args.input, args.output_dir)
