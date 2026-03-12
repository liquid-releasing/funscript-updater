#!/usr/bin/env bash
# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Build script for FunscriptForge packaged executable — Linux.
#
# Usage:
#   ./build_linux.sh            — clean build into dist/FunscriptForge/
#   ./build_linux.sh --no-clean — skip cleaning dist/ and build/ first
#   ./build_linux.sh --tarball  — also create dist/FunscriptForge-linux.tar.gz

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================================="
echo " FunscriptForge — Linux Package Build"
echo "=========================================================="
echo

# -------------------------------------------------------
# Check Python
# -------------------------------------------------------
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 not found on PATH. Install Python 3.10+ and try again."
    exit 1
fi
python3 --version

# -------------------------------------------------------
# Install / upgrade build dependencies
# -------------------------------------------------------
echo
echo "[1/4] Installing build dependencies..."
pip3 install --quiet --upgrade pyinstaller
pip3 install --quiet -r requirements.txt
pip3 install --quiet -r ui/streamlit/requirements.txt
echo "      Done."
echo

# -------------------------------------------------------
# Clean previous build artifacts
# -------------------------------------------------------
if [[ "${1:-}" != "--no-clean" && "${2:-}" != "--no-clean" ]]; then
    echo "[2/4] Cleaning dist/ and build/..."
    rm -rf dist/FunscriptForge build/FunscriptForge
    echo "      Done."
    echo
else
    echo "[2/4] Skipping clean (--no-clean)."
    echo
fi

# -------------------------------------------------------
# Run PyInstaller
# -------------------------------------------------------
echo "[3/4] Running PyInstaller..."
pyinstaller funscript_forge.spec --noconfirm
echo "      Done."
echo

# -------------------------------------------------------
# Verify output
# -------------------------------------------------------
echo "[4/4] Verifying output..."
if [ -f "dist/FunscriptForge/FunscriptForge" ]; then
    echo "      SUCCESS — dist/FunscriptForge/ created."
    echo
    echo " To run:   ./dist/FunscriptForge/FunscriptForge"
    echo " To share: use --tarball or manually tar.gz the dist/FunscriptForge/ folder."
else
    echo "[ERROR] Expected dist/FunscriptForge/FunscriptForge not found."
    exit 1
fi

# -------------------------------------------------------
# Optional tarball creation
# -------------------------------------------------------
if [[ "${1:-}" == "--tarball" || "${2:-}" == "--tarball" ]]; then
    echo
    echo "[+] Creating tarball..."
    TARBALL="dist/FunscriptForge-linux.tar.gz"
    tar -czf "$TARBALL" -C dist FunscriptForge
    echo "      $TARBALL created."
fi

echo
echo "=========================================================="
echo " Build complete."
echo "=========================================================="
