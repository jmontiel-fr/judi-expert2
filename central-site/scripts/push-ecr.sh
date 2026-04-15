#!/bin/bash
set -e

# ─────────────────────────────────────────────────────────
# push-ecr.sh — Authenticate to ECR and push production images
# Pushes: backend and frontend images to ECR.
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
AWS_REGION="${AWS_REGION:-eu-west-3}"

if [ -z "$ECR_REGISTRY" ] || [ "$ECR_REGISTRY" = "CHANGEZ_MOI.dkr.ecr.eu-west-3.amazonaws.com" ]; then
  echo -e "${RED}Erreur : ECR_REGISTRY n'est pas configuré dans .env${NC}"
  exit 1
fi

BACKEND_IMAGE="${ECR_REGISTRY}/${PROJECT_NAME}-${ENVIRONMENT}-backend"
FRONTEND_IMAGE="${ECR_REGISTRY}/${PROJECT_NAME}-${ENVIRONMENT}-frontend"
TAG="${1:-latest}"

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert — Push des images vers ECR${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""

# ── ECR Authentication ─────────────────────────────────
echo -e "${YELLOW}[1/3]${NC} Authentification auprès d'ECR (${GREEN}${AWS_REGION}${NC})..."
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_REGISTRY"
echo -e "${GREEN}  ✔ Authentification ECR réussie${NC}"
echo ""

# ── Push Backend ───────────────────────────────────────
echo -e "${YELLOW}[2/3]${NC} Push de ${GREEN}${PROJECT_NAME}-backend:${TAG}${NC}..."
docker push "${BACKEND_IMAGE}:${TAG}"
echo -e "${GREEN}  ✔ Backend pushed: ${BACKEND_IMAGE}:${TAG}${NC}"
echo ""

# ── Push Frontend ──────────────────────────────────────
echo -e "${YELLOW}[3/3]${NC} Push de ${GREEN}${PROJECT_NAME}-frontend:${TAG}${NC}..."
docker push "${FRONTEND_IMAGE}:${TAG}"
echo -e "${GREEN}  ✔ Frontend pushed: ${FRONTEND_IMAGE}:${TAG}${NC}"
echo ""

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✔ Toutes les images ont été poussées vers ECR${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${YELLOW}Prochaine étape :${NC} ./deploy.sh"
