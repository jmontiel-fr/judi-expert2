#!/bin/bash
set -e

# ─────────────────────────────────────────────────────────
# restart.sh — Full restart of all Judi-Expert local
#              containers (stop + start)
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
echo -e "${BLUE}  Judi-Expert — Redémarrage complet${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Arrêt de tous les services...${NC}"
docker compose -f "$PROJECT_DIR/docker-compose.yml" down
echo -e "${GREEN}  ✔ Conteneurs arrêtés${NC}"
echo ""

echo -e "${YELLOW}Démarrage de tous les services...${NC}"
docker compose -f "$PROJECT_DIR/docker-compose.yml" up -d
echo -e "${GREEN}  ✔ Conteneurs redémarrés${NC}"
echo ""

echo -e "${BLUE}Services disponibles :${NC}"
echo -e "  • Frontend  : ${GREEN}http://localhost:3000${NC}"
echo -e "  • Backend   : ${GREEN}http://localhost:8000${NC}"
echo -e "  • LLM       : ${GREEN}http://localhost:11434${NC}"
echo -e "  • RAG       : ${GREEN}http://localhost:6333${NC}"
echo -e "  • OCR       : ${GREEN}http://localhost:8001${NC}"
