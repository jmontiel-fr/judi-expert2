#!/bin/bash
set -e

# ─────────────────────────────────────────────────────────
# site-stop.sh — Arrêt manuel du Site Central Judi-Expert
# 1. Scale ECS Fargate à zéro
# 2. Arrêt de l'instance RDS PostgreSQL
# 3. Configuration ALB en mode maintenance (HTTP 503)
# Exigences : 36.1, 36.2, 36.3, 36.4
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

# ── Configuration ──────────────────────────────────────
PROJECT_NAME="${PROJECT_NAME:-judi-expert}"
ENVIRONMENT="${ENVIRONMENT:-production}"
AWS_REGION="${AWS_REGION:-eu-west-3}"

ECS_CLUSTER="${PROJECT_NAME}-${ENVIRONMENT}-cluster"
ECS_SERVICE="${PROJECT_NAME}-${ENVIRONMENT}-service"
RDS_INSTANCE_ID="${PROJECT_NAME}-${ENVIRONMENT}"
ALB_NAME="${PROJECT_NAME}-${ENVIRONMENT}-alb"

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert — Arrêt du Site Central${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""
echo -e "  Cluster ECS  : ${YELLOW}${ECS_CLUSTER}${NC}"
echo -e "  Service ECS  : ${YELLOW}${ECS_SERVICE}${NC}"
echo -e "  Instance RDS : ${YELLOW}${RDS_INSTANCE_ID}${NC}"
echo -e "  ALB          : ${YELLOW}${ALB_NAME}${NC}"
echo -e "  Région       : ${YELLOW}${AWS_REGION}${NC}"
echo ""

# ── Step 1: Scale ECS to zero ─────────────────────────
echo -e "${YELLOW}[1/3]${NC} Arrêt ECS — Scale-to-zero..."
aws ecs update-service \
  --cluster "$ECS_CLUSTER" \
  --service "$ECS_SERVICE" \
  --desired-count 0 \
  --region "$AWS_REGION" \
  --no-cli-pager > /dev/null
echo -e "${GREEN}  ✔ Service ECS mis à zéro (desiredCount=0)${NC}"
echo ""

# ── Step 2: Stop RDS instance ─────────────────────────
echo -e "${YELLOW}[2/3]${NC} Arrêt RDS..."
RDS_STATUS=$(aws rds describe-db-instances \
  --db-instance-identifier "$RDS_INSTANCE_ID" \
  --region "$AWS_REGION" \
  --query "DBInstances[0].DBInstanceStatus" \
  --output text \
  --no-cli-pager 2>/dev/null || echo "unknown")

if [ "$RDS_STATUS" = "stopped" ] || [ "$RDS_STATUS" = "stopping" ]; then
  echo -e "${YELLOW}  ⚠ RDS déjà en cours d'arrêt ou arrêté (statut: ${RDS_STATUS})${NC}"
else
  aws rds stop-db-instance \
    --db-instance-identifier "$RDS_INSTANCE_ID" \
    --region "$AWS_REGION" \
    --no-cli-pager > /dev/null 2>&1 || echo -e "${YELLOW}  ⚠ RDS déjà en cours d'arrêt${NC}"
  echo -e "${GREEN}  ✔ Arrêt RDS demandé${NC}"
fi
echo ""

# ── Step 3: Configure ALB maintenance mode ────────────
echo -e "${YELLOW}[3/3]${NC} Activation du mode maintenance ALB..."

# Get the ALB ARN
ALB_ARN=$(aws elbv2 describe-load-balancers \
  --names "$ALB_NAME" \
  --region "$AWS_REGION" \
  --query "LoadBalancers[0].LoadBalancerArn" \
  --output text \
  --no-cli-pager 2>/dev/null)

if [ -z "$ALB_ARN" ] || [ "$ALB_ARN" = "None" ]; then
  echo -e "${RED}  ✘ ALB introuvable : ${ALB_NAME}${NC}"
  exit 1
fi

# Get the HTTP listener ARN
LISTENER_ARN=$(aws elbv2 describe-listeners \
  --load-balancer-arn "$ALB_ARN" \
  --region "$AWS_REGION" \
  --query "Listeners[?Port==\`80\`].ListenerArn | [0]" \
  --output text \
  --no-cli-pager 2>/dev/null)

if [ -z "$LISTENER_ARN" ] || [ "$LISTENER_ARN" = "None" ]; then
  echo -e "${RED}  ✘ Listener HTTP introuvable sur l'ALB${NC}"
  exit 1
fi

# Delete forwarding rules (backend priority 100, frontend priority 200)
# This leaves only the default action (fixed-response 503 maintenance page)
RULE_ARNS=$(aws elbv2 describe-rules \
  --listener-arn "$LISTENER_ARN" \
  --region "$AWS_REGION" \
  --query "Rules[?!IsDefault].RuleArn" \
  --output text \
  --no-cli-pager 2>/dev/null)

for RULE_ARN in $RULE_ARNS; do
  aws elbv2 delete-rule \
    --rule-arn "$RULE_ARN" \
    --region "$AWS_REGION" \
    --no-cli-pager > /dev/null 2>&1 || true
done
echo -e "${GREEN}  ✔ Mode maintenance activé (HTTP 503)${NC}"
echo ""

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✔ Site Central arrêté avec succès${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${YELLOW}Pour redémarrer :${NC} ./site-start.sh"
echo -e "  ${YELLOW}Pour vérifier   :${NC} ./site-status.sh"
