#!/usr/bin/env bash
# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Build script for FunscriptForge packaged executable — macOS.
#
# Usage:
#   ./build.sh            — clean build into dist/FunscriptForge.app
#   ./build.sh --no-clean — skip cleaning dist/ and build/ first
#   ./build.sh --dmg      — also create a distributable DMG after building

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================================="
echo " FunscriptForge — macOS Package Build"
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
# Generate .icns if not present (requires macOS iconutil)
# -------------------------------------------------------
ICO_SRC="media/anvil.png"
ICNS_OUT="media/funscriptforge.icns"
if [ ! -f "$ICNS_OUT" ] && [ -f "$ICO_SRC" ]; then
    echo "[*] Generating $ICNS_OUT from $ICO_SRC..."
    ICONSET_DIR="$(mktemp -d)/FunscriptForge.iconset"
    mkdir -p "$ICONSET_DIR"
    for SIZE in 16 32 64 128 256 512; do
        sips -z "$SIZE" "$SIZE" "$ICO_SRC" --out "$ICONSET_DIR/icon_${SIZE}x${SIZE}.png" &>/dev/null
        DOUBLE=$((SIZE * 2))
        sips -z "$DOUBLE" "$DOUBLE" "$ICO_SRC" --out "$ICONSET_DIR/icon_${SIZE}x${SIZE}@2x.png" &>/dev/null
    done
    iconutil -c icns "$ICONSET_DIR" -o "$ICNS_OUT"
    rm -rf "$(dirname "$ICONSET_DIR")"
    echo "      $ICNS_OUT created."
    echo
fi

# -------------------------------------------------------
# Clean previous build artifacts
# -------------------------------------------------------
if [[ "${1:-}" != "--no-clean" && "${2:-}" != "--no-clean" ]]; then
    echo "[2/4] Cleaning dist/ and build/..."
    rm -rf dist/FunscriptForge dist/FunscriptForge.app build/FunscriptForge
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
if [ -d "dist/FunscriptForge.app" ]; then
    echo "      SUCCESS — dist/FunscriptForge.app created."
    echo
    echo " To run:   open dist/FunscriptForge.app"
    echo " To share: zip the dist/FunscriptForge.app bundle."
else
    echo "[ERROR] Expected dist/FunscriptForge.app not found."
    exit 1
fi

# -------------------------------------------------------
# Optional DMG creation
# -------------------------------------------------------
if [[ "${1:-}" == "--dmg" || "${2:-}" == "--dmg" ]]; then
    echo
    echo "[+] Creating DMG..."
    DMG_NAME="dist/FunscriptForge.dmg"
    hdiutil create \
        -volname "FunscriptForge" \
        -srcfolder "dist/FunscriptForge.app" \
        -ov -format UDZO \
        "$DMG_NAME"
    echo "      $DMG_NAME created."
fi

echo
echo "=========================================================="
echo " Build complete."
echo "=========================================================="
