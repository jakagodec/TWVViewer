#!/bin/bash
# Build "TWV Viewer.app" using PyInstaller.
# Usage: ./build_app.sh
set -euo pipefail
cd "$(dirname "$0")"

rm -rf build dist
uv run --group build pyinstaller build.spec

echo ""
echo "Build complete: dist/TWV Viewer.app"
echo "Move it to /Applications, then see README.md to set it as the default .twv handler."
