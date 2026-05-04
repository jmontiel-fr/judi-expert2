#!/bin/bash
set -e

# ─────────────────────────────────────────────────────────
# build.sh — Build production Docker images for Site Central
# Tags images for ECR push.
# ─────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AWS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Config
ECR_REGISTRY="059247592146.dkr.ecr.eu-west-1.amazonaws.com"
BACKEND_IMAGE="${ECR_REGISTRY}/judi-expert/central-backend"
FRONTEND_IMAGE="${ECR_REGISTRY}/judi-expert/central-frontend"
TAG="${1:-latest}"

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert — Build des images de production${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""
echo -e "  Registry : ${GREEN}${ECR_REGISTRY}${NC}"
echo -e "  Tag      : ${GREEN}${TAG}${NC}"
echo ""

# ── Backend ────────────────────────────────────────────
echo -e "${YELLOW}[1/2]${NC} Build de ${GREEN}central-backend${NC} (FastAPI)..."
docker build \
  -t "${BACKEND_IMAGE}:${TAG}" \
  -f "$AWS_DIR/web/backend/Dockerfile" \
  "$AWS_DIR/web/backend"
echo -e "${GREEN}  ✔ Backend built: ${BACKEND_IMAGE}:${TAG}${NC}"
echo ""

# ── Frontend ───────────────────────────────────────────
echo -e "${YELLOW}[2/2]${NC} Build de ${GREEN}central-frontend${NC} (Next.js)..."
docker build \
  -t "${FRONTEND_IMAGE}:${TAG}" \
  --build-arg NEXT_PUBLIC_API_URL="/api" \
  --build-arg NEXT_PUBLIC_RECAPTCHA_SITE_KEY="6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI" \
  -f "$AWS_DIR/web/frontend/Dockerfile" \
  "$AWS_DIR/web/frontend"
echo -e "${GREEN}  ✔ Frontend built: ${FRONTEND_IMAGE}:${TAG}${NC}"
echo ""

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✔ Images de production prêtes${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${YELLOW}Prochaine étape :${NC} ./push-ecr.sh [tag]"
