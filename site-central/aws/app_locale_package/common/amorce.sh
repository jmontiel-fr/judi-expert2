#!/bin/bash
# ─────────────────────────────────────────────────────────
# amorce.sh — Lanceur Amorce pour l'Application Locale
# Copie embarquée dans l'installateur.
#
# Vérifie Docker, démarre le daemon si nécessaire, lance
# les conteneurs et ouvre le navigateur.
#
# Exigences : 1.4, 1.5, 2.2, 31.2
# ─────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$INSTALL_DIR/config/docker-compose.yml"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

DOCKER_READY_TIMEOUT=60
FRONTEND_READY_TIMEOUT=180
FRONTEND_URL="http://localhost:3000"

info()    { echo -e "${BLUE}ℹ ${NC} $1"; }
success() { echo -e "${GREEN}✔ ${NC} $1"; }
warn()    { echo -e "${YELLOW}⚠ ${NC} $1"; }
error()   { echo -e "${RED}✖ ${NC} $1"; exit 1; }

detect_os() {
    case "$(uname -s)" in
        Linux*)  echo "linux"  ;;
        Darwin*) echo "macos"  ;;
        *)       echo "unknown" ;;
    esac
}

print_banner() {
    echo ""
    echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}${BOLD}║        Judi-Expert — Amorce / Lanceur        ║${NC}"
    echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════╝${NC}"
    echo ""
}

check_docker_installed() {
    info "Vérification de l'installation de Docker..."
    if ! command -v docker &>/dev/null; then
        error "Docker n'est pas installé. Veuillez réinstaller Judi-Expert."
    fi
    success "Docker est installé ($(docker --version))"
}

check_docker_running() {
    if docker info &>/dev/null; then
        success "Le daemon Docker est en cours d'exécution."
        return 0
    fi
    return 1
}

start_docker_daemon() {
    local os
    os="$(detect_os)"
    warn "Le daemon Docker n'est pas en cours d'exécution."
    info "Tentative de démarrage automatique..."

    case "$os" in
        linux)
            if command -v systemctl &>/dev/null; then
                sudo systemctl start docker 2>/dev/null || true
            elif command -v service &>/dev/null; then
                sudo service docker start 2>/dev/null || true
            fi
            ;;
        macos)
            open -a Docker 2>/dev/null || true
            ;;
    esac
}

wait_for_docker() {
    info "Attente du daemon Docker (timeout : ${DOCKER_READY_TIMEOUT}s)..."
    local elapsed=0
    while [ $elapsed -lt $DOCKER_READY_TIMEOUT ]; do
        if docker info &>/dev/null; then
            success "Le daemon Docker est prêt."
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    error "Le daemon Docker n'a pas démarré. Veuillez le démarrer manuellement."
}

launch_containers() {
    info "Lancement des conteneurs via docker compose..."
    if ! docker compose -f "$COMPOSE_FILE" up -d; then
        error "Échec du lancement des conteneurs."
    fi
    success "Tous les conteneurs sont lancés."
}

wait_for_frontend() {
    info "Attente du frontend (timeout : ${FRONTEND_READY_TIMEOUT}s)..."
    local elapsed=0
    while [ $elapsed -lt $FRONTEND_READY_TIMEOUT ]; do
        if command -v curl &>/dev/null && curl -sf "$FRONTEND_URL" &>/dev/null; then
            success "Le frontend est prêt sur ${FRONTEND_URL}"
            return 0
        fi
        sleep 3
        elapsed=$((elapsed + 3))
    done
    warn "Le frontend n'a pas répondu dans le délai imparti."
    info "Vérifiez manuellement : ${FRONTEND_URL}"
}

open_browser() {
    local os
    os="$(detect_os)"
    case "$os" in
        linux)  xdg-open "$FRONTEND_URL" 2>/dev/null & ;;
        macos)  open "$FRONTEND_URL" 2>/dev/null & ;;
    esac
}

main() {
    print_banner
    check_docker_installed
    if ! check_docker_running; then
        start_docker_daemon
        wait_for_docker
    fi
    launch_containers
    wait_for_frontend
    open_browser

    echo ""
    echo -e "${GREEN}${BOLD}  Judi-Expert est prêt !${NC}"
    echo -e "  Application : ${CYAN}${FRONTEND_URL}${NC}"
    echo ""
}

main "$@"
