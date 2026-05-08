#!/bin/bash
set -e
# Usage : bash scripts-dev/dev-central-restart.sh [--build]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE="$ROOT_DIR/central-site/docker-compose.dev.yml"
source "$SCRIPT_DIR/_common.sh"
parse_args "dev-central-restart.sh" \
  "Redémarrer le Site Central (arrêt + libération ports + démarrage)" \
  "yes" "" "$@"

PORTS=(3001 8002 5433)

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert Central — Redémarrage${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}[1/4] Docker...${NC}"
ensure_docker
echo ""
echo -e "${YELLOW}[2/4] Arrêt...${NC}"
docker compose -f "$COMPOSE" --env-file "$ROOT_DIR/central-site/.env.dev" down --remove-orphans || true
echo -e "${GREEN}  ✔ Arrêté${NC}"
echo ""
echo -e "${YELLOW}[3/4] Libération des ports...${NC}"
free_ports "${PORTS[@]}"
echo -e "${GREEN}  ✔ Ports libres${NC}"
echo ""
echo -e "${YELLOW}[4/4] Démarrage${BUILD_FLAG:+ + build}...${NC}"
ENV_FILE="$ROOT_DIR/central-site/.env.dev"
if [ -f "$ENV_FILE" ]; then
  docker compose -f "$COMPOSE" --env-file "$ENV_FILE" up -d $BUILD_FLAG
else
  docker compose -f "$COMPOSE" up -d $BUILD_FLAG
fi
echo ""
echo -e "${GREEN}  ✔ Site Central redémarré${NC}"
echo -e "  Frontend   : ${GREEN}http://localhost:3001${NC}"
echo -e "  Backend    : ${GREEN}http://localhost:8002/docs${NC}"
echo -e "  PostgreSQL : ${GREEN}localhost:5433${NC}"
