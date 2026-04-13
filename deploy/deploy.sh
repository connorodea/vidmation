#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/var/www/aividio"
RELEASES_DIR="/var/www/aividio-releases"
MAX_RELEASES=5
SERVICE_API="aividio-api"
SERVICE_WEB="aividio-web"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RELEASE_TAG="${TIMESTAMP}"

echo "=== AIVidio Deploy ==="
echo "Release: $RELEASE_TAG"
cd "$APP_DIR"

# --- Snapshot current release before overwriting ---
echo ""
echo "=== Creating release snapshot ==="
mkdir -p "$RELEASES_DIR"

# Only snapshot if there's a running version to preserve
if [[ -f "$APP_DIR/pyproject.toml" ]]; then
    SNAPSHOT_DIR="$RELEASES_DIR/$RELEASE_TAG"
    echo "Snapshotting current state → $SNAPSHOT_DIR"
    rsync -a \
        --exclude='.venv' \
        --exclude='node_modules' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='data/' \
        --exclude='output/' \
        --exclude='logs/' \
        --exclude='.env' \
        "$APP_DIR/" "$SNAPSHOT_DIR/"

    # Record git commit hash if available
    if command -v git &>/dev/null && [[ -d "$APP_DIR/.git" ]]; then
        git -C "$APP_DIR" rev-parse HEAD > "$SNAPSHOT_DIR/.release-commit" 2>/dev/null || true
    fi

    # Write release metadata
    cat > "$SNAPSHOT_DIR/.release-meta" <<RELEASE_EOF
release=$RELEASE_TAG
timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
commit=$(git -C "$APP_DIR" rev-parse HEAD 2>/dev/null || echo "unknown")
RELEASE_EOF

    echo "Snapshot saved."

    # Prune old releases (keep latest $MAX_RELEASES)
    RELEASE_COUNT=$(ls -1d "$RELEASES_DIR"/*/ 2>/dev/null | wc -l)
    if [[ "$RELEASE_COUNT" -gt "$MAX_RELEASES" ]]; then
        PRUNE_COUNT=$((RELEASE_COUNT - MAX_RELEASES))
        echo "Pruning $PRUNE_COUNT old release(s)..."
        ls -1d "$RELEASES_DIR"/*/ | head -n "$PRUNE_COUNT" | xargs rm -rf
    fi
else
    echo "No existing deployment found — skipping snapshot."
fi

# --- Build ---
echo ""
echo "=== Installing dependencies ==="
.venv/bin/pip install -e . --quiet

echo ""
echo "=== Building frontend ==="
cd "$APP_DIR/frontend"
npm install --silent
npm run build
cd "$APP_DIR"

# Create required runtime directories
mkdir -p data output assets/fonts assets/music channel_profiles logs

# --- Restart services ---
echo ""
echo "=== Restarting services ==="
systemctl stop "$SERVICE_API" || true
systemctl stop "$SERVICE_WEB" || true
sleep 2
systemctl start "$SERVICE_API"
systemctl start "$SERVICE_WEB"

# Wait for startup
sleep 5

# --- Status & health check ---
echo ""
echo "=== Service Status ==="
systemctl status "$SERVICE_API" --no-pager -l
echo ""
systemctl status "$SERVICE_WEB" --no-pager -l
echo ""

API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/health 2>/dev/null || echo "000")
WEB_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3002/ 2>/dev/null || echo "000")
echo "API /health: HTTP $API_STATUS"
echo "Web /: HTTP $WEB_STATUS"

if [[ "$API_STATUS" == "200" && "$WEB_STATUS" == "200" ]]; then
    echo ""
    echo "Deploy complete — aividio.com is live."
    echo "Release: $RELEASE_TAG"
    echo ""
    echo "To rollback: bash /var/www/aividio/deploy/rollback.sh"
else
    echo ""
    echo "WARNING: Health checks failed!"
    echo "  API: $API_STATUS  Web: $WEB_STATUS"
    echo ""
    echo "Auto-rolling back to previous release..."
    bash "$APP_DIR/deploy/rollback.sh" --auto 2>&1 || true
    echo ""
    echo "Check logs:"
    echo "  journalctl -u aividio-api -n 50"
    echo "  journalctl -u aividio-web -n 50"
    exit 1
fi
