# Canonical imager pipeline

The completed Madeena imager research pipeline now lives in
`mpips.engine.imager_pipeline`. Its original processing functions, ImageJ
replication, command-line flow, calibration examples, pairing utility,
no-FFC flow, and DICOM converter are maintained as importable modules.

Install the optional dependencies and run the original complete pipeline:

```bash
pip install -e '.[imager]'
mpips-imager
# Equivalent module form:
python -m mpips.engine.imager_pipeline.complete_pipeline
```

Set `MPIPS_RADIOGRAPHY_ENV=/path/to/settings.env` to select a configuration
file. If it is unset, the engine checks `.env` in the current working
directory. Library and Colab callers should normally use
`mpips.workflows.imager_pipeline`, which applies a configuration object and stages
NPZ arrays without changing the canonical numerical implementation.

The ImageJ replication module retains its GPL-v2 notice. See
`THIRD_PARTY_NOTICES.md`; distribution licensing requires owner/legal review.
