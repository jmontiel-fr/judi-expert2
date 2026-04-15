#!/bin/bash
set -e

# ─────────────────────────────────────────────────────────
# update-rag.sh — Build and push a RAG image for a domain
# Usage: ./update-rag.sh <domain_name> [tag]
# Example: ./update-rag.sh psychologie v1.0.0
# Exigences : 30.6
# ─────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AWS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$AWS_DIR/.." && pwd)"
ENV_FILE="$AWS_DIR/.env"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# ── Validate arguments ─────────────────────────────────
if [ -z "$1" ]; then
  echo -e "${RED}Erreur : nom de domaine requis${NC}"
  echo ""
  echo -e "Usage : ${YELLOW}./update-rag.sh <domaine> [tag]${NC}"
  echo -e "Exemple : ${GREEN}./update-rag.sh psychologie v1.0.0${NC}"
  echo ""
  echo -e "Domaines disponibles :"
  echo -e "  - psychologie"
  echo -e "  - psychiatrie"
  echo -e "  - medecine_legale"
  echo -e "  - batiment"
  echo -e "  - comptabilite"
  exit 1
fi

DOMAIN="$1"
TAG="${2:-latest}"

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

# ── Validate corpus directory ─────────────────────────
CORPUS_DIR="$REPO_ROOT/corpus/$DOMAIN"
if [ ! -d "$CORPUS_DIR" ]; then
  echo -e "${RED}Erreur : répertoire corpus introuvable ($CORPUS_DIR)${NC}"
  echo -e "Vérifiez que le domaine '${DOMAIN}' existe dans corpus/"
  exit 1
fi

RAG_IMAGE="${ECR_REGISTRY}/${PROJECT_NAME}-${ENVIRONMENT}-rag-${DOMAIN}"

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert — Mise à jour image RAG${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""
echo -e "  Domaine  : ${GREEN}${DOMAIN}${NC}"
echo -e "  Tag      : ${GREEN}${TAG}${NC}"
echo -e "  Image    : ${GREEN}${RAG_IMAGE}:${TAG}${NC}"
echo ""

# ── Build RAG image ────────────────────────────────────
echo -e "${YELLOW}[1/3]${NC} Build de l'image RAG pour ${GREEN}${DOMAIN}${NC}..."
docker build \
  -t "${RAG_IMAGE}:${TAG}" \
  --build-arg DOMAIN="$DOMAIN" \
  -f "$REPO_ROOT/local-site/rag/Dockerfile" \
  "$CORPUS_DIR"
echo -e "${GREEN}  ✔ Image RAG built: ${RAG_IMAGE}:${TAG}${NC}"
echo ""

# ── ECR Authentication ─────────────────────────────────
echo -e "${YELLOW}[2/3]${NC} Authentification auprès d'ECR (${GREEN}${AWS_REGION}${NC})..."
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_REGISTRY"
echo -e "${GREEN}  ✔ Authentification ECR réussie${NC}"
echo ""

# ── Push RAG image ─────────────────────────────────────
echo -e "${YELLOW}[3/3]${NC} Push de ${GREEN}${RAG_IMAGE}:${TAG}${NC}..."
docker push "${RAG_IMAGE}:${TAG}"
echo -e "${GREEN}  ✔ Image RAG pushed: ${RAG_IMAGE}:${TAG}${NC}"
echo ""

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✔ Image RAG '${DOMAIN}' mise à jour (${TAG})${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
