#!/bin/bash
# Run TWV Viewer directly from source (no packaging) for development/testing.
# Usage: ./run_dev.sh [path/to/video.twv]
set -euo pipefail
cd "$(dirname "$0")"

exec uv run main.py "$@"
