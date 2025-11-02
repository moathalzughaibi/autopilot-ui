#!/usr/bin/env bash
PID="/workspace/data/logs/webhook_pull.pid"
[ -f "$PID" ] && kill -9 "$(cat "$PID")" >/dev/null 2>&1 || true
rm -f "$PID"
echo "✅ webhook stopped"
