#!/bin/bash
set -e

# ─────────────────────────────────────────────────────────
# dev-start.sh — Lancement du Site Central en mode développement
# Démarre les 3 conteneurs (PostgreSQL, Backend, Frontend)
# via Docker Compose, avec nettoyage des ports et rebuild.
#
# URLs :
#   - Frontend  : http://localhost:3001
#   - Backend   : http://localhost:8002/docs
#   - PostgreSQL: localhost:5433
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

# Ports used by this stack
PORTS=(3001 8002 5433)

# ── Fonction : stopper tout conteneur Docker occupant un port ──
free_port() {
  local port=$1
  local cid
  cid=$(docker ps -q --filter "publish=${port}" 2>/dev/null | head -1)
  if [ -n "$cid" ]; then
    local cname
    cname=$(docker inspect --format '{{.Name}}' "$cid" 2>/dev/null | sed 's|^/||')
    echo -e "${YELLOW}  ⚠ Port $port occupé par conteneur $cname — arrêt...${NC}"
    docker stop "$cid" > /dev/null 2>&1 || true
    docker rm "$cid" > /dev/null 2>&1 || true
    sleep 1
    return
  fi
  local pid
  pid=$(netstat -ano 2>/dev/null | grep ":${port}.*LISTENING" | awk '{print $NF}' | head -1)
  if [ -z "$pid" ] || [ "$pid" = "0" ]; then
    return
  fi
  local pname
  pname=$(tasklist //FI "PID eq $pid" //FO CSV //NH 2>/dev/null | head -1 | cut -d'"' -f2)
  case "$pname" in
    com.docker.*|docker.exe|Docker\ Desktop.exe|dockerd.exe)
      return
      ;;
  esac
  echo -e "${YELLOW}  ⚠ Port $port occupé par $pname (PID $pid), arrêt...${NC}"
  taskkill //F //PID "$pid" > /dev/null 2>&1 || true
  sleep 1
}

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert — Site Central (dev)${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""

# ── Vérification & démarrage Docker ───────────────────
echo -e "${YELLOW}[1/4]${NC} Vérification de Docker..."
if ! docker info > /dev/null 2>&1; then
  echo -e "${YELLOW}  ⚠ Docker n'est pas lancé — démarrage automatique...${NC}"
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
    echo -e "${RED}  ✘ Docker Desktop introuvable. Démarrez-le manuellement.${NC}"
    exit 1
  fi
  "$DOCKER_DESKTOP" &
  disown
  MAX_DOCKER_WAIT=120
  for ((i=1; i<=MAX_DOCKER_WAIT; i++)); do
    if docker info > /dev/null 2>&1; then
      echo -e "${GREEN}  ✔ Docker est prêt${NC}"
      break
    fi
    if [ "$i" -eq "$MAX_DOCKER_WAIT" ]; then
      echo -e "${RED}  ✘ Docker n'a pas démarré après ${MAX_DOCKER_WAIT}s${NC}"
      exit 1
    fi
    sleep 1
  done
else
  echo -e "${GREEN}  ✔ Docker est disponible${NC}"
fi
echo ""

# ── Arrêt du stack existant ───────────────────────────
echo -e "${YELLOW}[2/4]${NC} Arrêt des services existants..."
docker compose -f "$COMPOSE_FILE" down --remove-orphans || true
echo -e "${GREEN}  ✔ Conteneurs arrêtés${NC}"
echo ""

# ── Libération des ports ──────────────────────────────
echo -e "${YELLOW}[3/4]${NC} Vérification des ports..."
for port in "${PORTS[@]}"; do
  free_port "$port"
done
echo -e "${GREEN}  ✔ Ports libres${NC}"
echo ""

# ── Build & démarrage ─────────────────────────────────
echo -e "${YELLOW}[4/4]${NC} Build et démarrage..."
docker compose -f "$COMPOSE_FILE" up -d --build
echo ""

# ── Attente de disponibilité ──────────────────────────
echo -e "${YELLOW}Attente du backend...${NC}"
MAX_ATTEMPTS=30
for ((i=1; i<=MAX_ATTEMPTS; i++)); do
  if curl -sf http://localhost:8002/docs > /dev/null 2>&1; then
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
echo -e "  Backend   : ${GREEN}http://localhost:8002/docs${NC}"
echo -e "  PostgreSQL: ${GREEN}localhost:5433${NC}"
echo ""
echo -e "  ${YELLOW}Arrêter :${NC} docker compose -f central-site/docker-compose.dev.yml down"
echo -e "  ${YELLOW}Logs    :${NC} docker compose -f central-site/docker-compose.dev.yml logs -f"
