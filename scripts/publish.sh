#!/usr/bin/env bash
# Build a multi-arch image and push to Docker Hub and GHCR. Usage: ./scripts/publish.sh <dockerhub-user>
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

DOCKER_HUB_USERNAME="${1:-${DOCKER_USER:?set DOCKER_USER or pass username as arg}}"
VERSION=$(grep -m1 '^version = ' pyproject.toml | sed 's/.*"\(.*\)".*/\1/')

docker buildx build --platform linux/amd64,linux/arm64 \
  -t "docker.io/$DOCKER_HUB_USERNAME/aespa:$VERSION" \
  -t "docker.io/$DOCKER_HUB_USERNAME/aespa:latest" \
  -t "ghcr.io/ledwardchow/aespa:$VERSION" \
  -t "ghcr.io/ledwardchow/aespa:latest" \
  --push .
