#!/bin/bash
set -e
# Usage : bash scripts-dev/dev-central-stop.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE="$ROOT_DIR/central-site/docker-compose.dev.yml"
source "$SCRIPT_DIR/_common.sh"
parse_args "dev-central-stop.sh" \
  "Arrêter le Site Central et libérer les ports (3001, 8002, 5433)" \
  "" "" "$@"

PORTS=(3001 8002 5433)

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert Central — Arrêt${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}[1/2] Docker...${NC}"
ensure_docker
echo ""
echo -e "${YELLOW}[2/2] Arrêt des services...${NC}"
docker compose -f "$COMPOSE" down --remove-orphans || true
free_ports "${PORTS[@]}"
echo -e "${GREEN}  ✔ Site Central arrêté${NC}"
