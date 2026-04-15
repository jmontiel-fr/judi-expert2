#!/bin/bash
set -e

# ─────────────────────────────────────────────────────────
# dev-start.sh — Lancement du Site Central en mode développement
# Démarre les 3 conteneurs (PostgreSQL, Backend, Frontend)
# via Docker Compose, avec vérification de Docker Desktop.
#
# URLs :
#   - Frontend  : http://localhost:3001
#   - Backend   : http://localhost:8001/docs
#   - PostgreSQL: localhost:5433
# ─────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AWS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$AWS_DIR/.." && pwd)"
COMPOSE_FILE="$AWS_DIR/docker-compose.dev.yml"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert — Site Central (dev)${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""

# ── Vérification & démarrage Docker ───────────────────
echo -e "${YELLOW}[1/3]${NC} Vérification de Docker..."
if ! docker info > /dev/null 2>&1; then
  echo -e "${YELLOW}  ⚠ Docker n'est pas lancé — démarrage automatique...${NC}"

  DOCKER_DESKTOP="/c/Program Files/Docker/Docker/Docker Desktop.exe"
  if [ ! -f "$DOCKER_DESKTOP" ]; then
    echo -e "${RED}  ✘ Docker Desktop introuvable à : ${DOCKER_DESKTOP}${NC}"
    echo -e "  Installez Docker Desktop ou démarrez-le manuellement."
    exit 1
  fi

  "$DOCKER_DESKTOP" &
  disown

  # Attente que le daemon Docker soit prêt (max ~60s)
  MAX_DOCKER_WAIT=60
  echo -e "  Attente du daemon Docker..."
  for ((i=1; i<=MAX_DOCKER_WAIT; i++)); do
    if docker info > /dev/null 2>&1; then
      echo -e "${GREEN}  ✔ Docker est prêt${NC}"
      break
    fi
    if [ "$i" -eq "$MAX_DOCKER_WAIT" ]; then
      echo -e "${RED}  ✘ Docker n'a pas démarré après ${MAX_DOCKER_WAIT}s${NC}"
      echo -e "  Démarrez Docker Desktop manuellement puis relancez ce script."
      exit 1
    fi
    sleep 1
  done
else
  echo -e "${GREEN}  ✔ Docker est disponible${NC}"
fi
echo ""

# ── Build & démarrage ─────────────────────────────────
echo -e "${YELLOW}[2/3]${NC} Build et démarrage des conteneurs..."
docker compose -f "$COMPOSE_FILE" up -d --build
echo ""

# ── Attente de disponibilité ──────────────────────────
echo -e "${YELLOW}[3/3]${NC} Attente du backend..."
MAX_ATTEMPTS=30
for ((i=1; i<=MAX_ATTEMPTS; i++)); do
  if curl -sf http://localhost:8001/docs > /dev/null 2>&1; then
    echo -e "${GREEN}  ✔ Backend prêt${NC}"
    break
  fi
  if [ "$i" -eq "$MAX_ATTEMPTS" ]; then
    echo -e "${YELLOW}  ⚠ Le backend n'a pas répondu après ${MAX_ATTEMPTS}s — vérifiez les logs :${NC}"
    echo -e "    docker compose -f central-site/docker-compose.dev.yml logs backend"
    break
  fi
  sleep 1
done
echo ""

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✔ Site Central démarré${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""
echo -e "  Frontend  : ${GREEN}http://localhost:3001${NC}"
echo -e "  Backend   : ${GREEN}http://localhost:8001/docs${NC}"
echo -e "  PostgreSQL: ${GREEN}localhost:5433${NC}"
echo ""
echo -e "  ${YELLOW}Arrêter :${NC} ./dev-stop.sh"
echo -e "  ${YELLOW}Logs    :${NC} docker compose -f central-site/docker-compose.dev.yml logs -f"
