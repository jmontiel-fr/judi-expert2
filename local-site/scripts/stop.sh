#!/bin/bash
set -e

# ─────────────────────────────────────────────────────────
# stop.sh — Stop all Judi-Expert local containers
# Uses docker-compose to stop all services.
# Exigences : 30.1
# ─────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert — Arrêt des conteneurs${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Arrêt de tous les services...${NC}"
docker compose -f "$PROJECT_DIR/docker-compose.yml" down
echo ""

echo -e "${GREEN}  ✔ Tous les conteneurs sont arrêtés${NC}"
