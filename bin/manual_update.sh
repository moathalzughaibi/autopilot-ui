#!/usr/bin/env bash
set -euo pipefail
if [ -f /workspace/data/flags/OFFLINE ]; then
  echo "❌ OFFLINE مفعّل. احذف العلامة قبل التشغيل: rm -f /workspace/data/flags/OFFLINE"
  exit 1
fi
source /workspace/data/.venv/bin/activate || true
python /workspace/data/autopilot/jobs/update_all.py
