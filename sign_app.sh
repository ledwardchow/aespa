#!/usr/bin/env bash
# Sign dist/AESPA.app with hardened runtime: every Mach-O inner-out, then the
# bundle with entitlements. Idempotent (--force re-signs). Called by both
# notarize_only_mac.sh and make_dmg.sh so the app is ALWAYS signed before it is
# notarized or packed into a dmg — running either script alone is safe.
set -euo pipefail
cd "$(dirname "$0")"

APP="${APP:-dist/AESPA.app}"
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

echo "==> Signing nested binaries (every Mach-O, inner-out)"
# Detect by content (file), not extension — bundled executables like
# playwright/driver/node have no suffix and `codesign --deep` won't reach them,
# but the notary scans every Mach-O.
# Nested binaries get the SAME entitlements as the bundle. Playwright's bundled
# `node` driver runs V8, which JITs (write+execute memory); under hardened
# runtime without allow-jit / allow-unsigned-executable-memory the OS kills it
# mid-run → "Connection closed while reading from the driver" and crawls die.
find "$APP" -type f -print0 | while IFS= read -r -d '' f; do
  case "$(file -b "$f")" in
    *Mach-O*)
      codesign --force --options runtime --timestamp \
        --entitlements "$ENTITLEMENTS" --sign "$SIGN_ID" "$f" ;;
  esac
done

echo "==> Signing the app bundle"
codesign --force --options runtime --timestamp \
  --entitlements "$ENTITLEMENTS" --sign "$SIGN_ID" "$APP"
codesign --verify --deep --strict --verbose=2 "$APP"
echo "==> Signed: $APP"
