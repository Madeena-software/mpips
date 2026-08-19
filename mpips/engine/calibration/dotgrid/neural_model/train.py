"""Compatibility exports for the canonical neural training implementation."""

if __name__ == "__main__":
    import runpy

    runpy.run_module(
        "mpips.calibration.dotgrid.neural_model.train", run_name="__main__"
    )
else:
    from mpips.calibration.dotgrid.neural_model.train import train_model

    __all__ = ["train_model"]
