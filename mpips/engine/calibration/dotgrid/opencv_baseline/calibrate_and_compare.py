"""Compatibility exports for the canonical OpenCV baseline."""

from mpips.calibration.dotgrid.opencv_baseline.calibrate_and_compare import (
    METRIC_SPECS,
    calibrate_opencv,
    comparison_rows,
    compute_neural_result,
    compute_undistorted_diameters,
    dist_coeff_dict,
    format_number,
    format_pct,
    image_size_from_file,
    main,
    make_object_points,
    metric_reduction,
    plot_metric_comparison,
    run_opencv_comparison,
    undistort_image,
    undistort_points,
    write_comparison_csv,
    write_parameters_json,
    write_report,
)

__all__ = [
    "METRIC_SPECS",
    "image_size_from_file",
    "make_object_points",
    "calibrate_opencv",
    "undistort_points",
    "compute_undistorted_diameters",
    "compute_neural_result",
    "undistort_image",
    "metric_reduction",
    "format_number",
    "format_pct",
    "dist_coeff_dict",
    "write_parameters_json",
    "comparison_rows",
    "write_comparison_csv",
    "write_report",
    "plot_metric_comparison",
    "run_opencv_comparison",
    "main",
]

if __name__ == "__main__":
    main()
