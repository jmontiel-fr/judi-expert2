#!/bin/bash
set -e

# ─────────────────────────────────────────────────────────
# build-and-deploy-client.sh — Build et démarrage du Site Client
# Usage : bash scripts-dev/build-and-deploy-client.sh [--no-cache] [--pull-llm]
# ─────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE="$ROOT_DIR/client-site/docker-compose.yml"
source "$SCRIPT_DIR/_common.sh"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Parse arguments
NO_CACHE=""
PULL_LLM=""
for arg in "$@"; do
  case "$arg" in
    --no-cache) NO_CACHE="yes" ;;
    --pull-llm) PULL_LLM="yes" ;;
    --help|-h)
      echo "Usage: bash scripts-dev/build-and-deploy-client.sh [--no-cache] [--pull-llm]"
      echo ""
      echo "Options:"
      echo "  --no-cache   Rebuild les images sans cache Docker"
      echo "  --pull-llm   Télécharger/mettre à jour le modèle LLM (Mistral 7B)"
      echo ""
      exit 0
      ;;
  esac
done

PORTS=(3000 8000 8001 11434 6333)

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert — Build & Deploy Client${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""

# ── Étape 1 : Prérequis ───────────────────────────────
echo -e "${YELLOW}[1/5]${NC} Vérification Docker..."
ensure_docker
echo ""

# ── Étape 2 : Libération des ports ────────────────────
echo -e "${YELLOW}[2/5]${NC} Libération des ports (${PORTS[*]})..."
free_ports "${PORTS[@]}"
echo -e "${GREEN}  ✔ Ports libres${NC}"
echo ""

# ── Étape 3 : Arrêt des conteneurs existants ──────────
echo -e "${YELLOW}[3/5]${NC} Arrêt des conteneurs existants..."
docker compose -f "$COMPOSE" down --remove-orphans 2>/dev/null || true
echo -e "${GREEN}  ✔ Conteneurs arrêtés${NC}"
echo ""

# ── Étape 4 : Build + démarrage ───────────────────────
echo -e "${YELLOW}[4/5]${NC} Build et démarrage des conteneurs..."

# Détection GPU
GPU_COMPOSE=""
if command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null; then
  echo -e "${GREEN}  ✔ GPU NVIDIA détecté — accélération GPU activée${NC}"
  GPU_COMPOSE="-f $ROOT_DIR/client-site/docker-compose.gpu.yml"
else
  echo -e "${YELLOW}  ℹ Pas de GPU NVIDIA — mode CPU${NC}"
fi

if [ "$NO_CACHE" = "yes" ]; then
  echo -e "  ${YELLOW}Build sans cache...${NC}"
  docker compose -f "$COMPOSE" $GPU_COMPOSE build --no-cache
fi

docker compose -f "$COMPOSE" $GPU_COMPOSE up -d --build
echo -e "${GREEN}  ✔ Conteneurs démarrés${NC}"
echo ""

# ── Étape 5 : Modèle LLM ──────────────────────────────
if [ "$PULL_LLM" = "yes" ]; then
  echo -e "${YELLOW}[5/5]${NC} Téléchargement du modèle LLM..."
  if ! ensure_llm_model; then
    echo -e "${RED}  ✘ Échec du téléchargement du modèle LLM${NC}"
    exit 1
  fi
  echo -e "${GREEN}  ✔ Modèle LLM prêt${NC}"
else
  echo -e "${YELLOW}[5/5]${NC} Modèle LLM — ${YELLOW}SKIP${NC} (ajouter --pull-llm si nécessaire)"
fi
echo ""

# ── Résumé ─────────────────────────────────────────────
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✔ Site Client déployé${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""
echo -e "  Frontend : ${GREEN}http://localhost:3000${NC}"
echo -e "  Backend  : ${GREEN}http://localhost:8000${NC}"
echo -e "  OCR      : ${GREEN}http://localhost:8001${NC}"
echo -e "  LLM      : ${GREEN}http://localhost:11434${NC}"
echo -e "  RAG      : ${GREEN}http://localhost:6333${NC}"
echo ""
