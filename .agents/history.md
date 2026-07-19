# Agent History

This is an append-only session log. Do not rewrite earlier entries except to
fix formatting errors. To conserve context budget, archive older sessions into
files such as `.agents/history/archive_YYYY_Qx.md` once this file exceeds 15
to 20 entries.

## 2026-07-08 - Session 1: Bootstrap .agents Control Center

Goal: Bootstrap an enterprise-grade `.agents/` control center for this
repository.

Audit actions:

- Read `.agents/prompts/bootstrap-new-repo.md` as the implementation spec.
- Inspected project metadata in `pyproject.toml`, `.python-version`,
  `.env.production.example`, `Dockerfile`, and `docker/entrypoint.sh`.
- Reviewed product context in `README.md` and `docs/PRD.md`.
- Reviewed FastAPI app structure, API routes, security, storage, Celery worker
  configuration, DAG execution, schemas, node catalog, and tests.
- Checked for CI/CD workflows; no `.github/workflows/` files were detected.
- Attempted local verification:
  - `uv run pytest` could not run because `uv` is not installed.
  - `python3 -m pytest` could not run because `pytest` is not installed in the
    system Python environment.

Files created or updated:

- Created `.agents/README.md`.
- Created `.agents/history.md`.
- Created `.agents/memory.json`.
- Created `.agents/memory/state.md`.
- Created `.agents/rules/project-context.md`.
- Created `.agents/rules/python-fastapi-celery.md`.
- Updated `.agents/AGENTS.md`.
- Updated `.agents/prompts/prompts.md`.
- Updated `.agents/prompts/prd-generator.md`.
- Updated `.agents/prompts/verify-features-prd.md`.
- Updated `.agents/rules/server-access-constraints.md`.
- Updated `.agents/rules/testing-pyramid.md`.

Notes:

- The existing `.agents/prompts/bootstrap-new-repo.md` file was left untouched
  because it already had an uncommitted worktree change before this bootstrap.
- The older `.agents/` files contained stale Laravel/Pest/Dusk guidance; the
  active rules now describe the Python/FastAPI/Celery MPIPS service.

## 2026-07-08 - Session 2: Folder Refactor And Promotion Flow

Goal: Refactor MPIPS so experiments, importable package code, and backend
service code have clear boundaries.

Implementation actions:

- Moved `camera-callibration-dotgrid/` to
  `research/camera-calibration-dotgrid/` and `imager-pipeline/` to
  `research/imager-pipeline/`.
- Removed tracked `*:Zone.Identifier` Windows metadata files and ignored them
  for future changes.
- Promoted `mpips/` to the primary source package with `mpips.api`,
  `mpips.engine`, `mpips.storage`, `mpips.tenant_paths`, and `mpips.worker`.
- Initially kept `app/`, `image_engine/`, and `celery_tasks/` as compatibility
  shims, then removed them after the user clarified the desired structure
  should be clean rather than compatibility-first.
- Removed dashboard static frontend assets because MPIPS is a backend-only
  service.
- Added `LocalFileStorageBackend` for importable/local/Colab DAG execution.
- Added promoted calibration helper `mpips.engine.calibration.warp_image` and
  backend node `camera_calibration_warp`.
- Updated packaging extras, Docker entrypoint, README, and promotion-flow docs.

Verification:

- `.venv/bin/pip install -e ".[dev]"`
- `.venv/bin/uv lock`
- `.venv/bin/python - <<'PY' ... public import smoke ... PY`
- `.venv/bin/pytest -q` passed: 62 tests, 4 warnings.
- `.venv/bin/black --check .` passed.
- `.venv/bin/flake8 .` passed.
- `.venv/bin/mypy .` passed: no issues in 46 source files.

## 2026-07-14 - Session 3: Google Colab Integration & Research for `kambing-260714`

Goal: Enable interactive parameter tweaking and research of the image pipeline on Google Colab using the `kambing-260714` dataset.

Implementation actions:
- Inspected NPZ file contents under `research/kambing-260714/data/` (gain, kambing, kalibrasi-gotri).
- Created a wrapper process that loads NPZ arrays, matches radiographs to their respective gain file, formats them to uint16, and saves them to temporary TIFF files for pipeline processing compatibility.
- Programmatically generated an interactive Jupyter Notebook (`imager_pipeline_tweak.ipynb`) under `research/kambing-260714/` featuring Google Colab forms, parameter configuration, camera calibration steps, and matplotlib visualizations.
- Set up a virtual environment `.venv` and verified pipeline execution on the dataset.

Verification:
- Local python test execution of the wrapper logic completed successfully.
- Matplotlib and python-dotenv installed in the virtual environment.
- Processing output [output_test.tiff](file:///var/www/mpips/research/kambing-260714/output_test.tiff) validated.

## 2026-07-14 - Session 4: Fix Missing Calibration Dependencies

Goal: Fix `ModuleNotFoundError: No module named 'torch'` when running `imager_pipeline_tweak_local.ipynb`.

Implementation actions:
- Identified `torch` as a dependency of the `calibration` extra in `pyproject.toml`.
- Installed the missing dependencies using `.venv/bin/pip install -e '.[calibration]'`.

Verification:
- The installation command completed successfully, installing `torch` and other calibration dependencies.

## 2026-07-14: Refactor Neural Calibration
Moved the neural calibration step to after Flat-Field Correction (FFC) in `complete_pipeline.py`.
Modified `pipeline.py` to pass `map_x` and `map_y` into the engine rather than applying them preemptively.
Deleted the legacy `camera_calibration.py` (OpenCV) step to prevent it from ever being used.
Added integration test passing pipeline input with different sizes mimicking `expanded_canvas` remaps.
