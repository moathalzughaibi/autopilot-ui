#!/usr/bin/env bash
PID="/workspace/data/logs/timeline_watcher.pid"
if [ -f "$PID" ]; then
  kill -9 "$(cat "$PID")" 2>/dev/null || true
  rm -f "$PID"
  echo "✅ timeline-watcher stopped"
else
  echo "timeline-watcher not running"
fi
