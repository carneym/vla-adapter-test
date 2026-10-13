#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "$(uname -s)" != Darwin || "$(uname -m)" != arm64 ]]; then
  echo "This setup targets Apple Silicon Macs (M2/M4). Modal training is separate." >&2
  exit 1
fi
if ! command -v uv >/dev/null 2>&1; then
  echo "Install uv first: brew install uv" >&2
  echo "Then rerun: bash scripts/setup.sh" >&2
  exit 1
fi
# Keep installation files inside this checkout; do not alter another Python env.
export UV_CACHE_DIR="${UV_CACHE_DIR:-$PWD/.cache/uv}"
export UV_PYTHON_INSTALL_DIR="${UV_PYTHON_INSTALL_DIR:-$PWD/.python}"
uv sync --locked
uv run --locked so101 init --machine "${1:-macbook}"
uv run --locked so101 doctor --check
