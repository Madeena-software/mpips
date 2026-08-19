"""Compatibility exports for the canonical neural image-warp implementation."""

if __name__ == "__main__":
    import runpy

    runpy.run_module(
        "mpips.calibration.dotgrid.neural_model.warp_image", run_name="__main__"
    )
else:
    from mpips.calibration.dotgrid.neural_model.warp_image import (  # noqa: F401
        _axis_samples,
    )  # noqa: F401
    from mpips.calibration.dotgrid.neural_model.warp_image import (
        BORDER_MODE,
        CANVAS_MODE,
        INTERPOLATION,
        build_inverse_maps,
        compute_valid_mask,
        ensure_parent_dir,
        estimate_expanded_canvas,
        largest_valid_rectangle,
        load_model,
        resolve_device,
        warp_image,
    )

    __all__ = [
        "BORDER_MODE",
        "CANVAS_MODE",
        "INTERPOLATION",
        "build_inverse_maps",
        "compute_valid_mask",
        "ensure_parent_dir",
        "estimate_expanded_canvas",
        "largest_valid_rectangle",
        "load_model",
        "resolve_device",
        "warp_image",
    ]
