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

# ── Read version from VERSION file ────────────────────
VERSION_FILE="$AWS_DIR/VERSION"
if [ -f "$VERSION_FILE" ]; then
    VERSION=$(head -n 1 "$VERSION_FILE")
else
    echo -e "${RED}ERROR: VERSION file not found at $VERSION_FILE${NC}"
    exit 1
fi

echo "Deploying with version: $VERSION"

# ── Load .env ──────────────────────────────────────────
if [ ! -f "$ENV_FILE" ]; then
  echo -e "${RED}Erreur : fichier .env introuvable ($ENV_FILE)${NC}"
  exit 1
fi
set -a
source "$ENV_FILE"
set +a

# Export version for Terraform
export TF_VAR_app_version="$VERSION"

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
echo -e "  Version       : ${GREEN}${VERSION}${NC}"
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
terraform -chdir="$TERRAFORM_DIR" plan -var="app_version=${VERSION}" -out=tfplan
echo -e "${GREEN}  ✔ Plan Terraform généré${NC}"
echo ""

# ── Terraform Apply ────────────────────────────────────
echo -e "${YELLOW}[3/3]${NC} Application des changements..."
terraform -chdir="$TERRAFORM_DIR" apply tfplan
echo -e "${GREEN}  ✔ Déploiement Terraform terminé${NC}"
echo ""

# ── Cleanup plan file ─────────────────────────────────
rm -f "$TERRAFORM_DIR/tfplan"

# ── Update .env.aws with Terraform outputs ─────────────
ENV_AWS_FILE="$AWS_DIR/.env.aws"

if [ -f "$ENV_AWS_FILE" ]; then
  echo -e "${YELLOW}[4/4]${NC} Mise à jour de .env.aws avec les outputs Terraform..."

  # Récupérer les outputs
  RDS_ENDPOINT=$(terraform -chdir="$TERRAFORM_DIR" output -raw rds_endpoint 2>/dev/null || echo "")
  COGNITO_POOL_ID=$(terraform -chdir="$TERRAFORM_DIR" output -raw cognito_user_pool_id 2>/dev/null || echo "")
  COGNITO_CLIENT_ID=$(terraform -chdir="$TERRAFORM_DIR" output -raw cognito_user_pool_client_id 2>/dev/null || echo "")

  # Mettre à jour DATABASE_URL
  if [ -n "$RDS_ENDPOINT" ]; then
    # Extraire user/password/db existants ou utiliser les valeurs par défaut
    DB_USER="${db_username:-judi_admin}"
    DB_PASS="${db_password:-JudiExpert2026!Prod}"
    DB_NAME="${db_name:-judi_expert}"
    NEW_DB_URL="postgresql+asyncpg://${DB_USER}:${DB_PASS}@${RDS_ENDPOINT}:5432/${DB_NAME}"
    sed -i "s|^DATABASE_URL=.*|DATABASE_URL=${NEW_DB_URL}|" "$ENV_AWS_FILE"
    echo -e "${GREEN}  ✔ DATABASE_URL mis à jour (${RDS_ENDPOINT})${NC}"
  fi

  # Mettre à jour Cognito
  if [ -n "$COGNITO_POOL_ID" ]; then
    sed -i "s|^COGNITO_USER_POOL_ID=.*|COGNITO_USER_POOL_ID=${COGNITO_POOL_ID}|" "$ENV_AWS_FILE"
    echo -e "${GREEN}  ✔ COGNITO_USER_POOL_ID mis à jour${NC}"
  fi

  if [ -n "$COGNITO_CLIENT_ID" ]; then
    sed -i "s|^COGNITO_APP_CLIENT_ID=.*|COGNITO_APP_CLIENT_ID=${COGNITO_CLIENT_ID}|" "$ENV_AWS_FILE"
    echo -e "${GREEN}  ✔ COGNITO_APP_CLIENT_ID mis à jour${NC}"
  fi

  echo ""
else
  echo -e "${YELLOW}  ⚠ .env.aws introuvable — les outputs Terraform n'ont pas été injectés.${NC}"
  echo -e "${YELLOW}    Créez central-site/.env.aws avant de lancer push-deploy.sh${NC}"
  echo ""
fi

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✔ Infrastructure AWS déployée avec succès${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
