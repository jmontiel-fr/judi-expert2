#!/bin/bash
# ─────────────────────────────────────────────────────────
# _common.sh — Fonctions partagées par les scripts dev-*
# Sourcé par les autres scripts, ne pas exécuter directement.
# ─────────────────────────────────────────────────────────

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ── Vérifier et démarrer Docker Desktop ───────────────────
ensure_docker() {
  if docker info > /dev/null 2>&1; then
    echo -e "${GREEN}  ✔ Docker est disponible${NC}"
    return
  fi
  echo -e "${YELLOW}  Docker Desktop n'est pas démarré. Lancement...${NC}"
  local DOCKER_DESKTOP=""
  for path in \
    "/c/Program Files/Docker/Docker/Docker Desktop.exe" \
    "/c/Program Files (x86)/Docker/Docker/Docker Desktop.exe" \
    "$LOCALAPPDATA/Docker/Docker Desktop.exe" \
    "$PROGRAMFILES/Docker/Docker/Docker Desktop.exe"; do
    if [ -f "$path" ]; then DOCKER_DESKTOP="$path"; break; fi
  done
  if [ -z "$DOCKER_DESKTOP" ]; then
    echo -e "${RED}  ✘ Docker Desktop introuvable. Démarrez-le manuellement.${NC}"
    exit 1
  fi
  "$DOCKER_DESKTOP" &
  disown 2>/dev/null || true
  local MAX_WAIT=120 ELAPSED=0
  while ! docker info > /dev/null 2>&1; do
    if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
      echo -e "${RED}  ✘ Timeout : Docker n'a pas démarré après ${MAX_WAIT}s.${NC}"
      exit 1
    fi
    sleep 3; ELAPSED=$((ELAPSED + 3))
  done
  echo -e "${GREEN}  ✔ Docker Desktop est prêt (${ELAPSED}s)${NC}"
}

# ── Libérer un port ───────────────────────────────────────
free_port() {
  local port=$1
  local cid
  cid=$(docker ps -q --filter "publish=${port}" 2>/dev/null | head -1)
  if [ -n "$cid" ]; then
    local cname
    cname=$(docker inspect --format '{{.Name}}' "$cid" 2>/dev/null | sed 's|^/||')
    echo -e "${YELLOW}    Port $port ← conteneur $cname — arrêt...${NC}"
    docker stop "$cid" > /dev/null 2>&1 || true
    docker rm "$cid" > /dev/null 2>&1 || true
    sleep 1
    return
  fi
  local pid
  pid=$(netstat -ano 2>/dev/null | grep ":${port}.*LISTENING" | awk '{print $NF}' | head -1)
  if [ -z "$pid" ] || [ "$pid" = "0" ]; then return; fi
  local pname
  pname=$(tasklist //FI "PID eq $pid" //FO CSV //NH 2>/dev/null | head -1 | cut -d'"' -f2)
  case "$pname" in
    com.docker.*|docker.exe|Docker\ Desktop.exe|dockerd.exe) return ;;
  esac
  echo -e "${YELLOW}    Port $port ← $pname (PID $pid) — arrêt...${NC}"
  taskkill //F //PID "$pid" > /dev/null 2>&1 || true
  sleep 1
}

free_ports() {
  for port in "$@"; do free_port "$port"; done
}

# ── Vérifier et télécharger le modèle LLM ────────────────
LLM_MODEL="mistral:7b-instruct-v0.3"
LLM_CONTAINER="judi-llm"

ensure_llm_model() {
  if ! docker ps --format '{{.Names}}' | grep -q "^${LLM_CONTAINER}$"; then
    echo -e "${YELLOW}  ⚠ Conteneur $LLM_CONTAINER non démarré${NC}"
    return
  fi
  local MAX_WAIT=30 ELAPSED=0
  while ! docker exec "$LLM_CONTAINER" curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; do
    if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
      echo -e "${YELLOW}  ⚠ Ollama pas prêt après ${MAX_WAIT}s${NC}"
      return
    fi
    sleep 2; ELAPSED=$((ELAPSED + 2))
  done
  if docker exec "$LLM_CONTAINER" ollama list 2>/dev/null | grep -q "mistral"; then
    echo -e "${GREEN}  ✔ Modèle LLM $LLM_MODEL disponible${NC}"
    return
  fi
  echo -e "${YELLOW}  ⬇ Téléchargement du modèle $LLM_MODEL (~4 Go)...${NC}"
  echo -e "${YELLOW}    Cela peut prendre plusieurs minutes.${NC}"
  docker exec "$LLM_CONTAINER" ollama pull "$LLM_MODEL"
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✔ Modèle $LLM_MODEL téléchargé${NC}"
  else
    echo -e "${RED}  ✘ Erreur téléchargement. Réessayez : docker exec $LLM_CONTAINER ollama pull $LLM_MODEL${NC}"
  fi
}

