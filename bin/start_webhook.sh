#!/usr/bin/env bash
set -euo pipefail
LOG=/workspace/data/logs/webhook_pull.log
PID=/workspace/data/logs/webhook_pull.pid

# عدّل السر هنا أو عبر ENV قبل التشغيل
export GITHUB_WEBHOOK_SECRET="${GITHUB_WEBHOOK_SECRET:-change_me}"

# لا تشغّل مثيل ثاني
if [ -f "$PID" ] && ps -p "$(cat "$PID")" >/dev/null 2>&1; then
  echo "webhook already running: PID $(cat "$PID")"; exit 0
fi

setsid nohup bash -lc 'cd /workspace/data && uvicorn bin.webhook_pull:app --host 0.0.0.0 --port 9088' \
  >> "$LOG" 2>&1 < /dev/null &

echo $! > "$PID"
echo "✅ webhook started. PID=$(cat $PID); LOG=$LOG; PORT=9088"
