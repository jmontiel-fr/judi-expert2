#!/bin/bash
set -e
# ─────────────────────────────────────────────────────────
# start.sh — Démarrage de l'Application Locale (production)
# Usage : bash local-site/scripts/start.sh
#
# Ce script :
#   1. Vérifie que Docker est disponible
#   2. Démarre les conteneurs
#   3. Vérifie et télécharge le modèle LLM si nécessaire
#   4. Interrompt le démarrage en cas d'échec du téléchargement
# ─────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE="$ROOT_DIR/docker-compose.yml"
ENV_FILE="$ROOT_DIR/.env"

# ── Couleurs ──────────────────────────────────────────────
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ── Charger LLM_MODEL depuis .env ────────────────────────
if [ -f "$ENV_FILE" ]; then
  LLM_MODEL=$(grep -E '^LLM_MODEL=' "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'")
fi
LLM_MODEL="${LLM_MODEL:-mistral:7b-instruct-v0.3-q4_0}"
LLM_CONTAINER="judi-llm"

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert — Démarrage Application Locale${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""

# ── Étape 1 : Vérifier Docker ────────────────────────────
echo -e "${YELLOW}[1/3] Vérification de Docker...${NC}"
if ! docker info > /dev/null 2>&1; then
  echo -e "${RED}  ✘ Docker n'est pas disponible. Démarrez Docker Desktop.${NC}"
  exit 1
fi
echo -e "${GREEN}  ✔ Docker est disponible${NC}"
echo ""

# ── Étape 2 : Démarrer les conteneurs ────────────────────
echo -e "${YELLOW}[2/3] Démarrage des conteneurs...${NC}"
GPU_COMPOSE=""
if command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null; then
  echo -e "${GREEN}  ✔ GPU NVIDIA détecté — accélération GPU activée${NC}"
  GPU_COMPOSE="-f $ROOT_DIR/docker-compose.gpu.yml"
fi
docker compose -f "$COMPOSE" $GPU_COMPOSE up -d
echo -e "${GREEN}  ✔ Conteneurs démarrés${NC}"
echo ""

# ── Étape 3 : Vérifier et télécharger le modèle LLM ─────
echo -e "${YELLOW}[3/3] Vérification du modèle LLM ($LLM_MODEL)...${NC}"

# Attendre que le conteneur Ollama soit prêt
MAX_WAIT=60
ELAPSED=0
echo -e "${YELLOW}  Attente du service Ollama...${NC}"
while ! docker exec "$LLM_CONTAINER" curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; do
  if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
    echo -e "${RED}  ✘ Ollama n'est pas prêt après ${MAX_WAIT}s — abandon${NC}"
    echo -e "${RED}    Vérifiez les logs : docker logs $LLM_CONTAINER${NC}"
    exit 1
  fi
  sleep 2
  ELAPSED=$((ELAPSED + 2))
done
echo -e "${GREEN}  ✔ Service Ollama prêt (${ELAPSED}s)${NC}"

# Forcer la vérification et le téléchargement du modèle
echo -e "${YELLOW}  ⬇ ollama pull $LLM_MODEL (vérification du digest + téléchargement si nécessaire)...${NC}"
if ! docker exec "$LLM_CONTAINER" ollama pull "$LLM_MODEL"; then
  echo -e "${RED}  ✘ Échec du téléchargement du modèle $LLM_MODEL${NC}"
  echo -e "${RED}    Le démarrage est interrompu.${NC}"
  echo -e "${RED}    Réessayez : docker exec $LLM_CONTAINER ollama pull $LLM_MODEL${NC}"
  exit 1
fi
echo -e "${GREEN}  ✔ Modèle $LLM_MODEL vérifié et à jour${NC}"
echo ""

# ── Résumé ────────────────────────────────────────────────
echo -e "${GREEN}══════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✔ Application Locale démarrée avec succès${NC}"
echo -e "${GREEN}══════════════════════════════════════════════${NC}"
echo -e "  Frontend : ${GREEN}http://localhost:3000${NC}"
echo -e "  Backend  : ${GREEN}http://localhost:8000${NC}"
echo -e "  OCR      : ${GREEN}http://localhost:8001${NC}"
echo -e "  LLM      : ${GREEN}http://localhost:11434${NC}"
echo -e "  RAG      : ${GREEN}http://localhost:6333${NC}"
