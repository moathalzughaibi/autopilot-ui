#!/usr/bin/env bash
set -euo pipefail

MIN_GAP_MINUTES="${1:-30}"                       # الحد الأدنى بين تشغيل وآخر (بالدقائق)
STAMP="/workspace/data/logs/.timeline_last_run"  # ملف ختم وقت آخر تشغيل

now_ts="$(date +%s)"
last_ts=0
[ -f "$STAMP" ] && last_ts="$(cat "$STAMP" 2>/dev/null || echo 0)"

gap=$(( (now_ts - last_ts) / 60 ))
if [ "$gap" -lt "$MIN_GAP_MINUTES" ]; then
  echo "Skip timeline sync (last run $gap min ago; min gap $MIN_GAP_MINUTES)."
  exit 0
fi

# نفّذ الدفعة
source /workspace/data/.venv/bin/activate || true
/workspace/data/bin/run_timeline_once.sh || true

# حدّث الختم
date +%s > "$STAMP"
echo "Timeline sync done."
