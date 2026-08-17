#!/usr/bin/env bash
# Pull the latest code and restart the VeritasIQ backend service.
#
# Run on the VPS as: sudo bash /opt/veritasiq/deploy/update.sh
# Optionally wired to GitHub Actions (see .github/workflows/deploy-backend.yml).
set -euo pipefail

APP_DIR="${1:-/opt/veritasiq}"
cd "$APP_DIR"

echo ">> pulling latest code"
git pull --ff-only

echo ">> refreshing python deps"
su veritasiq -s /bin/bash -c "'$APP_DIR/backend/venv/bin/pip' install -r '$APP_DIR/backend/requirements.txt'"

echo ">> restarting service"
systemctl restart veritasiq

echo ">> done"
