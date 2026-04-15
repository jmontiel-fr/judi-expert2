#!/bin/bash
set -e

# ─────────────────────────────────────────────────────────
# dev-stop.sh — Arrêt du Site Central en mode développement
# ─────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AWS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$AWS_DIR/docker-compose.dev.yml"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert — Arrêt Site Central (dev)${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""

docker compose -f "$COMPOSE_FILE" down
echo ""

echo -e "${GREEN}  ✔ Site Central arrêté${NC}"
echo ""
echo -e "  ${BLUE}Pour relancer :${NC} ./dev-start.sh"
