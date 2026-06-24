#!/usr/bin/env bash
# Sign, notarize, and staple dist/AESPA.app.
#
# Prereqs (one-time):
#   - Apple Developer Program + a "Developer ID Application" cert in your keychain
#   - cache notary creds once:
#       xcrun notarytool store-credentials aespa-notary \
#         --apple-id you@example.com --team-id TEAMID --password APP-SPECIFIC-PW
#
# Usage:
#   SIGN_ID="Developer ID Application: Your Name (TEAMID)" ./notarize_mac.sh
#   (optional) NOTARY_PROFILE=aespa-notary  APP=dist/AESPA.app
set -euo pipefail
cd "$(dirname "$0")"

APP="${APP:-dist/AESPA.app}"
NOTARY_PROFILE="${NOTARY_PROFILE:-aespa-notary}"

./sign_app.sh

echo "==> Submitting for notarization (this can take a few minutes)"
ZIP="dist/AESPA.zip"
ditto -c -k --keepParent "$APP" "$ZIP"
OUT=$(xcrun notarytool submit "$ZIP" --keychain-profile "$NOTARY_PROFILE" --wait 2>&1) || true
echo "$OUT"
rm -f "$ZIP"
# `submit --wait` exits 0 even when the verdict is Invalid, so check explicitly.
if ! printf '%s\n' "$OUT" | grep -q "status: Accepted"; then
  SUBID=$(printf '%s\n' "$OUT" | awk '/id:/{print $2; exit}')
  echo "==> Notarization was not accepted. Failure log:"
  [ -n "$SUBID" ] && xcrun notarytool log "$SUBID" --keychain-profile "$NOTARY_PROFILE"
  exit 1
fi

echo "==> Stapling the ticket"
xcrun stapler staple "$APP"

echo "==> Verifying Gatekeeper acceptance"
spctl -a -vvv -t install "$APP"
echo "==> Done. $APP is signed, notarized, and stapled."
