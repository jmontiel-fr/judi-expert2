#!/bin/bash
set -e

# ─────────────────────────────────────────────────────────
# deploy.sh — Deploy AWS infrastructure via Terraform
# Runs: terraform init, plan, and apply.
# Exigences : 30.5
# ─────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AWS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TERRAFORM_DIR="$AWS_DIR/terraform"
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

# ── Validate Terraform directory ──────────────────────
if [ ! -d "$TERRAFORM_DIR" ]; then
  echo -e "${RED}Erreur : répertoire Terraform introuvable ($TERRAFORM_DIR)${NC}"
  exit 1
fi

PROJECT_NAME="${PROJECT_NAME:-judi-expert}"
ENVIRONMENT="${ENVIRONMENT:-production}"
AWS_REGION="${AWS_REGION:-eu-west-3}"

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert — Déploiement AWS (Terraform)${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""
echo -e "  Projet      : ${GREEN}${PROJECT_NAME}${NC}"
echo -e "  Environnement: ${GREEN}${ENVIRONMENT}${NC}"
echo -e "  Région       : ${GREEN}${AWS_REGION}${NC}"
echo -e "  Terraform    : ${GREEN}${TERRAFORM_DIR}${NC}"
echo ""

# ── Terraform Init ─────────────────────────────────────
echo -e "${YELLOW}[1/3]${NC} Initialisation de Terraform..."
terraform -chdir="$TERRAFORM_DIR" init
echo -e "${GREEN}  ✔ Terraform initialisé${NC}"
echo ""

# ── Terraform Plan ─────────────────────────────────────
echo -e "${YELLOW}[2/3]${NC} Planification des changements..."
terraform -chdir="$TERRAFORM_DIR" plan -out=tfplan
echo -e "${GREEN}  ✔ Plan Terraform généré${NC}"
echo ""

# ── Terraform Apply ────────────────────────────────────
echo -e "${YELLOW}[3/3]${NC} Application des changements..."
terraform -chdir="$TERRAFORM_DIR" apply tfplan
echo -e "${GREEN}  ✔ Déploiement Terraform terminé${NC}"
echo ""

# ── Cleanup plan file ─────────────────────────────────
rm -f "$TERRAFORM_DIR/tfplan"

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✔ Infrastructure AWS déployée avec succès${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
