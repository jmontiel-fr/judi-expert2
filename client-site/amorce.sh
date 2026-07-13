#!/bin/bash
# ─────────────────────────────────────────────────────────
# amorce.sh — Lanceur de l'Application Locale Judi-Expert
# Vérifie Docker, démarre le daemon si nécessaire, lance
# les conteneurs et ouvre le navigateur.
# Exigences : 1.4, 1.5, 2.2
# ─────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"

# ── Couleurs ──────────────────────────────────────────────
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

DOCKER_READY_TIMEOUT=60   # secondes
FRONTEND_READY_TIMEOUT=180 # secondes
FRONTEND_URL="http://localhost:3000"

# ── Fonctions utilitaires ─────────────────────────────────

print_banner() {
    echo ""
    echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}${BOLD}║        Judi-Expert — Amorce / Lanceur        ║${NC}"
    echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════╝${NC}"
    echo ""
}

info()    { echo -e "${BLUE}ℹ ${NC} $1"; }
success() { echo -e "${GREEN}✔ ${NC} $1"; }
warn()    { echo -e "${YELLOW}⚠ ${NC} $1"; }
error()   { echo -e "${RED}✖ ${NC} $1"; }

detect_os() {
    case "$(uname -s)" in
        Linux*)  echo "linux"  ;;
        Darwin*) echo "macos"  ;;
        *)       echo "unknown" ;;
    esac
}

# ── Étape 1 : Vérifier que Docker est installé ───────────

check_docker_installed() {
    info "Vérification de l'installation de Docker..."
    if ! command -v docker &>/dev/null; then
        error "Docker n'est pas installé ou n'est pas dans le PATH."
        echo ""
        echo -e "  Veuillez installer Docker Desktop depuis :"
        echo -e "    ${CYAN}https://www.docker.com/products/docker-desktop${NC}"
        echo ""
        exit 1
    fi
    success "Docker est installé ($(docker --version))"
}

# ── Étape 2 : Vérifier / démarrer le daemon Docker ───────

check_docker_running() {
    info "Vérification du daemon Docker..."
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
                info "Démarrage via systemctl..."
                sudo systemctl start docker 2>/dev/null || true
            elif command -v service &>/dev/null; then
                info "Démarrage via service..."
                sudo service docker start 2>/dev/null || true
            else
                error "Impossible de démarrer Docker automatiquement."
                echo "  Veuillez démarrer Docker manuellement et relancer ce script."
                exit 1
            fi
            ;;
        macos)
            info "Ouverture de Docker Desktop..."
            open -a Docker 2>/dev/null || true
            ;;
        *)
            error "Système d'exploitation non reconnu. Veuillez démarrer Docker manuellement."
            exit 1
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
        printf "\r  ${YELLOW}⏳ Attente... %ds / %ds${NC}" "$elapsed" "$DOCKER_READY_TIMEOUT"
    done
    echo ""
    error "Le daemon Docker n'a pas démarré dans le délai imparti (${DOCKER_READY_TIMEOUT}s)."
    echo "  Veuillez démarrer Docker manuellement et relancer ce script."
    exit 1
}

# ── Étape 3 : Lancer docker compose ──────────────────────

launch_containers() {
    info "Lancement des conteneurs via docker compose..."
    echo ""
    if ! docker compose -f "$COMPOSE_FILE" up -d; then
        error "Échec du lancement des conteneurs."
        echo "  Consultez les logs avec : docker compose -f \"$COMPOSE_FILE\" logs"
        exit 1
    fi
    echo ""
    success "Tous les conteneurs sont lancés."
}

# ── Étape 4 : Attendre que le frontend soit prêt ─────────

