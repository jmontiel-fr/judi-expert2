#!/bin/bash
set -e

# ─────────────────────────────────────────────────────────
# stop.sh — Stop all Judi-Expert local containers
# Exigences : 30.1
# ─────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert Local — Arrêt${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Arrêt de tous les services...${NC}"
docker compose -f "$PROJECT_DIR/docker-compose.yml" down --remove-orphans || true
echo ""

echo -e "${GREEN}  ✔ Tous les conteneurs sont arrêtés${NC}"
