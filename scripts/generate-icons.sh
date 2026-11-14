#!/usr/bin/env bash
# Run with: bash scripts/generate-icons.sh (requires FFmpeg with librsvg).
set -euo pipefail
cd "$(dirname "$0")/.."
icons="frontend/static/icons"
for size in 32 180 192 512; do
  ffmpeg -hide_banner -loglevel error -y -i "$icons/icon.svg" \
    -vf "scale=$size:$size:flags=lanczos" -frames:v 1 -update 1 \
    "$icons/icon-$size.png"
done
