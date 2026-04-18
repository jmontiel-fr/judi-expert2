#!/bin/bash
set -e

# ─────────────────────────────────────────────────────────
# start.sh — Build and start all Judi-Expert local containers
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

# Ports used by this stack
PORTS=(3000 8000 8001 11434 6333)

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
      return ;;
  esac
  echo -e "${YELLOW}  ⚠ Port $port occupé par $pname (PID $pid), arrêt...${NC}"
  taskkill //F //PID "$pid" > /dev/null 2>&1 || true
  sleep 1
}

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert Local — Démarrage${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""

# ── Vérification de Docker Desktop ────────────────────────
if ! docker info > /dev/null 2>&1; then
  echo -e "${YELLOW}Docker Desktop n'est pas démarré. Lancement en cours...${NC}"
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
    echo -e "${RED}  ✘ Docker Desktop introuvable. Veuillez le démarrer manuellement.${NC}"
    exit 1
  fi
  "$DOCKER_DESKTOP" &
  echo -e "${YELLOW}Attente du daemon Docker...${NC}"
  MAX_WAIT=120; ELAPSED=0
  while ! docker info > /dev/null 2>&1; do
    if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
      echo -e "${RED}  ✘ Timeout : Docker Desktop n'a pas démarré après ${MAX_WAIT}s.${NC}"
      exit 1
    fi
    sleep 3; ELAPSED=$((ELAPSED + 3))
  done
  echo -e "${GREEN}  ✔ Docker Desktop est prêt (${ELAPSED}s)${NC}"
  echo ""
fi

# ── Libération des ports ──────────────────────────────────
echo -e "${YELLOW}Vérification des ports...${NC}"
for port in "${PORTS[@]}"; do
  free_port "$port"
done
echo -e "${GREEN}  ✔ Ports libres${NC}"
echo ""

# ── Détection GPU NVIDIA ──────────────────────────────────
GPU_COMPOSE=""
if command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null; then
  echo -e "${GREEN}  ✔ GPU NVIDIA détecté — accélération GPU activée${NC}"
  GPU_COMPOSE="-f $PROJECT_DIR/docker-compose.gpu.yml"
else
  echo -e "${YELLOW}  ℹ Pas de GPU NVIDIA détecté — mode CPU${NC}"
fi
echo ""

# ── Build + démarrage ────────────────────────────────────
echo -e "${YELLOW}Build et démarrage de tous les services...${NC}"
docker compose -f "$PROJECT_DIR/docker-compose.yml" $GPU_COMPOSE up -d --build
echo ""

echo -e "${GREEN}  ✔ Tous les conteneurs sont démarrés${NC}"
echo ""

# ── Vérification du modèle LLM ───────────────────────────
LLM_MODEL="${LLM_MODEL:-mistral}"
echo -e "${YELLOW}Vérification du modèle LLM (${LLM_MODEL})...${NC}"
MAX_WAIT=1800  # 30 min max pour le téléchargement initial
ELAPSED=0
while ! docker exec judi-llm ollama list 2>/dev/null | grep -q "${LLM_MODEL%%:*}"; do
  if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
    echo -e "${RED}  ✘ Timeout : le modèle ${LLM_MODEL} n'est pas disponible après ${MAX_WAIT}s.${NC}"
    echo -e "${YELLOW}  Vérifiez les logs : docker logs judi-llm${NC}"
    break
  fi
  if [ "$((ELAPSED % 30))" -eq 0 ] && [ "$ELAPSED" -gt 0 ]; then
    echo -e "${YELLOW}  … téléchargement en cours (${ELAPSED}s)${NC}"
  fi
  sleep 5; ELAPSED=$((ELAPSED + 5))
done
if docker exec judi-llm ollama list 2>/dev/null | grep -q "${LLM_MODEL%%:*}"; then
  echo -e "${GREEN}  ✔ Modèle ${LLM_MODEL} prêt${NC}"
fi
echo ""

echo -e "${BLUE}Services disponibles :${NC}"
echo -e "  • Frontend  : ${GREEN}http://localhost:3000${NC}"
echo -e "  • Backend   : ${GREEN}http://localhost:8000${NC}"
echo -e "  • LLM       : ${GREEN}http://localhost:11434${NC}"
echo -e "  • RAG       : ${GREEN}http://localhost:6333${NC}"
echo -e "  • OCR       : ${GREEN}http://localhost:8001${NC}"
