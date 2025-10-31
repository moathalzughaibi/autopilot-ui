#!/usr/bin/env bash
PID="/workspace/data/logs/notion_watcher.pid"
if [ -f "$PID" ]; then
  kill -9 "$(cat "$PID")" 2>/dev/null || true
  rm -f "$PID"
  echo "✅ notion-watcher stopped"
else
  echo "notion-watcher not running"
fi
