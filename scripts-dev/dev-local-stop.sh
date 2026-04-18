#!/bin/bash
set -e
# Usage : bash scripts-dev/dev-local-stop.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE="$ROOT_DIR/local-site/docker-compose.yml"
source "$SCRIPT_DIR/_common.sh"
parse_args "dev-local-stop.sh" \
  "Arrêter l'Application Locale et libérer les ports (3000, 8000, 8001, 11434, 6333)" \
  "" "" "$@"

PORTS=(3000 8000 8001 11434 6333)

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert Local — Arrêt${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}[1/2] Docker...${NC}"
ensure_docker
echo ""
echo -e "${YELLOW}[2/2] Arrêt des services...${NC}"
docker compose -f "$COMPOSE" down --remove-orphans || true
free_ports "${PORTS[@]}"
echo -e "${GREEN}  ✔ Application Locale arrêtée${NC}"
