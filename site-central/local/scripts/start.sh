#!/bin/bash
set -e

# ─────────────────────────────────────────────────────────
# start.sh — Start all Judi-Expert local containers
# Uses docker-compose to start all services.
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
echo -e "${BLUE}  Judi-Expert — Démarrage des conteneurs${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Démarrage de tous les services...${NC}"
docker compose -f "$PROJECT_DIR/docker-compose.yml" up -d
echo ""

echo -e "${GREEN}  ✔ Tous les conteneurs sont démarrés${NC}"
echo ""
echo -e "${BLUE}Services disponibles :${NC}"
echo -e "  • Frontend  : ${GREEN}http://localhost:3000${NC}"
echo -e "  • Backend   : ${GREEN}http://localhost:8000${NC}"
echo -e "  • LLM       : ${GREEN}http://localhost:11434${NC}"
echo -e "  • RAG       : ${GREEN}http://localhost:6333${NC}"
echo -e "  • OCR       : ${GREEN}http://localhost:8001${NC}"
