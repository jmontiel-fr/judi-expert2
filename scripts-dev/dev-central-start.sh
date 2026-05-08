#!/bin/bash
set -e
# Usage : bash scripts-dev/dev-central-start.sh [--build]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE="$ROOT_DIR/central-site/docker-compose.dev.yml"
source "$SCRIPT_DIR/_common.sh"
parse_args "dev-central-start.sh" \
  "Démarrer le Site Central (3 conteneurs : PostgreSQL, backend FastAPI, frontend Next.js)" \
  "yes" "" "$@"

PORTS=(3001 8002 5433)

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert Central — Démarrage${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}[1/3] Docker...${NC}"
ensure_docker
echo ""
echo -e "${YELLOW}[2/3] Libération des ports...${NC}"
free_ports "${PORTS[@]}"
echo -e "${GREEN}  ✔ Ports libres${NC}"
echo ""
echo -e "${YELLOW}[3/3] Démarrage${BUILD_FLAG:+ + build}...${NC}"
ENV_FILE="$ROOT_DIR/central-site/.env.dev"
if [ -f "$ENV_FILE" ]; then
  docker compose -f "$COMPOSE" --env-file "$ENV_FILE" up -d $BUILD_FLAG
else
  docker compose -f "$COMPOSE" up -d $BUILD_FLAG
fi
echo ""
echo -e "${GREEN}  ✔ Site Central démarré${NC}"
echo -e "  Frontend   : ${GREEN}http://localhost:3001${NC}"
echo -e "  Backend    : ${GREEN}http://localhost:8002/docs${NC}"
echo -e "  PostgreSQL : ${GREEN}localhost:5433${NC}"
