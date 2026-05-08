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
RED='\033[0;31m'
NC='\033[0m'

# ── Read version from VERSION file ────────────────────
VERSION_FILE="$AWS_DIR/VERSION"
if [ -f "$VERSION_FILE" ]; then
    VERSION=$(head -n 1 "$VERSION_FILE")
else
    echo -e "${RED}ERROR: VERSION file not found at $VERSION_FILE${NC}"
    exit 1
fi

# Config
ECR_REGISTRY="059247592146.dkr.ecr.eu-west-1.amazonaws.com"
BACKEND_IMAGE="${ECR_REGISTRY}/judi-expert/central-backend"
FRONTEND_IMAGE="${ECR_REGISTRY}/judi-expert/central-frontend"
TAG="${1:-$VERSION}"

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert — Build des images de production${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""
echo -e "  Version  : ${GREEN}${VERSION}${NC}"
echo -e "  Registry : ${GREEN}${ECR_REGISTRY}${NC}"
echo -e "  Tag      : ${GREEN}${TAG}${NC}"
echo ""

# ── Ensure Docker is running ───────────────────────────
if ! docker info > /dev/null 2>&1; then
  echo -e "${YELLOW}[0/2]${NC} Docker n'est pas démarré. Lancement de Docker Desktop..."
  if command -v "Docker Desktop" > /dev/null 2>&1 || [ -f "/c/Program Files/Docker/Docker/Docker Desktop.exe" ]; then
    "/c/Program Files/Docker/Docker/Docker Desktop.exe" &
  elif [ -f "/mnt/c/Program Files/Docker/Docker/Docker Desktop.exe" ]; then
    "/mnt/c/Program Files/Docker/Docker/Docker Desktop.exe" &
  elif command -v open > /dev/null 2>&1; then
    open -a Docker
  else
    echo -e "${RED}  ✘ Impossible de lancer Docker Desktop automatiquement.${NC}"
    echo -e "${RED}    Lancez Docker Desktop manuellement puis relancez ce script.${NC}"
    exit 1
  fi
  # Attendre que Docker soit prêt (max 60s)
  echo -n "  Attente de Docker"
  for i in $(seq 1 60); do
    if docker info > /dev/null 2>&1; then
      echo ""
      echo -e "${GREEN}  ✔ Docker Desktop prêt${NC}"
      break
    fi
    echo -n "."
    sleep 1
  done
  if ! docker info > /dev/null 2>&1; then
    echo ""
    echo -e "${RED}  ✘ Docker Desktop n'a pas démarré dans les 60s.${NC}"
    exit 1
  fi
  echo ""
fi

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
  --build-arg NEXT_PUBLIC_API_URL="" \
  --build-arg NEXT_PUBLIC_APP_ENV="production" \
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
