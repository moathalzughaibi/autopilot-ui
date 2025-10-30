#!/usr/bin/env bash
PID="/workspace/data/logs/backup_daily.pid"
if [ -f "$PID" ]; then
  kill -9 "$(cat "$PID")" 2>/dev/null || true
  rm -f "$PID"
  echo "✅ backup-daily stopped"
else
  echo "backup-daily not running"
fi
