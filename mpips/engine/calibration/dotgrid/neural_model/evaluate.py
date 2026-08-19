"""Compatibility exports for the canonical neural evaluation implementation."""

if __name__ == "__main__":
    import runpy

    runpy.run_module(
        "mpips.calibration.dotgrid.neural_model.evaluate", run_name="__main__"
    )
else:
    from mpips.calibration.dotgrid.neural_model.evaluate import (  # noqa: F401
        _diameter_values,
    )  # noqa: F401
    from mpips.calibration.dotgrid.neural_model.evaluate import (
        compute_all_metrics,
        compute_reprojection_error,
        compute_smia,
        estimate_brown_conrady,
        evaluate_model,
        format_center_marker_note,
        improvement_pct,
        load_model,
        plot_compensated_x,
        plot_compensated_y,
        plot_diameter_hist,
        plot_vertical_diameter_profile,
        write_advanced_metrics,
        write_basic_metrics,
    )

    __all__ = [
        "compute_all_metrics",
        "compute_reprojection_error",
        "compute_smia",
        "estimate_brown_conrady",
        "evaluate_model",
        "format_center_marker_note",
        "improvement_pct",
        "load_model",
        "plot_compensated_x",
        "plot_compensated_y",
        "plot_diameter_hist",
        "plot_vertical_diameter_profile",
        "write_advanced_metrics",
        "write_basic_metrics",
    ]
