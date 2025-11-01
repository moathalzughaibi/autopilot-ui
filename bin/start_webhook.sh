#!/usr/bin/env bash
set -euo pipefail
PORT="${1:-8889}"
LOG="/workspace/data/logs/webhook_pull.log"
PID="/workspace/data/logs/webhook_pull.pid"
APP_DIR="/workspace/data/bin"
UVICORN="/workspace/data/.venv/bin/uvicorn"

# أوقف إن كان شغال
if [ -f "$PID" ] && ps -p "$(cat "$PID")" >/dev/null 2>&1; then
  kill -9 "$(cat "$PID")" 2>/dev/null || true
  rm -f "$PID"
fi

: > "$LOG"
# انتبه: لا توجد أي مسافة بعد "\" في السطر التالي
setsid nohup "$UVICORN" webhook_pull:app \
  --app-dir "$APP_DIR" \
  --host 0.0.0.0 --port "$PORT" \
  >> "$LOG" 2>&1 &

echo $! > "$PID"
echo "✅ webhook started. PID=$(cat "$PID"); LOG=$LOG; PORT=$PORT"
echo "Webhook URL: https://$(hostname)-${PORT}.proxy.runpod.net/hook"
