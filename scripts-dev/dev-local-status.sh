#!/bin/bash
# Usage : bash scripts-dev/dev-local-status.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_common.sh"
parse_args "dev-local-status.sh" \
  "Afficher le statut de tous les composants de l'Application Locale" \
  "" "" "$@"

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert Local — Statut${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""

# Docker
if docker info > /dev/null 2>&1; then
  echo -e "  ${GREEN}✔${NC} Docker Desktop — ${GREEN}running${NC}"
else
  echo -e "  ${RED}✘${NC} Docker Desktop — ${RED}arrêté${NC}"
  echo ""
  echo -e "  Lancez : bash scripts-dev/dev-local-start.sh"
  exit 1
fi
echo ""

# Conteneurs
echo -e "${BLUE}Conteneurs :${NC}"
ERRORS=0
check_container "judi-web-frontend" "Frontend (Next.js :3000)" || ERRORS=$((ERRORS+1))
check_container "judi-web-backend"  "Backend  (FastAPI :8000)" || ERRORS=$((ERRORS+1))
check_container "judi-ocr"          "OCR      (Tesseract :8001)" || ERRORS=$((ERRORS+1))
check_container "judi-llm"          "LLM      (Ollama :11434)" || ERRORS=$((ERRORS+1))
check_container "judi-rag"          "RAG      (Qdrant :6333)" || ERRORS=$((ERRORS+1))
echo ""

# Modèle LLM
echo -e "${BLUE}Modèle LLM :${NC}"
check_llm_model || ERRORS=$((ERRORS+1))
echo ""

# GPU
echo -e "${BLUE}Accélération GPU :${NC}"
if command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null; then
  GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
  echo -e "  ${GREEN}✔ GPU NVIDIA détecté — ${GPU_NAME}${NC}"
else
  echo -e "  ${YELLOW}ℹ Mode CPU (pas de GPU NVIDIA détecté)${NC}"
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
