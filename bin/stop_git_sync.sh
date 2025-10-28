#!/usr/bin/env bash
PID="/workspace/data/logs/git_sync.pid"
if [ -f "$PID" ]; then
  kill -9 "$(cat "$PID")" 2>/dev/null || true
  rm -f "$PID"
  echo "✅ git-sync stopped"
else
  echo "ℹ️ no git-sync running"
fi
