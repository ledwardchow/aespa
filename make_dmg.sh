#!/usr/bin/env bash
# Build dist/AESPA.dmg with a "drag to Applications" install layout.
# Run AFTER ./build_mac.sh (and ./notarize_mac.sh if distributing).
#
#   brew install create-dmg     # one-time
#   ./make_dmg.sh
#
# Signs the .dmg too if a Developer ID Application identity is available
# (auto-detected, or set SIGN_ID).
set -euo pipefail
cd "$(dirname "$0")"

APP="${APP:-dist/AESPA.app}"
DMG="${DMG:-dist/AESPA.dmg}"
NOTARY_PROFILE="${NOTARY_PROFILE:-aespa-notary}"

command -v create-dmg >/dev/null || { echo "Missing create-dmg — run: brew install create-dmg"; exit 1; }
[ -d "$APP" ] || { echo "Not found: $APP — run ./build_mac.sh first."; exit 1; }

# Auto-pick a signing identity (skip signing if none — the .dmg still works).
if [ -z "${SIGN_ID:-}" ]; then
  SIGN_ID=$(security find-identity -v -p codesigning \
    | grep -o '"Developer ID Application:[^"]*"' | sed 's/^"//;s/"$//' | head -1)
fi
SIGN_ARGS=()
[ -n "$SIGN_ID" ] && SIGN_ARGS=(--codesign "$SIGN_ID") && echo "==> Will sign dmg with: $SIGN_ID"

rm -f "$DMG"
echo "==> Building $DMG"
create-dmg \
  --volname "AESPA" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "AESPA.app" 150 190 \
  --app-drop-link 450 190 \
  --hdiutil-quiet \
  "${SIGN_ARGS[@]}" \
  "$DMG" "$APP"

if [ "${SKIP_NOTARIZE:-}" = "1" ]; then
  echo "==> SKIP_NOTARIZE=1 — leaving $DMG un-notarized."
else
  echo "==> Notarizing the dmg (covers the app inside too; a few minutes)"
  OUT=$(xcrun notarytool submit "$DMG" --keychain-profile "$NOTARY_PROFILE" --wait 2>&1) || true
  echo "$OUT"
  if printf '%s\n' "$OUT" | grep -q "status: Accepted"; then
    xcrun stapler staple "$DMG"
  else
    SUBID=$(printf '%s\n' "$OUT" | awk '/id:/{print $2; exit}')
    echo "==> Notarization not accepted. Failure log:"
    [ -n "$SUBID" ] && xcrun notarytool log "$SUBID" --keychain-profile "$NOTARY_PROFILE"
    exit 1
  fi
fi

echo "==> Done: $DMG"
