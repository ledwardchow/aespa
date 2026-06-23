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
ENTITLEMENTS="entitlements.plist"

# Auto-pick the signing identity if there's exactly one Developer ID Application
# cert in the keychain. Set SIGN_ID explicitly to override or to disambiguate.
if [ -z "${SIGN_ID:-}" ]; then
  IDS=$(security find-identity -v -p codesigning \
    | grep -o '"Developer ID Application:[^"]*"' | sed 's/^"//;s/"$//')
  COUNT=$(printf '%s\n' "$IDS" | grep -c .)
  if [ "$COUNT" -eq 1 ]; then
    SIGN_ID="$IDS"
    echo "==> Using the only Developer ID Application identity: $SIGN_ID"
  elif [ "$COUNT" -eq 0 ]; then
    echo "No 'Developer ID Application' identity in keychain. Set SIGN_ID."; exit 1
  else
    echo "Multiple Developer ID Application identities — set SIGN_ID to one of:"
    printf '  %s\n' "$IDS"; exit 1
  fi
fi
[ -d "$APP" ] || { echo "Not found: $APP — run ./build_mac.sh first."; exit 1; }

echo "==> Signing nested binaries (inner-out)"
# Sign EVERY Mach-O first, then the bundle, so the outer signature seals valid
# inner ones. Detect by content (file), not extension — bundled executables like
# playwright/driver/node have no suffix and `codesign --deep` won't reach them,
# but the notary scans every Mach-O.
find "$APP" -type f -print0 | while IFS= read -r -d '' f; do
  case "$(file -b "$f")" in
    *Mach-O*)
      codesign --force --options runtime --timestamp --sign "$SIGN_ID" "$f" ;;
  esac
done

echo "==> Signing the app bundle"
codesign --force --options runtime --timestamp \
  --entitlements "$ENTITLEMENTS" --sign "$SIGN_ID" "$APP"
codesign --verify --deep --strict --verbose=2 "$APP"

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
