#!/usr/bin/env bash
# Build and publish the AESPA Python executor as one amd64/arm64 image manifest.
set -euo pipefail

cd "$(dirname "$0")/.."

usage() {
  cat <<'EOF'
Usage: ./scripts/publish_python_executor.sh DOCKER_HUB_USERNAME

Examples:
  docker login docker.io
  ./scripts/publish_python_executor.sh acme

Authenticate with Docker Hub before running this script. It publishes
docker.io/USERNAME/aespa-python-executor:0.1 with both linux/amd64 and
linux/arm64 images.
EOF
}

if [ "$#" -ne 1 ]; then
  usage >&2
  exit 2
fi

DOCKER_HUB_USERNAME="$1"
if [[ ! "$DOCKER_HUB_USERNAME" =~ ^[a-z0-9][a-z0-9_-]{0,254}$ ]]; then
  echo "Error: invalid Docker Hub username: $DOCKER_HUB_USERNAME" >&2
  usage >&2
  exit 2
fi
IMAGE_REF="docker.io/$DOCKER_HUB_USERNAME/aespa-python-executor:0.1"

command -v docker >/dev/null || {
  echo "Error: Docker is not installed or is not on PATH." >&2
  exit 1
}
docker info >/dev/null
docker buildx version >/dev/null

BUILDER="${AESPA_BUILDX_BUILDER:-aespa-multiarch}"
if docker buildx inspect "$BUILDER" >/dev/null 2>&1; then
  docker buildx use "$BUILDER"
else
  echo "==> Creating buildx builder: $BUILDER"
  docker buildx create --name "$BUILDER" --driver docker-container --use >/dev/null
fi
docker buildx inspect --bootstrap >/dev/null

echo "==> Publishing linux/amd64 and linux/arm64 as $IMAGE_REF"
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --pull \
  --provenance=true \
  --sbom=true \
  --tag "$IMAGE_REF" \
  --push \
  runtime/python-executor

echo "==> Published manifest"
docker buildx imagetools inspect "$IMAGE_REF"
