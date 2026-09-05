# Repository artifact policy

Keep source code, tests, configuration, small deterministic manifests, and
lightweight characterization evidence in Git. Runtime-required calibration
payloads may remain tracked only when the deployment workflow consumes them
directly; otherwise keep large datasets and generated outputs in approved
external storage.

Do not commit calibration TIFF inputs, generated calibration output, bundled
paper PDFs, or exploratory notebooks. When a large input or output is needed,
record its authoritative location, checksum, and reproduction or provisioning
step in the governing task or a lightweight manifest. Do not invent an external
URL or upload data as part of repository maintenance. Explicit approval is
required for new large tracked artifacts.
