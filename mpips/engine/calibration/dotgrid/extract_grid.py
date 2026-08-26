import argparse
import csv
import math
import os

import cv2
import numpy as np

_BORDER_DISTANCE = 20
_BORDER_ARTIFACT_AREA = 100


def extract_grid(
    image_path,
    output_dir,
    threshold=128,
    minimum_contour_area=10,
    row_tolerance=50,
):
    print(f"Processing image: {image_path}")

    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"Error: Could not load image at {image_path}")
        return

    # Thresholding
    _, thresh = cv2.threshold(img, threshold, 255, cv2.THRESH_BINARY)

    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    dots = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > minimum_contour_area:
            (x, y), radius = cv2.minEnclosingCircle(cnt)
            diameter = radius * 2

            # Calculate Circularity: 4 * pi * Area / (Perimeter^2)
            perimeter = cv2.arcLength(cnt, True)
            if perimeter > 0:
                circularity = (4 * math.pi * area) / (perimeter * perimeter)
            else:
                circularity = 0

            dots.append(
                {
                    "x": x,
                    "y": y,
                    "area": area,
                    "diameter": diameter,
                    "circularity": circularity,
                    "bbox": cv2.boundingRect(cnt),
                    "border_distance": min(
                        x, y, img.shape[1] - 1 - x, img.shape[0] - 1 - y
                    ),
                }
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
            if abs(dot["y"] - current_y_avg) < row_tolerance:
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

    # Tiny components at the detector edge are clipped border fragments, not
    # recoverable phantom dots.  The area bound is below legitimate clipped
    # dots in the source image and is paired with border proximity.
    row_data = [
        (row, any(dot["border_distance"] < _BORDER_DISTANCE for dot in row))
        for row in rows
    ]
    excluded_border_components = [
        dot
        for row, _ in row_data
        for dot in row
        if dot["border_distance"] < _BORDER_DISTANCE
        and dot["area"] < _BORDER_ARTIFACT_AREA
    ]
    if excluded_border_components:
        excluded_ids = {id(dot) for dot in excluded_border_components}
        row_data = [
            ([dot for dot in row if id(dot) not in excluded_ids], touched_border)
            for row, touched_border in row_data
        ]
        row_data = [(row, touched) for row, touched in row_data if row]
        print(
            "Excluded "
            f"{len(excluded_border_components)} tiny detector-border components."
        )

    from collections import Counter

    widths = [len(row) for row, _ in row_data]
    if len(row_data) < 2 or not widths:
        raise ValueError(
            "Detected dot grid has insufficient rows after border filtering"
        )
    expected_width = Counter(widths).most_common(1)[0][0]
    partial_rows = [
        row
        for row, touched_border in row_data
        if len(row) != expected_width
        and (
            touched_border
            or min(dot["y"] for dot in row) < row_tolerance
            or max(dot["y"] for dot in row) >= img.shape[0] - row_tolerance
        )
    ]
    if partial_rows:
        partial_ids = {id(row) for row in partial_rows}
        row_data = [
            (row, touched) for row, touched in row_data if id(row) not in partial_ids
        ]
        print(f"Excluded {len(partial_rows)} partial edge rows.")

    rows = [row for row, _ in row_data]
    row_widths = {len(row) for row in rows}
    if len(rows) < 2 or len(row_widths) != 1 or next(iter(row_widths)) < 2:
        widths = ", ".join(str(len(row)) for row in rows)
        raise ValueError(
            "Detected dot grid has inconsistent row widths; refusing to discard "
            "rows; "
            f"row widths: {widths}"
        )

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

    coordinates = np.asarray(
        [[(dot["x"], dot["y"]) for dot in row] for row in rows],
        dtype=np.float32,
    )
    diameters = np.asarray(
        [[dot["diameter"] for dot in row] for row in rows], dtype=np.float32
    )
    circularities = np.asarray(
        [[dot["circularity"] for dot in row] for row in rows], dtype=np.float32
    )
    return coordinates, diameters, circularities


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract grid from image.")
    parser.add_argument("--input", required=True, help="Path to input image")
    parser.add_argument(
        "--output_dir", required=True, help="Directory to save output CSVs"
    )
    args = parser.parse_args()

    extract_grid(args.input, args.output_dir)
