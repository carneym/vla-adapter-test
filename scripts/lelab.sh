#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export UV_CACHE_DIR="${UV_CACHE_DIR:-$PWD/.cache/uv}"
export UV_PROJECT_ENVIRONMENT="$PWD/.cache/lelab/venv"
exec uv run --project integrations/lelab --locked python "$PWD/scripts/run_lelab.py" "$@"