wait_for_frontend() {
    info "Attente du frontend judi-web-frontend (timeout : ${FRONTEND_READY_TIMEOUT}s)..."
    local elapsed=0
    while [ $elapsed -lt $FRONTEND_READY_TIMEOUT ]; do
        # Check via curl if available, otherwise via docker inspect
        if command -v curl &>/dev/null; then
            if curl -sf "$FRONTEND_URL" &>/dev/null; then
                echo ""
                success "Le frontend est prêt sur ${FRONTEND_URL}"
                return 0
            fi
        else
            local state
            state=$(docker inspect --format='{{.State.Health.Status}}' judi-web-frontend 2>/dev/null || echo "unknown")
            if [ "$state" = "healthy" ]; then
                echo ""
                success "Le conteneur frontend est healthy."
                return 0
            fi
        fi
        sleep 3
        elapsed=$((elapsed + 3))
        printf "\r  ${YELLOW}⏳ Attente du frontend... %ds / %ds${NC}" "$elapsed" "$FRONTEND_READY_TIMEOUT"
    done
    echo ""
    warn "Le frontend n'a pas répondu dans le délai imparti."
    warn "Les conteneurs sont démarrés mais le frontend peut encore être en cours de chargement."
    info "Vous pouvez vérifier manuellement : ${CYAN}${FRONTEND_URL}${NC}"
}

# ── Étape 5 : Ouvrir le navigateur ───────────────────────

open_browser() {
    info "Ouverture du navigateur..."
    local os
    os="$(detect_os)"

    case "$os" in
        linux)
            if command -v xdg-open &>/dev/null; then
                xdg-open "$FRONTEND_URL" 2>/dev/null &
            elif command -v sensible-browser &>/dev/null; then
                sensible-browser "$FRONTEND_URL" 2>/dev/null &
            else
                warn "Impossible d'ouvrir le navigateur automatiquement."
                info "Ouvrez manuellement : ${CYAN}${FRONTEND_URL}${NC}"
                return
            fi
            ;;
        macos)
            open "$FRONTEND_URL" 2>/dev/null &
            ;;
        *)
            warn "Impossible d'ouvrir le navigateur automatiquement."
            info "Ouvrez manuellement : ${CYAN}${FRONTEND_URL}${NC}"
            return
            ;;
    esac
    success "Navigateur ouvert sur ${FRONTEND_URL}"
}

# ── Résumé final ──────────────────────────────────────────

print_summary() {
    echo ""
    echo -e "${BLUE}══════════════════════════════════════════════${NC}"
    echo -e "${GREEN}${BOLD}  Judi-Expert est prêt !${NC}"
    echo -e "${BLUE}══════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${BOLD}Services disponibles :${NC}"
    echo -e "    • Frontend  : ${CYAN}http://localhost:3000${NC}"
    echo -e "    • Backend   : ${CYAN}http://localhost:8000${NC}"
    echo -e "    • LLM       : ${CYAN}http://localhost:11434${NC}"
    echo -e "    • RAG       : ${CYAN}http://localhost:6333${NC}"
    echo -e "    • OCR       : ${CYAN}http://localhost:8001${NC}"
    echo ""
    echo -e "  ${BOLD}Commandes utiles :${NC}"
    echo -e "    Arrêter  : ${YELLOW}docker compose -f \"$COMPOSE_FILE\" down${NC}"
    echo -e "    Logs     : ${YELLOW}docker compose -f \"$COMPOSE_FILE\" logs -f${NC}"
    echo -e "    Statut   : ${YELLOW}docker compose -f \"$COMPOSE_FILE\" ps${NC}"
    echo ""
}

# ── Main ──────────────────────────────────────────────────

main() {
    print_banner

    # 1. Vérifier Docker installé
    check_docker_installed

    # 2. Vérifier / démarrer le daemon
    if ! check_docker_running; then
        start_docker_daemon
        wait_for_docker
    fi

    # 3. Lancer les conteneurs
    launch_containers

    # 4. Attendre le frontend
    wait_for_frontend

    # 5. Ouvrir le navigateur
    open_browser

    # 6. Résumé
    print_summary
}

main "$@"
