#!/bin/bash
# Usage : bash scripts-dev/dev-central-status.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_common.sh"
parse_args "dev-central-status.sh" \
  "Afficher le statut de tous les composants du Site Central" \
  "" "" "$@"

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert Central — Statut${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""

# Docker
if docker info > /dev/null 2>&1; then
  echo -e "  ${GREEN}✔${NC} Docker Desktop — ${GREEN}running${NC}"
else
  echo -e "  ${RED}✘${NC} Docker Desktop — ${RED}arrêté${NC}"
  echo ""
  echo -e "  Lancez : bash scripts-dev/dev-central-start.sh"
  exit 1
fi
echo ""

# Conteneurs
echo -e "${BLUE}Conteneurs :${NC}"
ERRORS=0
check_container "judi-central-db"       "PostgreSQL (:5433)" || ERRORS=$((ERRORS+1))
check_container "judi-central-backend"  "Backend    (FastAPI :8002)" || ERRORS=$((ERRORS+1))
check_container "judi-central-frontend" "Frontend   (Next.js :3001)" || ERRORS=$((ERRORS+1))
echo ""

# Connectivité backend
echo -e "${BLUE}API Backend :${NC}"
if curl -sf http://localhost:8002/docs > /dev/null 2>&1; then
  echo -e "  ${GREEN}✔${NC} http://localhost:8002/docs — ${GREEN}accessible${NC}"
else
  echo -e "  ${RED}✘${NC} http://localhost:8002/docs — ${RED}inaccessible${NC}"
  ERRORS=$((ERRORS+1))
fi

if curl -sf http://localhost:8002/api/tickets/price > /dev/null 2>&1; then
  PRICE=$(curl -s http://localhost:8002/api/tickets/price 2>/dev/null)
  echo -e "  ${GREEN}✔${NC} API tickets/price — $PRICE"
else
  echo -e "  ${RED}✘${NC} API tickets/price — ${RED}inaccessible${NC}"
  ERRORS=$((ERRORS+1))
fi
echo ""

# Résumé
if [ "$ERRORS" -eq 0 ]; then
  echo -e "${GREEN}══════════════════════════════════════════════${NC}"
  echo -e "${GREEN}  ✔ Tous les composants sont prêts${NC}"
  echo -e "${GREEN}══════════════════════════════════════════════${NC}"
else
  echo -e "${RED}══════════════════════════════════════════════${NC}"
  echo -e "${RED}  ✘ $ERRORS composant(s) non prêt(s)${NC}"
  echo -e "${RED}══════════════════════════════════════════════${NC}"
fi
