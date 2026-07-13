#!/bin/bash
set -euo pipefail

# ─────────────────────────────────────────────────────────
# publish-client-package.sh — Build, upload et publication
# du package Site Client en une seule commande.
#
# Usage :
#   bash scripts-dev/publish-client-package.sh [OPTIONS]
#
# Options :
#   --update-type TYPE   images | full (défaut: images)
#   --release-notes "…"  Notes de version (optionnel)
#   --skip-build         Ne pas reconstruire les images Docker
#   --skip-export        Ne pas ré-exporter les images
#   --mode MODE          prod | local (défaut: prod)
#   --help               Afficher cette aide
#
# Le script :
#   1. Se connecte au Site Central (admin) pour obtenir un token
#   2. Génère le package (package.sh)
#   3. Upload sur S3
#   4. Publie la version sur le Site Central
#
# Prérequis :
#   - AWS CLI configuré (aws configure)
#   - NSIS installé (pour Windows)
#   - Site Central accessible (prod ou local selon --mode)
# ─────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PACKAGE_SCRIPT="$PROJECT_ROOT/central-site/app_client_package/package.sh"

# ── Couleurs ──────────────────────────────────────────────
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${BLUE}ℹ ${NC} $1"; }
success() { echo -e "${GREEN}✔ ${NC} $1"; }
warn()    { echo -e "${YELLOW}⚠ ${NC} $1"; }
error()   { echo -e "${RED}✖ ${NC} $1"; exit 1; }

# ── Valeurs par défaut ────────────────────────────────────
UPDATE_TYPE="images"
RELEASE_NOTES=""
PACKAGE_MODE="prod"
EXTRA_ARGS=()

# ── Configuration des URLs ────────────────────────────────
CENTRAL_URL_PROD="https://www.judi-expert.fr"
CENTRAL_URL_LOCAL="http://localhost:8002"

# ── Credentials admin (par défaut, configurable via .env.publish) ──
ADMIN_EMAIL="${JUDI_ADMIN_EMAIL:-admin@judi-expert.fr}"
ADMIN_PASSWORD="${JUDI_ADMIN_PASSWORD:-}"

# Charger les credentials depuis un fichier local si présent
ENV_FILE="$PROJECT_ROOT/.env.publish"
if [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE"
fi

# ── Parsing des arguments ─────────────────────────────────

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Build, upload et publie le package Site Client."
    echo ""
    echo "Options :"
    echo "  --update-type TYPE   images | full (défaut: images)"
    echo "  --release-notes \"…\"  Notes de version"
    echo "  --skip-build         Ne pas reconstruire les images"
    echo "  --skip-export        Ne pas ré-exporter les images"
    echo "  --mode MODE          prod | local (défaut: prod)"
    echo "  --help               Afficher cette aide"
    echo ""
    echo "Credentials admin :"
    echo "  Méthode 1 : fichier .env.publish à la racine du repo :"
    echo "    JUDI_ADMIN_EMAIL=admin@judi-expert.fr"
    echo "    JUDI_ADMIN_PASSWORD=votre-mot-de-passe"
    echo ""
    echo "  Méthode 2 : variables d'environnement :"
    echo "    export JUDI_ADMIN_EMAIL=admin@judi-expert.fr"
    echo "    export JUDI_ADMIN_PASSWORD=votre-mot-de-passe"
    echo ""
    echo "  Méthode 3 : le script demande le mot de passe interactivement"
    echo ""
    echo "Exemples :"
    echo "  $0                                    # Build + publish (images)"
    echo "  $0 --update-type full                 # Réinstallation complète"
    echo "  $0 --update-type full --release-notes \"Nouvelle config Docker\""
    echo "  $0 --mode local                       # Test en local"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --update-type)   UPDATE_TYPE="$2"; shift 2 ;;
        --release-notes) RELEASE_NOTES="$2"; shift 2 ;;
        --skip-build)    EXTRA_ARGS+=("--skip-build"); shift ;;
        --skip-export)   EXTRA_ARGS+=("--skip-export"); shift ;;
        --mode)          PACKAGE_MODE="$2"; shift 2 ;;
        --help)          usage ;;
        *) error "Argument inconnu : $1. Utilisez --help." ;;
    esac
done

# ── Déterminer l'URL du Site Central ──────────────────────
if [ "$PACKAGE_MODE" = "local" ]; then
    CENTRAL_URL="$CENTRAL_URL_LOCAL"
else
    CENTRAL_URL="$CENTRAL_URL_PROD"
fi

echo ""
echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}${BOLD}║  Judi-Expert — Publication package Site Client   ║${NC}"
echo -e "${CYAN}${BOLD}║  Mode : ${PACKAGE_MODE}  |  Update type : ${UPDATE_TYPE}          ║${NC}"
echo -e "${CYAN}${BOLD}║  Central : ${CENTRAL_URL}${NC}"
echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# ── Étape 1 : Obtenir le token admin ─────────────────────

info "Étape 1/3 : Authentification admin sur le Site Central..."

if [ -z "$ADMIN_PASSWORD" ]; then
    echo -n "  Mot de passe admin ($ADMIN_EMAIL) : "
    read -s ADMIN_PASSWORD
    echo ""
fi

# Login pour obtenir le token
LOGIN_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST "${CENTRAL_URL}/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\",\"captcha_token\":\"dev-bypass\"}")

HTTP_CODE=$(echo "$LOGIN_RESPONSE" | tail -1)
BODY=$(echo "$LOGIN_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" != "200" ]; then
    error "Échec de l'authentification (HTTP ${HTTP_CODE}). Vérifiez email/password."
fi

JUDI_ADMIN_TOKEN=$(echo "$BODY" | jq -r '.access_token' 2>/dev/null)
if [ -z "$JUDI_ADMIN_TOKEN" ] || [ "$JUDI_ADMIN_TOKEN" = "null" ]; then
    # Fallback: try python/python3
    JUDI_ADMIN_TOKEN=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || \
                       echo "$BODY" | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)
fi
if [ -z "$JUDI_ADMIN_TOKEN" ] || [ "$JUDI_ADMIN_TOKEN" = "null" ]; then
    error "Impossible d'extraire le token de la réponse. Body: $BODY"
fi

export JUDI_ADMIN_TOKEN
success "Authentification réussie."

# ── Étape 2 : Générer et uploader le package ─────────────

info "Étape 2/3 : Génération du package..."
echo ""

bash "$PACKAGE_SCRIPT" \
    --mode "$PACKAGE_MODE" \
    --publish \
    --update-type "$UPDATE_TYPE" \
    ${RELEASE_NOTES:+--release-notes "$RELEASE_NOTES"} \
    "${EXTRA_ARGS[@]}" \
    windows

# ── Étape 3 : Résumé ─────────────────────────────────────

echo ""
echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  Publication terminée !${NC}"
echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════${NC}"
echo ""
echo -e "  Mode        : ${PACKAGE_MODE}"
echo -e "  Update type : ${UPDATE_TYPE}"
echo -e "  Central     : ${CENTRAL_URL}"
if [ -n "$RELEASE_NOTES" ]; then
    echo -e "  Notes       : ${RELEASE_NOTES}"
fi
echo ""
