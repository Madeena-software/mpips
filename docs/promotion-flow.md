# MPIPS Promotion Flow

MPIPS keeps experimental code, importable engine code, and backend service code
separate.

## Folders

- `research/`: experiments, prototypes, notebooks, sample data, generated
  outputs, and one-off scripts.
- `mpips.engine`: importable image-processing logic, DAG execution, node
  registry, catalog metadata, and promoted calibration helpers.
- `mpips.api`: FastAPI routes, schemas, auth, docs, and health.
- `mpips.worker`: Celery task queue and webhook lifecycle.

## Promote Research Code

1. Start in `research/<topic>/`.
2. Move stable reusable logic to `mpips.engine` without FastAPI, Celery, Redis,
   or S3 dependencies.
3. Export import-only helpers from an engine package, for example
   `from mpips.engine.calibration import warp_image`.
4. For backend execution, create a node with `execute(inputs, params)`.
5. Register the node in `mpips.engine.registry`.
6. Add catalog metadata in `mpips.engine.catalog` so it appears in
   `GET /v1/nodes`.
7. Add tests for direct helper import, direct node execution, catalog exposure,
   and DAG execution.

Backend code must not import directly from `research/`.
