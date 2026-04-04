#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/var/www/vidmation"
SERVICE_WEB="vidmation-web"
SERVICE_WORKER="vidmation-worker"

echo "=== VIDMATION Deploy ==="
cd "$APP_DIR"

# Detect package manager
if [ -f "pnpm-lock.yaml" ]; then
    echo "ERROR: This is a Python project, not Node.js"
    exit 1
fi

# Install Python dependencies
echo "Installing dependencies..."
pip install -e . 2>/dev/null || pip3 install -e .

# Run database migrations if alembic is configured
if [ -f "alembic.ini" ]; then
    echo "Running database migrations..."
    alembic upgrade head 2>/dev/null || echo "Alembic migration skipped (may need manual setup)"
fi

# Create required directories
mkdir -p data output assets/fonts assets/music channel_profiles

# Restart services
echo "Restarting services..."
sudo systemctl restart "$SERVICE_WEB" || echo "Warning: $SERVICE_WEB not found"
sudo systemctl restart "$SERVICE_WORKER" || echo "Warning: $SERVICE_WORKER not found"

# Show status
echo ""
echo "=== Service Status ==="
systemctl status "$SERVICE_WEB" --no-pager -l 2>/dev/null || true
echo ""
systemctl status "$SERVICE_WORKER" --no-pager -l 2>/dev/null || true
echo ""
echo "Deploy complete!"
