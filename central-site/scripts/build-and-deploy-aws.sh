#!/bin/bash
set -e

# ─────────────────────────────────────────────────────────
# build-and-deploy-aws.sh — Build, push, Terraform apply & deploy Site Central
# Usage : bash scripts-dev/build-and-deploy-aws.sh [--skip-terraform] [--skip-build]
# ─────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
CENTRAL_DIR="$ROOT_DIR/central-site"
TERRAFORM_DIR="$CENTRAL_DIR/terraform"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Parse arguments
SKIP_TERRAFORM=""
SKIP_BUILD=""
for arg in "$@"; do
  case "$arg" in
    --skip-terraform) SKIP_TERRAFORM="yes" ;;
    --skip-build) SKIP_BUILD="yes" ;;
    --help|-h)
      echo "Usage: bash scripts-dev/build-and-deploy-aws.sh [--skip-terraform] [--skip-build]"
      echo ""
      echo "Options:"
      echo "  --skip-terraform  Ne pas exécuter terraform plan/apply"
      echo "  --skip-build      Ne pas rebuild les images Docker (utilise les existantes)"
      echo ""
      exit 0
      ;;
  esac
done

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert — Build & Deploy AWS (complet)${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""

# ── Prérequis ──────────────────────────────────────────
echo -e "${YELLOW}[0/5]${NC} Vérification des prérequis..."

if ! command -v aws &> /dev/null; then
  echo -e "${RED}  ✘ AWS CLI non trouvé. Installez-le : https://aws.amazon.com/cli/${NC}"
  exit 1
fi

if ! command -v docker &> /dev/null; then
  echo -e "${RED}  ✘ Docker non trouvé.${NC}"
  exit 1
fi

if ! docker info > /dev/null 2>&1; then
  echo -e "${RED}  ✘ Docker n'est pas démarré. Lancez Docker Desktop.${NC}"
  exit 1
fi

if [ "$SKIP_TERRAFORM" != "yes" ] && ! command -v terraform &> /dev/null; then
  echo -e "${RED}  ✘ Terraform non trouvé. Installez-le : https://www.terraform.io/downloads${NC}"
  exit 1
fi

echo -e "${GREEN}  ✔ Prérequis OK${NC}"
echo ""

# ── Étape 1 : Terraform ───────────────────────────────
if [ "$SKIP_TERRAFORM" != "yes" ]; then
  echo -e "${YELLOW}[1/5]${NC} Terraform — Infrastructure AWS..."
  echo ""

  cd "$TERRAFORM_DIR"

  echo -e "  ${YELLOW}terraform init...${NC}"
  terraform init -input=false > /dev/null 2>&1
  echo -e "  ${GREEN}✔ init${NC}"

  echo -e "  ${YELLOW}terraform plan...${NC}"
  terraform plan -out=tfplan -input=false
  echo ""

  echo -e "  ${YELLOW}terraform apply...${NC}"
  terraform apply -input=false tfplan
  echo -e "  ${GREEN}✔ Infrastructure à jour${NC}"
  echo ""

  cd "$ROOT_DIR"
else
  echo -e "${YELLOW}[1/5]${NC} Terraform — ${YELLOW}SKIP${NC} (--skip-terraform)"
  echo ""
fi

# ── Étape 2 : Build Docker ────────────────────────────
if [ "$SKIP_BUILD" != "yes" ]; then
  echo -e "${YELLOW}[2/5]${NC} Build des images Docker..."
  bash "$CENTRAL_DIR/scripts/build.sh"
  echo ""
else
  echo -e "${YELLOW}[2/5]${NC} Build Docker — ${YELLOW}SKIP${NC} (--skip-build)"
  echo ""
fi

# ── Étape 3 : Push ECR ────────────────────────────────
echo -e "${YELLOW}[3/5]${NC} Push des images vers ECR..."
bash "$CENTRAL_DIR/scripts/push-ecr.sh"
echo ""

# ── Étape 4 : Deploy Lightsail ────────────────────────
echo -e "${YELLOW}[4/5]${NC} Déploiement sur Lightsail..."
bash "$CENTRAL_DIR/scripts/push-deploy.sh"
echo ""

# ── Étape 5 : Résumé ──────────────────────────────────
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✔ Déploiement AWS complet${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""
echo -e "  Site     : ${GREEN}https://www.judi-expert.fr${NC}"
echo -e "  API docs : ${GREEN}https://www.judi-expert.fr/api/docs${NC}"
echo ""
