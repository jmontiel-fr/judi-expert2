#!/bin/bash
set -e
# Usage : bash scripts-dev/dev-local-start.sh [--build] [--pull-llm]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE="$ROOT_DIR/local-site/docker-compose.yml"
source "$SCRIPT_DIR/_common.sh"
parse_args "dev-local-start.sh" \
  "Démarrer l'Application Locale (5 conteneurs : frontend, backend, OCR, LLM, RAG)" \
  "yes" "yes" "$@"

PORTS=(3000 8000 8001 11434 6333)

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert Local — Démarrage${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}[1/3] Docker...${NC}"
ensure_docker
echo ""
echo -e "${YELLOW}[2/3] Libération des ports...${NC}"
free_ports "${PORTS[@]}"
echo -e "${GREEN}  ✔ Ports libres${NC}"
echo ""
echo -e "${YELLOW}[3/3] Démarrage${BUILD_FLAG:+ + build}${NO_CACHE:+ (no-cache)}...${NC}"
GPU_COMPOSE=""
if command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null; then
  echo -e "${GREEN}  ✔ GPU NVIDIA détecté — accélération GPU activée${NC}"
  GPU_COMPOSE="-f $ROOT_DIR/local-site/docker-compose.gpu.yml"
else
  echo -e "${YELLOW}  ℹ Pas de GPU NVIDIA détecté — mode CPU${NC}"
fi
if [ "$NO_CACHE" = "yes" ]; then
  docker compose -f "$COMPOSE" $GPU_COMPOSE build --no-cache
fi
docker compose -f "$COMPOSE" $GPU_COMPOSE up -d $BUILD_FLAG
echo ""

if [ "$PULL_LLM" = "yes" ]; then
  echo -e "${YELLOW}[LLM] Vérification et mise à jour du modèle LLM...${NC}"
  if ! ensure_llm_model; then
    echo -e "${RED}  ✘ Échec de la vérification/téléchargement du modèle LLM.${NC}"
    echo -e "${RED}    Démarrage interrompu.${NC}"
    exit 1
  fi
  echo ""
fi

echo -e "${GREEN}  ✔ Application Locale démarrée${NC}"
echo -e "  Frontend : ${GREEN}http://localhost:3000${NC}"
echo -e "  Backend  : ${GREEN}http://localhost:8000${NC}"
echo -e "  OCR      : ${GREEN}http://localhost:8001${NC}"
echo -e "  LLM      : ${GREEN}http://localhost:11434${NC}"
echo -e "  RAG      : ${GREEN}http://localhost:6333${NC}"
