#!/usr/bin/env bash
PID="/workspace/data/logs/git_sync.pid"
LOG="/workspace/data/logs/git_sync.log"
if [ -f "$PID" ] && ps -p "$(cat "$PID")" >/dev/null 2>&1; then
  echo "✅ git-sync running, PID=$(cat "$PID")"
else
  echo "❌ git-sync not running"
fi
echo "== LAST 30 LINES =="
tail -n 30 "$LOG" 2>/dev/null || echo "no log"
