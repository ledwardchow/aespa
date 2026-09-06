#!/usr/bin/env bash
# Build a multi-arch image and push to Docker Hub. Usage: ./scripts/publish.sh <dockerhub-user>
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

USER="${1:-${DOCKER_USER:?set DOCKER_USER or pass username as arg}}"
VERSION=$(grep -m1 '^version = ' pyproject.toml | sed 's/.*"\(.*\)".*/\1/')

docker buildx build --platform linux/amd64,linux/arm64 \
  -t "$USER/aespa:$VERSION" \
  -t "$USER/aespa:latest" \
  --push .
