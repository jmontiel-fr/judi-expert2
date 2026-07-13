#!/bin/bash
set -e
# Usage : bash scripts-dev/dev-client-stop.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE="$ROOT_DIR/client-site/docker-compose.yml"
source "$SCRIPT_DIR/_common.sh"
parse_args "dev-client-stop.sh" \
  "Arrêter le Site Client et libérer les ports (3000, 8000, 8001, 11434, 6333)" \
  "" "" "$@"

PORTS=(3000 8000 8001 11434 6333)

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert Client — Arrêt${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}[1/2] Docker...${NC}"
ensure_docker
echo ""
echo -e "${YELLOW}[2/2] Arrêt des services...${NC}"
docker compose -f "$COMPOSE" down --remove-orphans || true
free_ports "${PORTS[@]}"
echo -e "${GREEN}  ✔ Site Client arrêté${NC}"
