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

# ── Vérification de Docker Desktop ────────────────────────
if ! docker info > /dev/null 2>&1; then
  echo -e "${YELLOW}Docker Desktop n'est pas démarré. Lancement en cours...${NC}"

  # Tenter les chemins d'installation courants (Windows)
  DOCKER_DESKTOP=""
  for path in \
    "/c/Program Files/Docker/Docker/Docker Desktop.exe" \
    "/c/Program Files (x86)/Docker/Docker/Docker Desktop.exe" \
    "$LOCALAPPDATA/Docker/Docker Desktop.exe" \
    "$PROGRAMFILES/Docker/Docker/Docker Desktop.exe"; do
    if [ -f "$path" ]; then
      DOCKER_DESKTOP="$path"
      break
    fi
  done

  if [ -z "$DOCKER_DESKTOP" ]; then
    echo -e "${RED}  ✘ Docker Desktop introuvable. Veuillez l'installer ou le démarrer manuellement.${NC}"
    exit 1
  fi

  "$DOCKER_DESKTOP" &

  # Attendre que le daemon Docker soit prêt (max ~120 s)
  echo -e "${YELLOW}Attente du daemon Docker...${NC}"
  MAX_WAIT=120
  ELAPSED=0
  while ! docker info > /dev/null 2>&1; do
    if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
      echo -e "${RED}  ✘ Timeout : Docker Desktop n'a pas démarré après ${MAX_WAIT}s.${NC}"
      exit 1
    fi
    sleep 3
    ELAPSED=$((ELAPSED + 3))
  done
  echo -e "${GREEN}  ✔ Docker Desktop est prêt (${ELAPSED}s)${NC}"
  echo ""
fi

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
