#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

test -x .venv/bin/python || { echo "Run ./scripts/setup.sh first"; exit 1; }
test -f .env || echo "Notice: .env is missing; copy .env.example to .env"
command -v ffmpeg >/dev/null || echo "Notice: FFmpeg is not installed yet"

PYTHONPATH=src .venv/bin/python -m ai_youtube doctor

