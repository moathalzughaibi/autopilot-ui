#!/usr/bin/env bash
set -euo pipefail
INTERVAL_MIN="${1:-60}"
LOG="/workspace/data/logs/updater.log"
PID="/workspace/data/logs/updater.pid"
LOCK="/workspace/data/logs/updater.lock"

source /workspace/data/.venv/bin/activate
export PYTHONPATH=/workspace/data:$PYTHONPATH
mkdir -p /workspace/data/logs
touch "$LOG"

# لا تعيد تشغيله إن كان شغال
if [ -f "$PID" ] && ps -p "$(cat "$PID")" >/dev/null 2>&1; then
  echo "Updater already running with PID $(cat "$PID")"; exit 0
fi

SLEEP_SEC=$((INTERVAL_MIN*60))

# تدوير مبسط للّوج عند 5MB
if [ -f "$LOG" ] && [ $(stat -c%s "$LOG") -gt $((5*1024*1024)) ]; then
  mv "$LOG" "${LOG}.$(date +%Y%m%d%H%M%S)"
  : > "$LOG"
fi

# مستوى واحد فقط + تمرير المتغيرات كبيئة
setsid nohup env LOG="$LOG" LOCK="$LOCK" SLEEP_SEC="$SLEEP_SEC" bash -c '
  set +u
  while true; do
    (
      flock -n 9 || exit 0
      printf "[%s] running update_all.py\n" "$(date -u +%FT%TZ)"
      python /workspace/data/autopilot/jobs/update_all.py || true
      printf "[%s] done\n" "$(date -u +%FT%TZ)"
    ) 9>"$LOCK"
    sleep "$SLEEP_SEC"
  done
' </dev/null >> "$LOG" 2>&1 &

echo $! > "$PID"
sleep 1
echo "✅ updater started (every ${INTERVAL_MIN}m). PID=$(cat "$PID")"
echo "LOG: $LOG"
