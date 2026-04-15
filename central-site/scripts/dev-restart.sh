#!/bin/bash
set -e

# ─────────────────────────────────────────────────────────
# dev-restart.sh — Redémarrage léger du Site Central (dev)
# Usage :
#   ./dev-restart.sh           # Rebuild backend + frontend
#   ./dev-restart.sh front     # Rebuild frontend uniquement
#   ./dev-restart.sh back      # Rebuild backend uniquement
# La base PostgreSQL reste en place (pas de down/up).
# ─────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AWS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$AWS_DIR/docker-compose.dev.yml"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

TARGET="${1:-all}"

case "$TARGET" in
  front|frontend)
    SERVICES="frontend"
    LABEL="frontend"
    ;;
  back|backend)
    SERVICES="backend"
    LABEL="backend"
    ;;
  all|"")
    SERVICES="backend frontend"
    LABEL="backend + frontend"
    ;;
  *)
    echo -e "${RED}Usage : $0 [front|back]${NC}"
    echo -e "  (sans argument = rebuild les deux)"
    exit 1
    ;;
esac

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert — Restart léger ($LABEL)${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""

# ── Rebuild + restart ─────────────────────────────────
echo -e "${YELLOW}[1/2]${NC} Rebuild $LABEL..."
docker compose -f "$COMPOSE_FILE" up -d --build --no-deps $SERVICES
echo ""

# ── Attente du backend (si concerné) ──────────────────
if [[ "$SERVICES" == *"backend"* ]]; then
  echo -e "${YELLOW}[2/2]${NC} Attente du backend..."
  MAX_ATTEMPTS=30
  for ((i=1; i<=MAX_ATTEMPTS; i++)); do
    if curl -sf http://localhost:8001/docs > /dev/null 2>&1; then
      echo -e "${GREEN}  ✔ Backend prêt${NC}"
      break
    fi
    if [ "$i" -eq "$MAX_ATTEMPTS" ]; then
      echo -e "${YELLOW}  ⚠ Le backend n'a pas répondu après ${MAX_ATTEMPTS}s${NC}"
      echo -e "    docker compose -f central-site/docker-compose.dev.yml logs backend"
      break
    fi
    sleep 1
  done
else
  echo -e "${YELLOW}[2/2]${NC} Frontend uniquement — pas d'attente backend"
fi
echo ""

echo -e "${GREEN}  ✔ Restart terminé ($LABEL)${NC}"
echo -e "  Frontend : ${GREEN}http://localhost:3001${NC}"
echo -e "  Backend  : ${GREEN}http://localhost:8001/docs${NC}"
