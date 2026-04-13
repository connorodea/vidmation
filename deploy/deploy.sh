#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/var/www/aividio"
SERVICE_API="aividio-api"
SERVICE_WEB="aividio-web"

echo "=== AIVidio Deploy ==="
cd "$APP_DIR"

# Install/update Python dependencies in venv
echo "Installing Python dependencies..."
.venv/bin/pip install -e . --quiet

# Install/build frontend
echo "Building frontend..."
cd "$APP_DIR/frontend"
npm install --silent
npm run build
cd "$APP_DIR"

# Create required runtime directories
mkdir -p data output assets/fonts assets/music channel_profiles logs

# Restart services
echo "Restarting services..."
systemctl stop "$SERVICE_API" || true
systemctl stop "$SERVICE_WEB" || true
sleep 2
systemctl start "$SERVICE_API"
systemctl start "$SERVICE_WEB"

# Wait for startup
sleep 5

# Show status
echo ""
echo "=== Service Status ==="
systemctl status "$SERVICE_API" --no-pager -l
echo ""
systemctl status "$SERVICE_WEB" --no-pager -l
echo ""

# Quick health check
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/health 2>/dev/null || echo "000")
WEB_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3002/ 2>/dev/null || echo "000")
echo "API /docs: HTTP $API_STATUS"
echo "Web /: HTTP $WEB_STATUS"

if [[ "$API_STATUS" == "200" && "$WEB_STATUS" == "200" ]]; then
    echo ""
    echo "Deploy complete — aividio.com is live."
else
    echo ""
    echo "WARNING: One or more health checks failed. Check logs with:"
    echo "  journalctl -u aividio-api -n 50"
    echo "  journalctl -u aividio-web -n 50"
    exit 1
fi
