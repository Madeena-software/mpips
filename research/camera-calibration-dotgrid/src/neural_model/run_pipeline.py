import argparse
import os
import sys

from evaluate import evaluate_model
from phantom import CENTER_MARKER_MODES
from train import train_model
from validate_outputs import validate_outputs
from warp_image import CANVAS_MODE, warp_image

OPENCV_BASELINE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "opencv_baseline"
)
if OPENCV_BASELINE_DIR not in sys.path:
    sys.path.insert(0, OPENCV_BASELINE_DIR)

from calibrate_and_compare import run_opencv_comparison


def main(args):
    model_path = args.model

    if not args.skip_train:
        train_model(
            args.coords,
            args.diams,
            args.out_dir,
            epochs=args.epochs,
            lr=args.lr,
            target_loss=args.target_loss,
            hidden_dim=args.hidden_dim,
            seed=args.seed,
            smoothness_weight=args.smoothness_weight,
            edge_balance_weight=args.edge_balance_weight,
            center_marker_mode=args.center_marker_mode,
            center_marker_min_ratio=args.center_marker_min_ratio,
        )
        model_path = os.path.join(args.out_dir, "compensation_model.pth")

    if not args.skip_evaluate:
        evaluate_model(
            model_path,
            args.coords,
            args.diams,
            args.out_dir,
            image_size=(args.image_width, args.image_height),
            hidden_dim=args.hidden_dim,
            center_marker_mode=args.center_marker_mode,
            center_marker_min_ratio=args.center_marker_min_ratio,
        )

    if not args.skip_opencv_comparison:
        run_opencv_comparison(
            coords_path=args.coords,
            diams_path=args.diams,
            image_path=args.image,
            neural_model_path=model_path,
            output_dir=args.opencv_out_dir,
            image_size=(args.image_width, args.image_height),
            object_spacing=args.object_spacing,
            hidden_dim=args.hidden_dim,
            fix_aspect=args.opencv_fix_aspect,
            write_image=not args.opencv_skip_image,
            center_marker_mode=args.center_marker_mode,
            center_marker_min_ratio=args.center_marker_min_ratio,
        )

    if not args.skip_warp:
        warp_image(
            args.image,
            model_path,
            args.coords,
            args.diams,
            args.calibrated,
            step=args.step,
            iterations=args.iterations,
            interpolation=args.interpolation,
            border_mode=args.border_mode,
            border_value=args.border_value,
            batch_size=args.batch_size,
            hidden_dim=args.hidden_dim,
            device=args.device,
            mask_path=args.mask_out,
            crop_valid=args.crop_valid,
            crop_output_path=args.crop_out,
            canvas_mode=args.canvas_mode,
            expanded_bounds_step=args.expanded_bounds_step,
            expanded_margin=args.expanded_margin,
            metadata_path=args.metadata_out,
        )

    if not args.skip_validate:
        ok = validate_outputs(
            args.coords,
            args.diams,
            model_path,
            args.out_dir,
            image_path=args.image,
            calibrated_path=args.calibrated,
            mask_path=args.mask_out,
            hidden_dim=args.hidden_dim,
            csv_tolerance=args.csv_tolerance,
            center_marker_mode=args.center_marker_mode,
            center_marker_min_ratio=args.center_marker_min_ratio,
            allow_expanded_calibrated=args.canvas_mode == "expanded",
        )
        return 0 if ok else 1

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the neural calibration pipeline.")
    parser.add_argument("--coords", default="output/grid_coordinates.csv")
    parser.add_argument("--diams", default="output/grid_diameters.csv")
    parser.add_argument("--out-dir", default="output/neural_model")
    parser.add_argument("--model", default="output/neural_model/compensation_model.pth")
    parser.add_argument("--image", default="data/lowanu-bed-kalibrasi.tiff")
    parser.add_argument(
        "--calibrated", default="output/neural_model/calibrated_image.tiff"
    )

    parser.add_argument("--epochs", type=int, default=5000)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--target-loss", type=float, default=5.0)
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--smoothness-weight", type=float, default=1e-3)
    parser.add_argument("--edge-balance-weight", type=float, default=0.3)
    parser.add_argument(
        "--center-marker-mode", choices=CENTER_MARKER_MODES, default="auto"
    )
    parser.add_argument("--center-marker-min-ratio", type=float, default=1.5)

    parser.add_argument("--image-width", type=int, default=4096)
    parser.add_argument("--image-height", type=int, default=3000)
    parser.add_argument("--object-spacing", type=float, default=30.0)

    parser.add_argument("--step", type=int, default=4)
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=262144)
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    parser.add_argument(
        "--interpolation", default="linear", choices=["cubic", "linear", "nearest"]
    )
    parser.add_argument(
        "--border-mode",
        default="constant",
        choices=["constant", "reflect", "replicate"],
    )
    parser.add_argument("--border-value", type=float, default=0)
    parser.add_argument(
        "--mask-out", default="output/neural_model/calibrated_valid_mask.png"
    )
    parser.add_argument("--canvas-mode", choices=CANVAS_MODE, default="fixed")
    parser.add_argument("--expanded-bounds-step", type=int, default=4)
    parser.add_argument("--expanded-margin", type=int, default=16)
    parser.add_argument("--metadata-out", default=None)
    parser.add_argument("--crop-valid", action="store_true")
    parser.add_argument(
        "--crop-out", default="output/neural_model/calibrated_image_cropped.tiff"
    )

    parser.add_argument("--csv-tolerance", type=float, default=0.01)
    parser.add_argument("--skip-train", action="store_true")
    parser.add_argument("--skip-evaluate", action="store_true")
    parser.add_argument("--skip-opencv-comparison", action="store_true")
    parser.add_argument("--opencv-out-dir", default="output/opencv_baseline")
    parser.add_argument("--opencv-fix-aspect", action="store_true")
    parser.add_argument("--opencv-skip-image", action="store_true")
    parser.add_argument("--skip-warp", action="store_true")
    parser.add_argument("--skip-validate", action="store_true")
    args = parser.parse_args()

    sys.exit(main(args))
