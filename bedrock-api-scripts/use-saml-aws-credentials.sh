#!/usr/bin/env bash

# Source this file to load AWS temporary credentials into the current shell:
#   source ./use-saml-aws-credentials.sh
#
# Defaults can be overridden with environment variables before sourcing:
#   AWS_REGION=us-east-1 DURATION_SECONDS=3600 source ./use-saml-aws-credentials.sh
#   ROLE_ARN=... PRINCIPAL_ARN=... source ./use-saml-aws-credentials.sh

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "This script must be sourced so exported credentials remain in your shell:" >&2
  echo "  source ./use-saml-aws-credentials.sh" >&2
  exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SAML_ASSERTION_FILE="${SAML_ASSERTION_FILE:-$SCRIPT_DIR/saml.b64}"
AWS_REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-ap-southeast-2}}"
DURATION_SECONDS="${DURATION_SECONDS:-3600}"

if ! command -v aws >/dev/null 2>&1; then
  echo "AWS CLI was not found. Install AWS CLI v2 first." >&2
  return 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 was not found. It is required to parse the SAML assertion and AWS response." >&2
  return 1
fi

if [[ ! -f "$SAML_ASSERTION_FILE" ]]; then
  echo "SAML assertion file not found: $SAML_ASSERTION_FILE" >&2
  return 1
fi

detect_output="$({
python3 - "$SAML_ASSERTION_FILE" <<'PY'
import base64
import sys
import xml.etree.ElementTree as ET

path = sys.argv[1]
raw = open(path, "rb").read().strip()
try:
    xml_text = base64.b64decode(raw).decode("utf-8")
except Exception as exc:
    raise SystemExit(f"Could not base64-decode SAML assertion: {exc}")

try:
    root = ET.fromstring(xml_text)
except Exception as exc:
    raise SystemExit(f"Could not parse SAML XML: {exc}")

role_attr = "https://aws.amazon.com/SAML/Attributes/Role"
pairs = []
for attr in root.iter():
    if attr.tag.rsplit("}", 1)[-1] != "Attribute":
        continue
    if attr.attrib.get("Name") != role_attr:
        continue
    for child in attr:
        if child.tag.rsplit("}", 1)[-1] != "AttributeValue":
            continue
        parts = [p.strip() for p in (child.text or "").split(",")]
        role = next((p for p in parts if ":role/" in p), None)
        principal = next((p for p in parts if ":saml-provider/" in p), None)
        if role and principal:
            pairs.append((role, principal))

if not pairs:
    raise SystemExit("Could not find AWS role/principal ARNs in SAML assertion")

for role, principal in pairs:
    print(f"{role}\t{principal}")
PY
} 2>&1)" || {
  echo "$detect_output" >&2
  return 1
}

if [[ -z "${ROLE_ARN:-}" || -z "${PRINCIPAL_ARN:-}" ]]; then
  mapfile -t detected_pairs <<< "$detect_output"
  if [[ "${#detected_pairs[@]}" -gt 1 ]]; then
    echo "Multiple AWS roles found in $SAML_ASSERTION_FILE. Using the first one." >&2
    echo "Set ROLE_ARN and PRINCIPAL_ARN before sourcing this script to choose a different role." >&2
    for i in "${!detected_pairs[@]}"; do
      IFS=$'\t' read -r detected_role detected_principal <<< "${detected_pairs[$i]}"
      echo "[$i] $detected_role" >&2
      echo "    $detected_principal" >&2
    done
  fi

  IFS=$'\t' read -r auto_role_arn auto_principal_arn <<< "${detected_pairs[0]}"
  ROLE_ARN="${ROLE_ARN:-$auto_role_arn}"
  PRINCIPAL_ARN="${PRINCIPAL_ARN:-$auto_principal_arn}"
fi

echo "Assuming AWS role:"
echo "  RoleArn:      $ROLE_ARN"
echo "  PrincipalArn: $PRINCIPAL_ARN"
echo "  Duration:     $DURATION_SECONDS seconds"
echo "  Region:       $AWS_REGION"

assume_output="$({
aws sts assume-role-with-saml \
  --role-arn "$ROLE_ARN" \
  --principal-arn "$PRINCIPAL_ARN" \
  --saml-assertion "file://$SAML_ASSERTION_FILE" \
  --duration-seconds "$DURATION_SECONDS" \
  --output json
} 2>&1)" || {
  echo "$assume_output" >&2
  return 1
}

creds_output="$({
ASSUME_OUTPUT="$assume_output" python3 - <<'PY'
import json
import os
import sys

data = json.loads(os.environ["ASSUME_OUTPUT"])
creds = data.get("Credentials") or {}
required = ("AccessKeyId", "SecretAccessKey", "SessionToken", "Expiration")
missing = [key for key in required if not creds.get(key)]
if missing:
    raise SystemExit(f"AWS STS response is missing: {', '.join(missing)}")

print(creds["AccessKeyId"])
print(creds["SecretAccessKey"])
print(creds["SessionToken"])
print(creds["Expiration"])
PY
} 2>&1)" || {
  echo "$creds_output" >&2
  return 1
}

mapfile -t credential_lines <<< "$creds_output"

export AWS_ACCESS_KEY_ID="${credential_lines[0]}"
export AWS_SECRET_ACCESS_KEY="${credential_lines[1]}"
export AWS_SESSION_TOKEN="${credential_lines[2]}"
export AWS_REGION
export AWS_DEFAULT_REGION="$AWS_REGION"

# Avoid accidentally using a stale AWS profile instead of these env credentials.
unset AWS_PROFILE

echo "AWS credentials loaded into current shell."
echo "Expires: ${credential_lines[3]}"
echo "Test with: aws sts get-caller-identity"