#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/var/www/aividio"
RELEASES_DIR="/var/www/aividio-releases"
SERVICE_API="aividio-api"
SERVICE_WEB="aividio-web"
AUTO_MODE="${1:-}"

echo "=== AIVidio Rollback ==="

# List available releases
if [[ ! -d "$RELEASES_DIR" ]] || [[ -z "$(ls -A "$RELEASES_DIR" 2>/dev/null)" ]]; then
    echo "ERROR: No releases found in $RELEASES_DIR"
    echo "Nothing to rollback to."
    exit 1
fi

echo ""
echo "Available releases:"
echo "---"
RELEASES=($(ls -1d "$RELEASES_DIR"/*/ 2>/dev/null | sort -r))
for i in "${!RELEASES[@]}"; do
    REL_DIR="${RELEASES[$i]}"
    REL_NAME=$(basename "$REL_DIR")
    META=""
    if [[ -f "$REL_DIR/.release-meta" ]]; then
        COMMIT=$(grep "^commit=" "$REL_DIR/.release-meta" | cut -d= -f2 | head -c 8)
        META=" (commit: $COMMIT)"
    fi
    if [[ $i -eq 0 ]]; then
        echo "  [$i] $REL_NAME$META  ← most recent (pre-current deploy)"
    else
        echo "  [$i] $REL_NAME$META"
    fi
done
echo "---"

# In auto mode (called from deploy.sh on failure), use the most recent release
if [[ "$AUTO_MODE" == "--auto" ]]; then
    SELECTED=0
    echo "Auto-rollback: selecting release [0]"
else
    echo ""
    read -rp "Select release to restore [0]: " SELECTED
    SELECTED="${SELECTED:-0}"
fi

if [[ "$SELECTED" -ge "${#RELEASES[@]}" ]]; then
    echo "ERROR: Invalid selection."
    exit 1
fi

TARGET="${RELEASES[$SELECTED]}"
TARGET_NAME=$(basename "$TARGET")

echo ""
echo "Restoring release: $TARGET_NAME"
echo "Target: $APP_DIR"

# Restore files (preserve .env, data, output, logs, .venv, node_modules)
rsync -a --delete \
    --exclude='.env' \
    --exclude='data/' \
    --exclude='output/' \
    --exclude='logs/' \
    --exclude='.venv/' \
    --exclude='node_modules/' \
    "$TARGET/" "$APP_DIR/"

echo "Files restored."

# Reinstall deps and rebuild
echo ""
echo "Reinstalling dependencies..."
cd "$APP_DIR"
.venv/bin/pip install -e . --quiet

echo "Rebuilding frontend..."
cd "$APP_DIR/frontend"
npm install --silent
npm run build
cd "$APP_DIR"

# Restart services
echo ""
echo "Restarting services..."
systemctl stop "$SERVICE_API" || true
systemctl stop "$SERVICE_WEB" || true
sleep 2
systemctl start "$SERVICE_API"
systemctl start "$SERVICE_WEB"
sleep 5

# Health check
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/health 2>/dev/null || echo "000")
WEB_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3002/ 2>/dev/null || echo "000")
echo ""
echo "API /health: HTTP $API_STATUS"
echo "Web /: HTTP $WEB_STATUS"

if [[ "$API_STATUS" == "200" && "$WEB_STATUS" == "200" ]]; then
    echo ""
    echo "Rollback complete — aividio.com restored to release $TARGET_NAME"
else
    echo ""
    echo "WARNING: Health checks failed after rollback."
    echo "  journalctl -u aividio-api -n 50"
    echo "  journalctl -u aividio-web -n 50"
    exit 1
fi
