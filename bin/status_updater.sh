#!/usr/bin/env bash
set -euo pipefail
PID="/workspace/data/logs/updater.pid"
LOG="/workspace/data/logs/updater.log"
if [ -f "$PID" ] && ps -p "$(cat $PID)" >/dev/null 2>&1; then
  echo "✅ updater running, PID=$(cat $PID)"
else
  echo "❌ updater not running"
fi
echo "== LAST 30 LOG LINES =="
tail -n 30 "$LOG" 2>/dev/null || echo "no log"
