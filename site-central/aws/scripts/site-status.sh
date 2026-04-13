#!/bin/bash
set -e

# ─────────────────────────────────────────────────────────
# site-status.sh — Statut du Site Central Judi-Expert
# Affiche l'état de chaque composant :
#   - ECS Fargate (tâches en cours / désirées)
#   - RDS PostgreSQL (available, stopped, starting, etc.)
#   - ALB (mode normal ou maintenance)
# Indicateurs : 🟢 actif, 🔴 arrêté, 🟡 en transition
# Exigences : 36.3, 36.6
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
echo -e "${BLUE}  Judi-Expert — Statut du Site Central${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""

# ── ECS Status ─────────────────────────────────────────
echo -e "  ${BLUE}── ECS Fargate ──${NC}"
ECS_INFO=$(aws ecs describe-services \
  --cluster "$ECS_CLUSTER" \
  --services "$ECS_SERVICE" \
  --region "$AWS_REGION" \
  --query "services[0].{running:runningCount,desired:desiredCount,status:status}" \
  --output json \
  --no-cli-pager 2>/dev/null || echo '{"running":null,"desired":null,"status":"UNKNOWN"}')

ECS_RUNNING=$(echo "$ECS_INFO" | grep -o '"running":[0-9]*' | cut -d: -f2)
ECS_DESIRED=$(echo "$ECS_INFO" | grep -o '"desired":[0-9]*' | cut -d: -f2)
ECS_STATUS=$(echo "$ECS_INFO" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)

ECS_RUNNING="${ECS_RUNNING:-0}"
ECS_DESIRED="${ECS_DESIRED:-0}"
ECS_STATUS="${ECS_STATUS:-UNKNOWN}"

if [ "$ECS_RUNNING" -gt 0 ] 2>/dev/null; then
  echo -e "  ${GREEN}●${NC} ECS : ${GREEN}ACTIF${NC} — ${ECS_RUNNING}/${ECS_DESIRED} tâches en cours (${ECS_STATUS})"
elif [ "$ECS_DESIRED" -gt 0 ] 2>/dev/null; then
  echo -e "  ${YELLOW}●${NC} ECS : ${YELLOW}DÉMARRAGE${NC} — ${ECS_RUNNING}/${ECS_DESIRED} tâches en cours (${ECS_STATUS})"
else
  echo -e "  ${RED}●${NC} ECS : ${RED}ARRÊTÉ${NC} — ${ECS_RUNNING}/${ECS_DESIRED} tâches (${ECS_STATUS})"
fi
echo ""

# ── RDS Status ─────────────────────────────────────────
echo -e "  ${BLUE}── RDS PostgreSQL ──${NC}"
RDS_STATUS=$(aws rds describe-db-instances \
  --db-instance-identifier "$RDS_INSTANCE_ID" \
  --region "$AWS_REGION" \
  --query "DBInstances[0].DBInstanceStatus" \
  --output text \
  --no-cli-pager 2>/dev/null || echo "unknown")

case "$RDS_STATUS" in
  available)
    echo -e "  ${GREEN}●${NC} RDS : ${GREEN}DISPONIBLE${NC} (${RDS_STATUS})"
    ;;
  stopped)
    echo -e "  ${RED}●${NC} RDS : ${RED}ARRÊTÉ${NC} (${RDS_STATUS})"
    ;;
  starting|stopping|modifying|backing-up|configuring-enhanced-monitoring)
    echo -e "  ${YELLOW}●${NC} RDS : ${YELLOW}EN TRANSITION${NC} (${RDS_STATUS})"
    ;;
  *)
    echo -e "  ${YELLOW}●${NC} RDS : ${YELLOW}${RDS_STATUS}${NC}"
    ;;
esac
echo ""

# ── ALB Status ─────────────────────────────────────────
echo -e "  ${BLUE}── ALB (Load Balancer) ──${NC}"

ALB_ARN=$(aws elbv2 describe-load-balancers \
  --names "$ALB_NAME" \
  --region "$AWS_REGION" \
  --query "LoadBalancers[0].LoadBalancerArn" \
  --output text \
  --no-cli-pager 2>/dev/null || echo "None")

if [ -z "$ALB_ARN" ] || [ "$ALB_ARN" = "None" ]; then
  echo -e "  ${RED}●${NC} ALB : ${RED}INTROUVABLE${NC}"
else
  LISTENER_ARN=$(aws elbv2 describe-listeners \
    --load-balancer-arn "$ALB_ARN" \
    --region "$AWS_REGION" \
    --query "Listeners[?Port==\`80\`].ListenerArn | [0]" \
    --output text \
    --no-cli-pager 2>/dev/null || echo "None")

  if [ -z "$LISTENER_ARN" ] || [ "$LISTENER_ARN" = "None" ]; then
    echo -e "  ${RED}●${NC} ALB : ${RED}PAS DE LISTENER HTTP${NC}"
  else
    RULE_COUNT=$(aws elbv2 describe-rules \
      --listener-arn "$LISTENER_ARN" \
      --region "$AWS_REGION" \
      --query "length(Rules[?!IsDefault])" \
      --output text \
      --no-cli-pager 2>/dev/null || echo "0")

    if [ "$RULE_COUNT" -gt 0 ] 2>/dev/null; then
      echo -e "  ${GREEN}●${NC} ALB : ${GREEN}ROUTAGE NORMAL${NC} (${RULE_COUNT} règles actives)"
    else
      echo -e "  ${RED}●${NC} ALB : ${RED}MODE MAINTENANCE${NC} (HTTP 503)"
    fi
  fi
fi
echo ""

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
