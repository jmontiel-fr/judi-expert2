#!/bin/bash
set -e

# ─────────────────────────────────────────────────────────
# site-start.sh — Démarrage manuel du Site Central Judi-Expert
# 1. Démarrage de l'instance RDS et attente de disponibilité
# 2. Scale ECS Fargate au nombre désiré (défaut: 1)
# 3. Restauration du routage ALB normal
# Exigences : 36.4, 36.5
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
ECS_DESIRED_COUNT="${ECS_DESIRED_COUNT:-1}"

ECS_CLUSTER="${PROJECT_NAME}-${ENVIRONMENT}-cluster"
ECS_SERVICE="${PROJECT_NAME}-${ENVIRONMENT}-service"
RDS_INSTANCE_ID="${PROJECT_NAME}-${ENVIRONMENT}"
ALB_NAME="${PROJECT_NAME}-${ENVIRONMENT}-alb"

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert — Démarrage du Site Central${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""
echo -e "  Cluster ECS  : ${YELLOW}${ECS_CLUSTER}${NC}"
echo -e "  Service ECS  : ${YELLOW}${ECS_SERVICE}${NC}"
echo -e "  Instance RDS : ${YELLOW}${RDS_INSTANCE_ID}${NC}"
echo -e "  ALB          : ${YELLOW}${ALB_NAME}${NC}"
echo -e "  Région       : ${YELLOW}${AWS_REGION}${NC}"
echo -e "  Desired count: ${YELLOW}${ECS_DESIRED_COUNT}${NC}"
echo ""

# ── Step 1: Start RDS instance ────────────────────────
echo -e "${YELLOW}[1/3]${NC} Démarrage RDS..."
RDS_STATUS=$(aws rds describe-db-instances \
  --db-instance-identifier "$RDS_INSTANCE_ID" \
  --region "$AWS_REGION" \
  --query "DBInstances[0].DBInstanceStatus" \
  --output text \
  --no-cli-pager 2>/dev/null || echo "unknown")

if [ "$RDS_STATUS" = "available" ]; then
  echo -e "${GREEN}  ✔ RDS déjà disponible${NC}"
else
  if [ "$RDS_STATUS" = "stopped" ]; then
    aws rds start-db-instance \
      --db-instance-identifier "$RDS_INSTANCE_ID" \
      --region "$AWS_REGION" \
      --no-cli-pager > /dev/null 2>&1
    echo -e "${GREEN}  ✔ Démarrage RDS demandé${NC}"
  elif [ "$RDS_STATUS" = "starting" ]; then
    echo -e "${YELLOW}  ⚠ RDS déjà en cours de démarrage${NC}"
  else
    echo -e "${YELLOW}  ⚠ RDS dans un état inattendu (${RDS_STATUS}), tentative de démarrage...${NC}"
    aws rds start-db-instance \
      --db-instance-identifier "$RDS_INSTANCE_ID" \
      --region "$AWS_REGION" \
      --no-cli-pager > /dev/null 2>&1 || true
  fi

  # Wait for RDS to become available (poll every 15s, max ~5min)
  echo -e "  Attente de la disponibilité RDS..."
  MAX_ATTEMPTS=20
  for ((i=1; i<=MAX_ATTEMPTS; i++)); do
    RDS_STATUS=$(aws rds describe-db-instances \
      --db-instance-identifier "$RDS_INSTANCE_ID" \
      --region "$AWS_REGION" \
      --query "DBInstances[0].DBInstanceStatus" \
      --output text \
      --no-cli-pager 2>/dev/null)
    if [ "$RDS_STATUS" = "available" ]; then
      echo -e "${GREEN}  ✔ RDS disponible${NC}"
      break
    fi
    echo -e "  [${i}/${MAX_ATTEMPTS}] Statut RDS : ${YELLOW}${RDS_STATUS}${NC}"
    sleep 15
  done

  if [ "$RDS_STATUS" != "available" ]; then
    echo -e "${RED}  ⚠ RDS n'est pas disponible après ${MAX_ATTEMPTS} tentatives (statut: ${RDS_STATUS})${NC}"
    echo -e "${YELLOW}  Poursuite du démarrage ECS malgré tout...${NC}"
  fi
fi
echo ""

# ── Step 2: Scale ECS service ─────────────────────────
echo -e "${YELLOW}[2/3]${NC} Démarrage ECS — Scale à ${ECS_DESIRED_COUNT}..."
aws ecs update-service \
  --cluster "$ECS_CLUSTER" \
  --service "$ECS_SERVICE" \
  --desired-count "$ECS_DESIRED_COUNT" \
  --region "$AWS_REGION" \
  --no-cli-pager > /dev/null
echo -e "${GREEN}  ✔ Service ECS mis à jour (desiredCount=${ECS_DESIRED_COUNT})${NC}"
echo ""

# ── Step 3: Restore ALB normal routing ────────────────
echo -e "${YELLOW}[3/3]${NC} Restauration du routage ALB..."

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

# Get target group ARNs
BACKEND_TG_ARN=$(aws elbv2 describe-target-groups \
  --names "${PROJECT_NAME}-${ENVIRONMENT}-backend" \
  --region "$AWS_REGION" \
  --query "TargetGroups[0].TargetGroupArn" \
  --output text \
  --no-cli-pager 2>/dev/null)

FRONTEND_TG_ARN=$(aws elbv2 describe-target-groups \
  --names "${PROJECT_NAME}-${ENVIRONMENT}-frontend" \
  --region "$AWS_REGION" \
  --query "TargetGroups[0].TargetGroupArn" \
  --output text \
  --no-cli-pager 2>/dev/null)

# Check if forwarding rules already exist
EXISTING_RULES=$(aws elbv2 describe-rules \
  --listener-arn "$LISTENER_ARN" \
  --region "$AWS_REGION" \
  --query "length(Rules[?!IsDefault])" \
  --output text \
  --no-cli-pager 2>/dev/null)

if [ "$EXISTING_RULES" -gt 0 ] 2>/dev/null; then
  echo -e "${YELLOW}  ⚠ Règles de routage déjà présentes (${EXISTING_RULES} règles)${NC}"
else
  # Create backend rule (priority 100 — /api/*)
  aws elbv2 create-rule \
    --listener-arn "$LISTENER_ARN" \
    --priority 100 \
    --conditions "Field=path-pattern,Values=/api/*" \
    --actions "Type=forward,TargetGroupArn=${BACKEND_TG_ARN}" \
    --region "$AWS_REGION" \
    --no-cli-pager > /dev/null

  # Create frontend rule (priority 200 — /*)
  aws elbv2 create-rule \
    --listener-arn "$LISTENER_ARN" \
    --priority 200 \
    --conditions "Field=path-pattern,Values=/*" \
    --actions "Type=forward,TargetGroupArn=${FRONTEND_TG_ARN}" \
    --region "$AWS_REGION" \
    --no-cli-pager > /dev/null

  echo -e "${GREEN}  ✔ Règles de routage ALB restaurées${NC}"
fi
echo ""

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✔ Site Central démarré avec succès${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${YELLOW}Pour vérifier :${NC} ./site-status.sh"
