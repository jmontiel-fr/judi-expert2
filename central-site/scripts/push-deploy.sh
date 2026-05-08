#!/bin/bash
set -e

# ─────────────────────────────────────────────────────────
# push-deploy.sh — Deploy Site Central on Lightsail (pull from ECR)
# ─────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AWS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT_DIR="$(cd "$AWS_DIR/.." && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Config
INSTANCE_NAME="judi-expert-production"
REGION="eu-west-1"
SSH_USER="ec2-user"
KEY_FILE="$SCRIPT_DIR/lightsail-key.pem"
REMOTE_DIR="/opt/judi-expert"
ECR_REGISTRY="059247592146.dkr.ecr.eu-west-1.amazonaws.com"
BACKEND_IMAGE="${ECR_REGISTRY}/judi-expert/central-backend"
FRONTEND_IMAGE="${ECR_REGISTRY}/judi-expert/central-frontend"
TAG="${1:-latest}"

ENV_AWS_FILE="$AWS_DIR/.env.aws"

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert — Déploiement sur Lightsail${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""

# ── Validate .env.aws ──────────────────────────────────
if [ ! -f "$ENV_AWS_FILE" ]; then
  echo -e "${RED}  ✘ Fichier .env.aws introuvable ($ENV_AWS_FILE)${NC}"
  echo -e "${RED}    Créez-le à partir du template et renseignez les valeurs.${NC}"
  exit 1
fi

# Vérifier que DATABASE_URL n'est pas vide ou placeholder
DB_URL=$(grep "^DATABASE_URL=" "$ENV_AWS_FILE" | cut -d'=' -f2-)
if [ -z "$DB_URL" ] || [[ "$DB_URL" == *"PENDING"* ]]; then
  echo -e "${RED}  ✘ DATABASE_URL non configurée dans .env.aws${NC}"
  echo -e "${RED}    Renseignez l'endpoint RDS avant de déployer.${NC}"
  exit 1
fi
echo -e "${GREEN}  ✔ .env.aws validé${NC}"
echo ""

# ── Get instance IP ────────────────────────────────────
echo -e "${YELLOW}[1/5]${NC} Récupération de l'IP Lightsail..."
IP=$(aws lightsail get-static-ip --static-ip-name "${INSTANCE_NAME}-ip" --region "$REGION" --query "staticIp.ipAddress" --output text)
if [ -z "$IP" ]; then
  echo -e "${RED}  ✘ Impossible de récupérer l'IP. Lancez d'abord deploy.sh${NC}"
  exit 1
fi
echo -e "${GREEN}  ✔ IP : ${IP}${NC}"
echo ""

# ── Get SSH key if not present ─────────────────────────
if [ ! -f "$KEY_FILE" ]; then
  echo -e "${YELLOW}[1b]${NC} Téléchargement de la clé SSH..."
  aws lightsail download-default-key-pair --region "$REGION" --query "privateKeyBase64" --output text > "$KEY_FILE"
  chmod 600 "$KEY_FILE"
  echo -e "${GREEN}  ✔ Clé SSH sauvegardée${NC}"
  echo ""
fi

SSH_CMD="ssh -i $KEY_FILE -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null $SSH_USER@$IP"
SCP_CMD="scp -i $KEY_FILE -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

# ── Upload docker-compose and config ──────────────────
echo -e "${YELLOW}[2/5]${NC} Upload de la configuration..."
$SSH_CMD "sudo mkdir -p $REMOTE_DIR/domaines $REMOTE_DIR/corpus $REMOTE_DIR/docs && sudo chown -R ec2-user:ec2-user $REMOTE_DIR"
$SCP_CMD "$AWS_DIR/docker-compose.prod.yml" "$SSH_USER@$IP:$REMOTE_DIR/docker-compose.yml"
$SCP_CMD "$ENV_AWS_FILE" "$SSH_USER@$IP:$REMOTE_DIR/.env"
$SCP_CMD "$ROOT_DIR/domaines/domaines.yaml" "$SSH_USER@$IP:$REMOTE_DIR/domaines/domaines.yaml"
$SCP_CMD -r "$ROOT_DIR/corpus/." "$SSH_USER@$IP:$REMOTE_DIR/corpus/"
$SCP_CMD -r "$ROOT_DIR/docs/." "$SSH_USER@$IP:$REMOTE_DIR/docs/"
echo -e "${GREEN}  ✔ Configuration uploadée${NC}"
echo ""

# ── ECR login on instance ──────────────────────────────
echo -e "${YELLOW}[3/5]${NC} Authentification ECR sur l'instance..."
ECR_PASSWORD=$(aws ecr get-login-password --region "$REGION")
$SSH_CMD "echo '${ECR_PASSWORD}' | sudo docker login --username AWS --password-stdin ${ECR_REGISTRY}"
echo -e "${GREEN}  ✔ ECR authentifié${NC}"
echo ""

# ── Pull images on instance ────────────────────────────
echo -e "${YELLOW}[4/5]${NC} Pull des images depuis ECR..."
$SSH_CMD "sudo docker pull ${BACKEND_IMAGE}:${TAG} && sudo docker pull ${FRONTEND_IMAGE}:${TAG}"
echo -e "${GREEN}  ✔ Images pullées${NC}"
echo ""

# ── Start services ─────────────────────────────────────
echo -e "${YELLOW}[5/7]${NC} Démarrage des services..."
$SSH_CMD "cd $REMOTE_DIR && sudo docker compose down --remove-orphans 2>/dev/null; sudo docker compose up -d"
echo -e "${GREEN}  ✔ Services démarrés${NC}"
echo ""

# ── Run database migrations ────────────────────────────
echo -e "${YELLOW}[6/7]${NC} Exécution des migrations Alembic..."
$SSH_CMD "cd $REMOTE_DIR && sudo docker compose exec -T backend alembic upgrade head" || {
  echo -e "${YELLOW}  ⚠ Backend pas encore prêt, tentative via run...${NC}"
  $SSH_CMD "cd $REMOTE_DIR && sudo docker compose run --rm backend alembic upgrade head"
}
echo -e "${GREEN}  ✔ Migrations appliquées${NC}"
echo ""

# ── Restart backend (pick up migrated schema) ──────────
echo -e "${YELLOW}[7/7]${NC} Redémarrage du backend..."
$SSH_CMD "cd $REMOTE_DIR && sudo docker compose restart backend"
sleep 5

# ── Health check ───────────────────────────────────────
echo -e "${YELLOW}[✓]${NC} Vérification de santé..."
BACKEND_STATUS=$($SSH_CMD "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/docs" 2>/dev/null || echo "000")
FRONTEND_STATUS=$($SSH_CMD "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000" 2>/dev/null || echo "000")

if [ "$BACKEND_STATUS" = "200" ] && [ "$FRONTEND_STATUS" = "200" ]; then
  echo -e "${GREEN}  ✔ Backend (HTTP $BACKEND_STATUS) et Frontend (HTTP $FRONTEND_STATUS) opérationnels${NC}"
else
  echo -e "${RED}  ⚠ Problème détecté — Backend: HTTP $BACKEND_STATUS, Frontend: HTTP $FRONTEND_STATUS${NC}"
  echo -e "${YELLOW}    Consultez les logs : ssh ... 'cd $REMOTE_DIR && sudo docker compose logs -f'${NC}"
fi
echo ""

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✔ Site Central déployé sur Lightsail${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""
echo -e "  IP        : ${GREEN}http://${IP}${NC}"
echo -e "  Domaine   : ${GREEN}https://www.judi-expert.fr${NC}"
echo ""
echo -e "  ${YELLOW}SSH :${NC} ssh -i $KEY_FILE $SSH_USER@$IP"
echo -e "  ${YELLOW}Logs :${NC} ssh ... 'cd $REMOTE_DIR && sudo docker compose logs -f'"
