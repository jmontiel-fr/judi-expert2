#!/bin/bash
set -e

# ─────────────────────────────────────────────────────────
# build.sh — Build production Docker images for Site Central
# Builds: backend (FastAPI) and frontend (Next.js PWA)
# Tags images for ECR push.
# Exigences : 30.2, 30.4
# ─────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AWS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$AWS_DIR/.env"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# ── Load .env ──────────────────────────────────────────
if [ ! -f "$ENV_FILE" ]; then
  echo -e "${RED}Erreur : fichier .env introuvable ($ENV_FILE)${NC}"
  exit 1
fi
set -a
source "$ENV_FILE"
set +a

# ── Validate required variables ───────────────────────
PROJECT_NAME="${PROJECT_NAME:-judi-expert}"
ENVIRONMENT="${ENVIRONMENT:-production}"

if [ -z "$ECR_REGISTRY" ] || [ "$ECR_REGISTRY" = "CHANGEZ_MOI.dkr.ecr.eu-west-3.amazonaws.com" ]; then
  echo -e "${RED}Erreur : ECR_REGISTRY n'est pas configuré dans .env${NC}"
  exit 1
fi

BACKEND_IMAGE="${ECR_REGISTRY}/${PROJECT_NAME}-${ENVIRONMENT}-backend"
FRONTEND_IMAGE="${ECR_REGISTRY}/${PROJECT_NAME}-${ENVIRONMENT}-frontend"
TAG="${1:-latest}"

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert — Build des images de production${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""
echo -e "  Registry : ${GREEN}${ECR_REGISTRY}${NC}"
echo -e "  Tag      : ${GREEN}${TAG}${NC}"
echo ""

# ── Backend ────────────────────────────────────────────
echo -e "${YELLOW}[1/2]${NC} Build de ${GREEN}${PROJECT_NAME}-backend${NC} (FastAPI)..."
docker build \
  -t "${BACKEND_IMAGE}:${TAG}" \
  -f "$AWS_DIR/web/backend/Dockerfile" \
  "$AWS_DIR/web/backend"
echo -e "${GREEN}  ✔ Backend built: ${BACKEND_IMAGE}:${TAG}${NC}"
echo ""

# ── Frontend ───────────────────────────────────────────
echo -e "${YELLOW}[2/2]${NC} Build de ${GREEN}${PROJECT_NAME}-frontend${NC} (Next.js PWA)..."
docker build \
  -t "${FRONTEND_IMAGE}:${TAG}" \
  -f "$AWS_DIR/web/frontend/Dockerfile" \
  "$AWS_DIR/web/frontend"
echo -e "${GREEN}  ✔ Frontend built: ${FRONTEND_IMAGE}:${TAG}${NC}"
echo ""

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✔ Toutes les images de production sont prêtes${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${YELLOW}Prochaine étape :${NC} ./push-ecr.sh [tag]"
