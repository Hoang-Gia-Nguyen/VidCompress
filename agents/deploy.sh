#!/usr/bin/env bash

# Exit on error, undefined variable, or pipe failure
set -euo pipefail

# Default image name; can be overridden via env or argument
VERSION=${1:-latest}
IMAGE_NAME="transcode-app:${VERSION}"

# Build Docker image
docker build -t "$IMAGE_NAME" .

# Tag for registry if REGISTRY env var is set
if [ -n "${REGISTRY:-}" ]; then
  FULL_TAG="${REGISTRY}/${IMAGE_NAME}"
  docker tag "$IMAGE_NAME" "$FULL_TAG"
  echo "Pushing Docker image to $FULL_TAG"
  docker push "$FULL_TAG"
else
  echo "Registry not set; skipping push. Built image $IMAGE_NAME is available locally."
fi

# Optional: run container (placeholder, can be customized)
# docker run -d --name transcode-app "$IMAGE_NAME"

