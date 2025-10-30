#!/usr/bin/env bash
set -euo pipefail
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="/workspace/backups/backup_${STAMP}.tar.gz"
mkdir -p /workspace/backups
tar -czf "$DEST" \
  --ignore-failed-read \
  -C /workspace \
  data/app_dashboard.py \
  data/pages \
  data/autopilot \
  data/templates \
  data/input \
  data/processed
# أبقِ آخر نسختين فقط
ls -1t /workspace/backups/backup_*.tar.gz 2>/dev/null | tail -n +3 | xargs -r rm -f
echo "OK: backup @ $DEST"
