"""Compatibility exports for canonical neural-output validation."""

if __name__ == "__main__":
    import runpy

    runpy.run_module(
        "mpips.calibration.dotgrid.neural_model.validate_outputs", run_name="__main__"
    )
else:
    from mpips.calibration.dotgrid.neural_model.validate_outputs import (
        REQUIRED_OUTPUTS,
        check_calibrated_image,
        check_file_outputs,
        check_mask_image,
        load_coordinate_csv,
        require,
        validate_outputs,
    )

    __all__ = [
        "REQUIRED_OUTPUTS",
        "check_calibrated_image",
        "check_file_outputs",
        "check_mask_image",
        "load_coordinate_csv",
        "require",
        "validate_outputs",
    ]