# ── Vérifier le statut d'un conteneur ─────────────────────
check_container() {
  local name=$1
  local label=$2
  local url=$3  # optionnel : URL de healthcheck

  if ! docker ps --format '{{.Names}}' | grep -q "^${name}$"; then
    echo -e "  ${RED}✘${NC} $label ($name) — ${RED}arrêté${NC}"
    return 1
  fi

  local health
  health=$(docker inspect --format='{{.State.Health.Status}}' "$name" 2>/dev/null || echo "none")

  if [ "$health" = "healthy" ]; then
    echo -e "  ${GREEN}✔${NC} $label ($name) — ${GREEN}healthy${NC}"
  elif [ "$health" = "unhealthy" ]; then
    echo -e "  ${RED}✘${NC} $label ($name) — ${RED}unhealthy${NC}"
    return 1
  elif [ "$health" = "starting" ]; then
    echo -e "  ${YELLOW}…${NC} $label ($name) — ${YELLOW}starting${NC}"
  else
    echo -e "  ${GREEN}✔${NC} $label ($name) — ${GREEN}running${NC}"
  fi
  return 0
}

# ── Vérifier si le modèle LLM est présent ────────────────
check_llm_model() {
  if ! docker ps --format '{{.Names}}' | grep -q "^${LLM_CONTAINER}$"; then
    echo -e "  ${RED}✘${NC} Modèle LLM — ${RED}conteneur arrêté${NC}"
    return 1
  fi
  if docker exec "$LLM_CONTAINER" ollama list 2>/dev/null | grep -q "mistral"; then
    echo -e "  ${GREEN}✔${NC} Modèle LLM $LLM_MODEL — ${GREEN}disponible${NC}"
  else
    echo -e "  ${RED}✘${NC} Modèle LLM $LLM_MODEL — ${RED}non téléchargé${NC}"
    echo -e "      Lancez : bash scripts-dev/dev-local-start.sh --pull-llm"
    return 1
  fi
}

# ── Afficher l'aide et quitter ────────────────────────────
show_help() {
  local script_name="$1"
  local description="$2"
  local has_build="$3"
  local has_pull_llm="$4"
  echo ""
  echo -e "${BLUE}$script_name${NC} — $description"
  echo ""
  echo "Usage : bash scripts-dev/$script_name [options]"
  echo ""
  echo "Options :"
  if [ "$has_build" = "yes" ]; then
    echo "  --build      Reconstruire les images Docker avant de démarrer"
  fi
  if [ "$has_pull_llm" = "yes" ]; then
    echo "  --pull-llm   Vérifier et télécharger le modèle LLM si absent"
  fi
  echo "  --help       Afficher cette aide"
  echo ""
  echo "Actions automatiques :"
  echo "  • Vérifie et démarre Docker Desktop si nécessaire"
  echo "  • Libère les ports occupés (conteneurs Docker ou processus)"
  echo ""
  exit 0
}

# ── Parser les arguments ──────────────────────────────────
parse_args() {
  local script_name="$1"
  local description="$2"
  local has_build="$3"
  local has_pull_llm="$4"
  shift 4
  BUILD_FLAG=""
  PULL_LLM=""
  for arg in "$@"; do
    case "$arg" in
      --help|-h) show_help "$script_name" "$description" "$has_build" "$has_pull_llm" ;;
      --build) BUILD_FLAG="--build" ;;
      --pull-llm) PULL_LLM="yes" ;;
      *) echo "Option inconnue : $arg"; show_help "$script_name" "$description" "$has_build" "$has_pull_llm" ;;
    esac
  done
}
