#!/usr/bin/env bash
PID="/workspace/data/logs/notion_watcher.pid"
LOG="/workspace/data/logs/notion_watcher.log"
if [ -f "$PID" ] && ps -p "$(cat "$PID")" >/dev/null 2>&1; then
  echo "✅ notion-watcher running, PID=$(cat "$PID")"
  echo "== LAST 30 LINES =="
  tail -n 30 "$LOG" 2>/dev/null || true
else
  echo "notion-watcher not running"
fi
