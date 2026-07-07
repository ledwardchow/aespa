#!/usr/bin/env bash
# Build AESPA.app for macOS. Output: dist/AESPA.app
# Chromium is NOT bundled — it downloads into ~/Library/Application Support/aespa
# on first launch.
set -euo pipefail
cd "$(dirname "$0")"

ICON_SRC="src/aespa/web/icon.png"
ICONSET="build/AESPA.iconset"
ICNS="build/AESPA.icns"

echo "==> Generating .icns from $ICON_SRC"
rm -rf "$ICONSET"
mkdir -p "$ICONSET"
for size in 16 32 128 256 512; do
  sips -z "$size" "$size"         "$ICON_SRC" --out "$ICONSET/icon_${size}x${size}.png"   >/dev/null
  sips -z $((size*2)) $((size*2)) "$ICON_SRC" --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$ICNS"

echo "==> Building isolated build env (non-editable install)"
# Build against a NON-editable install so PyInstaller can collect a COMPLETE
# dist-info. uv's editable install leaves dangling metadata files (INSTALLER,
# METADATA, RECORD…) that crash PyInstaller's macOS BUNDLE step.
BUILD_VENV="build/venv"
rm -rf "$BUILD_VENV"
uv venv "$BUILD_VENV" >/dev/null
# Constrain to uv.lock so the bundled Playwright matches the dev env. Without
# this, `.`'s `playwright>=…` spec resolves to the newest release, whose browser
# build (e.g. v1228) differs from what dev/users have cached (v1223) — the app
# then can't find its headless-shell and first-run must re-download 260MB.
VIRTUAL_ENV="$BUILD_VENV" uv pip install --quiet \
    --constraint <(uv export --no-emit-project --no-hashes) \
    . pyinstaller pyobjc-framework-WebKit

echo "==> Generating THIRD_PARTY_LICENSES.txt"
# Attribution for the bundled MIT/BSD/Apache/MPL deps. Run against the build venv
# so it lists exactly what gets frozen into the app.
"$BUILD_VENV/bin/python" scripts/generate_third_party_licenses.py THIRD_PARTY_LICENSES.txt

echo "==> Building app bundle with PyInstaller"
# --collect-all playwright pulls in its node driver so first-run install works
# in the bundle; AESPA_BUNDLED is read at runtime (frozen sets sys.frozen too).
"$BUILD_VENV/bin/pyinstaller" \
    --noconfirm \
    --windowed \
    --name AESPA \
    --icon "$ICNS" \
    --osx-bundle-identifier com.aespa.app \
    --add-data "src/aespa/web:aespa/web" \
    --add-data "THIRD_PARTY_LICENSES.txt:." \
    --add-data "LICENSE:." \
    --collect-all playwright \
    --collect-submodules aespa \
    src/aespa/desktop.py

echo "==> Done: dist/AESPA.app"
echo "    Unsigned — first open: right-click > Open, or run:"
echo "    xattr -dr com.apple.quarantine dist/AESPA.app"
echo "    To distribute: ./make_dmg.sh  (signs + notarizes + builds the dmg)"
