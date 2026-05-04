#!/bin/bash
set -e

# ─────────────────────────────────────────────────────────
# push-ecr.sh — Authenticate to ECR and push production images
# ─────────────────────────────────────────────────────────

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Config
ECR_REGISTRY="059247592146.dkr.ecr.eu-west-1.amazonaws.com"
AWS_REGION="eu-west-1"
BACKEND_IMAGE="${ECR_REGISTRY}/judi-expert/central-backend"
FRONTEND_IMAGE="${ECR_REGISTRY}/judi-expert/central-frontend"
TAG="${1:-latest}"

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert — Push des images vers ECR${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""

# ── ECR Authentication ─────────────────────────────────
echo -e "${YELLOW}[1/3]${NC} Authentification ECR (${GREEN}${AWS_REGION}${NC})..."
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_REGISTRY"
echo -e "${GREEN}  ✔ Authentification ECR réussie${NC}"
echo ""

# ── Push Backend ───────────────────────────────────────
echo -e "${YELLOW}[2/3]${NC} Push de ${GREEN}central-backend:${TAG}${NC}..."
docker push "${BACKEND_IMAGE}:${TAG}"
echo -e "${GREEN}  ✔ Backend pushed${NC}"
echo ""

# ── Push Frontend ──────────────────────────────────────
echo -e "${YELLOW}[3/3]${NC} Push de ${GREEN}central-frontend:${TAG}${NC}..."
docker push "${FRONTEND_IMAGE}:${TAG}"
echo -e "${GREEN}  ✔ Frontend pushed${NC}"
echo ""

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✔ Images poussées vers ECR${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${YELLOW}Prochaine étape :${NC} ./push-deploy.sh [tag]"
