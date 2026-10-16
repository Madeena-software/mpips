#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "Building Stage B single-file ELF executable..."
.venv/bin/pyinstaller \
  --distpath build-standalone/dist \
  --workpath build-standalone/build-onefile \
  -y build-standalone/mpips_onefile.spec

mkdir -p dist-experimental
cp build-standalone/dist/mpips-runtime.bin dist-experimental/
sha256sum dist-experimental/mpips-runtime.bin > dist-experimental/mpips-runtime.bin.sha256
echo "Build complete: dist-experimental/mpips-runtime.bin"
cat dist-experimental/mpips-runtime.bin.sha256
