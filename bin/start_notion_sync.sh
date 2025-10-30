#!/usr/bin/env bash
set -euo pipefail
source /workspace/data/.venv/bin/activate || true
python /workspace/data/bin/notion_sync.py
