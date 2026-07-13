#!/usr/bin/env bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════════════
# migrate-admin-email.sh — Migre le compte admin de admin@itechsource.fr
# vers admin@judi-expert.fr (Cognito + BDD)
#
# Prérequis :
#   - AWS CLI configurée avec les bons credentials
#   - terraform.tfvars à jour (admin_email = "admin@judi-expert.fr")
#   - Accès SSH à l'instance Lightsail (pour la mise à jour BDD)
#
# Usage : bash central-site/scripts/migrate-admin-email.sh
# ═══════════════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AWS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TERRAFORM_DIR="$AWS_DIR/terraform"

# ── Configuration ──────────────────────────────────────────
OLD_EMAIL="admin@itechsource.fr"
NEW_EMAIL="admin@judi-expert.fr"
NEW_PASSWORD="Admin\$123!"
AWS_REGION="eu-west-3"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Migration Admin Email${NC}"
echo -e "${BLUE}  $OLD_EMAIL → $NEW_EMAIL${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""

# ── Étape 1 : Récupérer le User Pool ID ──────────────────
echo -e "${YELLOW}[1/5]${NC} Récupération du User Pool ID..."
USER_POOL_ID=$(cd "$TERRAFORM_DIR" && terraform output -raw cognito_user_pool_id 2>/dev/null || echo "")

if [ -z "$USER_POOL_ID" ]; then
    echo -e "${RED}  ✘ Impossible de récupérer le User Pool ID via Terraform.${NC}"
    echo -e "    Renseignez-le manuellement :"
    read -p "    User Pool ID : " USER_POOL_ID
fi
echo -e "${GREEN}  ✔ User Pool ID : $USER_POOL_ID${NC}"
echo ""

# ── Étape 2 : Terraform apply (crée le nouveau user Cognito) ──
echo -e "${YELLOW}[2/5]${NC} Application Terraform (création user Cognito $NEW_EMAIL)..."
echo -e "    ⚠ Cela va supprimer $OLD_EMAIL et créer $NEW_EMAIL dans Cognito."
read -p "    Continuer ? (y/N) : " CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "Annulé."
    exit 0
fi

cd "$TERRAFORM_DIR"
terraform plan -target=module.cognito.aws_cognito_user.admin -out=tfplan
terraform apply tfplan
rm -f tfplan
cd "$SCRIPT_DIR"
echo -e "${GREEN}  ✔ User Cognito $NEW_EMAIL créé${NC}"
echo ""

# ── Étape 3 : Confirmer le mot de passe (sortir de FORCE_CHANGE_PASSWORD) ──
echo -e "${YELLOW}[3/5]${NC} Confirmation du mot de passe (permanent)..."
aws cognito-idp admin-set-user-password \
    --user-pool-id "$USER_POOL_ID" \
    --username "$NEW_EMAIL" \
    --password "$NEW_PASSWORD" \
    --permanent \
    --region "$AWS_REGION"
echo -e "${GREEN}  ✔ Mot de passe confirmé — statut CONFIRMED${NC}"
echo ""

# ── Étape 4 : Récupérer le nouveau cognito_sub ──────────────
echo -e "${YELLOW}[4/5]${NC} Récupération du cognito_sub du nouveau user..."
NEW_SUB=$(aws cognito-idp admin-get-user \
    --user-pool-id "$USER_POOL_ID" \
    --username "$NEW_EMAIL" \
    --region "$AWS_REGION" \
    --query "Username" \
    --output text)
echo -e "${GREEN}  ✔ Nouveau cognito_sub : $NEW_SUB${NC}"
echo ""

# ── Étape 5 : Mettre à jour la BDD ──────────────────────────
echo -e "${YELLOW}[5/5]${NC} Mise à jour de la base de données..."
echo ""
echo -e "  Exécutez cette requête SQL sur la BDD prod (via psql ou le script push-deploy) :"
echo ""
echo -e "${BLUE}  UPDATE experts"
echo -e "  SET email = '$NEW_EMAIL',"
echo -e "      cognito_sub = '$NEW_SUB'"
echo -e "  WHERE email = '$OLD_EMAIL';${NC}"
echo ""

# Si SSH est accessible, proposer l'exécution directe
ENV_AWS_FILE="$AWS_DIR/.env.aws"
if [ -f "$ENV_AWS_FILE" ]; then
    DB_URL=$(grep "^DATABASE_URL=" "$ENV_AWS_FILE" | cut -d'=' -f2- | sed 's|postgresql+asyncpg://|postgresql://|')
    if [ -n "$DB_URL" ] && [[ "$DB_URL" != *"PENDING"* ]]; then
        echo -e "  Ou exécution automatique via psql :"
        read -p "  Exécuter maintenant ? (y/N) : " EXEC_SQL
        if [ "$EXEC_SQL" = "y" ] || [ "$EXEC_SQL" = "Y" ]; then
            PGPASSWORD=$(echo "$DB_URL" | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')
            PGHOST=$(echo "$DB_URL" | sed -n 's|.*@\([^:]*\):.*|\1|p')
            PGPORT=$(echo "$DB_URL" | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
            PGDB=$(echo "$DB_URL" | sed -n 's|.*/\(.*\)|\1|p')
            PGUSER=$(echo "$DB_URL" | sed -n 's|.*://\([^:]*\):.*|\1|p')

            PGPASSWORD="$PGPASSWORD" psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDB" \
                -c "UPDATE experts SET email = '$NEW_EMAIL', cognito_sub = '$NEW_SUB' WHERE email = '$OLD_EMAIL';"
            echo -e "${GREEN}  ✔ BDD mise à jour${NC}"
        fi
    fi
fi

echo ""
echo -e "${GREEN}══════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Migration terminée !${NC}"
echo -e "${GREEN}  Connectez-vous avec : $NEW_EMAIL / $NEW_PASSWORD${NC}"
echo -e "${GREEN}══════════════════════════════════════════════${NC}"
