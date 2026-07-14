import argparse
import csv
import os

import cv2
import numpy as np


def extract_dots(image_path, output_csv):
    print(f"Processing image: {image_path}")

    # Read the image in grayscale
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"Error: Could not load image at {image_path}")
        return

    # Apply a binary threshold to isolate the bright dots
    # You may need to tweak the threshold value (currently 128) based on lighting
    _, thresh = cv2.threshold(img, 128, 255, cv2.THRESH_BINARY)

    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    print(f"Found {len(contours)} raw contours. Filtering noise...")

    results = []

    for cnt in contours:
        # Calculate the area to filter out tiny noise specs
        area = cv2.contourArea(cnt)

        # We expect the dots to have a reasonable area, e.g., > 10 pixels
        if area > 10:
            # Find the minimum enclosing circle
            (x, y), radius = cv2.minEnclosingCircle(cnt)
            diameter = radius * 2

            # Store the data (rounding for cleanliness)
            results.append(
                {"x": round(x, 2), "y": round(y, 2), "diameter": round(diameter, 2)}
            )

    print(f"Successfully extracted {len(results)} valid dots.")

    # Sort results primarily by Y (top to bottom), then X (left to right) for readability
    # We round Y roughly to group them by row
    results.sort(key=lambda item: (round(item["y"] / 50), item["x"]))

    # Write to CSV
    with open(output_csv, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["x", "y", "diameter"])
        writer.writeheader()
        writer.writerows(results)

    print(f"Data successfully saved to: {output_csv}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract dots from image.")
    parser.add_argument("--input", required=True, help="Path to input image")
    parser.add_argument("--output", required=True, help="Path to output CSV")
    args = parser.parse_args()

    extract_dots(args.input, args.output)
