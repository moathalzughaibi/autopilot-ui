#!/usr/bin/env bash
set -euo pipefail
PORT="${1:-8889}"
LOG="/workspace/data/logs/webhook_pull.log"
PID="/workspace/data/logs/webhook_pull.pid"

# إن كان شغّال لا تكرر
if [ -f "$PID" ] && ps -p "$(cat "$PID")" >/dev/null 2>&1; then
  echo "webhook already running, PID=$(cat "$PID")"
  exit 0
fi

export $(grep -v '^#' /workspace/secrets/webhook.env | xargs -d '\n' || true)

# شغّل Uvicorn بالخلفية على 0.0.0.0:PORT
setsid nohup uvicorn webhook_pull:app --host 0.0.0.0 --port "$PORT" \
  --workers 1 >> "$LOG" 2>&1 &

echo $! > "$PID"
echo "✅ webhook started. PID=$(cat "$PID"); LOG=$LOG; PORT=$PORT"
echo "Webhook URL: https://$(hostname)-${PORT}.proxy.runpod.net/hook"
