import argparse
import csv
import os

import cv2


def overlay_dots(image_path, csv_path, output_path):
    print(f"Loading image: {image_path}")
    # Read the image in color so we can draw colored circles
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not load image at {image_path}")
        return

    print(f"Loading coordinates from: {csv_path}")
    count = 0
    with open(csv_path, mode="r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            x = int(float(row["x"]))
            y = int(float(row["y"]))
            radius = int(float(row["diameter"]) / 2)

            # Draw a green circle around the dot (thickness=3)
            cv2.circle(img, (x, y), radius + 5, (0, 255, 0), 3)
            # Draw a small red dot precisely at the center
            cv2.circle(img, (x, y), 2, (0, 0, 255), -1)
            count += 1

    print(f"Overlayed {count} dots onto the image.")

    cv2.imwrite(output_path, img)
    print(f"Saved annotated image to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Overlay dots on image.")
    parser.add_argument("--image", required=True, help="Path to input image")
    parser.add_argument("--csv", required=True, help="Path to input CSV")
    parser.add_argument("--output", required=True, help="Path to output image")
    args = parser.parse_args()

    overlay_dots(args.image, args.csv, args.output)
