#!/bin/bash
set -e
# Usage : bash scripts-dev/dev-local-restart.sh [--build] [--pull-llm]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE="$ROOT_DIR/local-site/docker-compose.yml"
source "$SCRIPT_DIR/_common.sh"
parse_args "dev-local-restart.sh" \
  "Redémarrer l'Application Locale (arrêt + libération ports + démarrage)" \
  "yes" "yes" "$@"

PORTS=(3000 8000 8001 11434 6333)

# Determine step count based on --pull-llm flag
if [ "$PULL_LLM" = "yes" ]; then
  TOTAL_STEPS=5
else
  TOTAL_STEPS=4
fi

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert Local — Redémarrage${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}[1/${TOTAL_STEPS}] Docker...${NC}"
ensure_docker
echo ""

STEP=2

# ── LLM model check/download BEFORE stopping containers ──
if [ "$PULL_LLM" = "yes" ]; then
  echo -e "${YELLOW}[${STEP}/${TOTAL_STEPS}] Vérification et mise à jour du modèle LLM...${NC}"
  if docker ps --format '{{.Names}}' | grep -q "^${LLM_CONTAINER}$"; then
    # Container is running — pull model before rebuild
    if ! ensure_llm_model; then
      echo -e "${RED}  ✘ Échec de la vérification/téléchargement du modèle LLM.${NC}"
      echo -e "${RED}    Redémarrage interrompu.${NC}"
      exit 1
    fi
  else
    echo -e "${YELLOW}  ℹ Conteneur $LLM_CONTAINER non démarré — le modèle sera vérifié après démarrage.${NC}"
  fi
  echo ""
  STEP=$((STEP + 1))
fi

echo -e "${YELLOW}[${STEP}/${TOTAL_STEPS}] Arrêt...${NC}"
docker compose -f "$COMPOSE" down --remove-orphans || true
echo -e "${GREEN}  ✔ Arrêté${NC}"
echo ""
STEP=$((STEP + 1))

echo -e "${YELLOW}[${STEP}/${TOTAL_STEPS}] Libération des ports...${NC}"
free_ports "${PORTS[@]}"
echo -e "${GREEN}  ✔ Ports libres${NC}"
echo ""
STEP=$((STEP + 1))

echo -e "${YELLOW}[${STEP}/${TOTAL_STEPS}] Démarrage${BUILD_FLAG:+ + build}${NO_CACHE:+ (no-cache)}...${NC}"
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

# ── If LLM container was not running before, pull model after restart ──
if [ "$PULL_LLM" = "yes" ]; then
  if ! docker exec "$LLM_CONTAINER" ollama list 2>/dev/null | grep -q "qwen2.5"; then
    echo -e "${YELLOW}[LLM] Modèle non trouvé — téléchargement post-démarrage...${NC}"
    if ! ensure_llm_model; then
      echo -e "${RED}  ✘ Échec de la vérification/téléchargement du modèle LLM.${NC}"
      echo -e "${RED}    Redémarrage interrompu.${NC}"
      exit 1
    fi
    echo ""
  fi
fi

echo -e "${GREEN}  ✔ Application Locale redémarrée${NC}"
echo -e "  Frontend : ${GREEN}http://localhost:3000${NC}"
echo -e "  Backend  : ${GREEN}http://localhost:8000${NC}"
echo -e "  OCR      : ${GREEN}http://localhost:8001${NC}"
echo -e "  LLM      : ${GREEN}http://localhost:11434${NC}"
echo -e "  RAG      : ${GREEN}http://localhost:6333${NC}"
