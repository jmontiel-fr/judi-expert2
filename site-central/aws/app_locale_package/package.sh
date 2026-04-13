#!/bin/bash
set -euo pipefail

# ─────────────────────────────────────────────────────────
# package.sh — Script principal de packaging Judi-Expert
# Produit un installateur autonome par OS cible :
#   - Windows : installateur NSIS (.exe)
#   - macOS   : script shell auto-extractible (.sh)
#   - Linux   : script shell auto-extractible (.sh)
#
# Utilise uniquement des outils gratuits et open-source
# compatibles avec un usage commercial.
#
# Exigences : 31.1, 31.2, 31.3, 31.6
# ─────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
LOCAL_DIR="$PROJECT_ROOT/site-central/local"
OUTPUT_DIR="$SCRIPT_DIR/output"
STAGING_DIR="$SCRIPT_DIR/.staging"
VERSION="${JUDI_VERSION:-1.0.0}"

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

print_banner() {
    echo ""
    echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}${BOLD}║   Judi-Expert — Packaging des installateurs     ║${NC}"
    echo -e "${CYAN}${BOLD}║   Version : ${VERSION}                                ║${NC}"
    echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════╝${NC}"
    echo ""
}

usage() {
    echo "Usage: $0 [OPTIONS] [CIBLE...]"
    echo ""
    echo "Cibles disponibles :"
    echo "  windows    Génère l'installateur Windows (.exe) via NSIS"
    echo "  macos      Génère l'installateur macOS (.sh auto-extractible)"
    echo "  linux      Génère l'installateur Linux (.sh auto-extractible)"
    echo "  all        Génère les installateurs pour tous les OS (défaut)"
    echo ""
    echo "Options :"
    echo "  --version VER   Version du package (défaut: 1.0.0)"
    echo "  --skip-build    Ne pas reconstruire les images Docker"
    echo "  --skip-export   Ne pas ré-exporter les images Docker (utiliser le cache)"
    echo "  --help           Afficher cette aide"
    echo ""
    echo "Exemples :"
    echo "  $0                    # Tous les OS"
    echo "  $0 linux macos        # Linux et macOS uniquement"
    echo "  $0 --version 2.0.0 windows"
    exit 0
}

# ── Parsing des arguments ─────────────────────────────────

TARGETS=()
SKIP_BUILD=false
SKIP_EXPORT=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --version)  VERSION="$2"; shift 2 ;;
        --skip-build)  SKIP_BUILD=true; shift ;;
        --skip-export) SKIP_EXPORT=true; shift ;;
        --help)     usage ;;
        windows|macos|linux|all) TARGETS+=("$1"); shift ;;
        *) error "Argument inconnu : $1. Utilisez --help pour l'aide." ;;
    esac
done

# Défaut : tous les OS
if [ ${#TARGETS[@]} -eq 0 ] || [[ " ${TARGETS[*]} " == *" all "* ]]; then
    TARGETS=(windows macos linux)
fi

# ── Vérification des prérequis de build ───────────────────

check_build_prerequisites() {
    info "Vérification des prérequis de build..."

    if ! command -v docker &>/dev/null; then
        error "Docker est requis pour le packaging. Installez Docker et réessayez."
    fi

    if ! docker info &>/dev/null; then
        error "Le daemon Docker n'est pas en cours d'exécution. Démarrez Docker et réessayez."
    fi

    # Vérifier NSIS si Windows est ciblé
    if [[ " ${TARGETS[*]} " == *" windows "* ]]; then
        if ! command -v makensis &>/dev/null; then
            warn "NSIS (makensis) non trouvé. L'installateur Windows ne sera pas généré."
            warn "Installez NSIS : https://nsis.sourceforge.io/ (gratuit, open-source)"
            TARGETS=("${TARGETS[@]/windows/}")
        fi
    fi

    success "Prérequis de build vérifiés."
}

# ── Construction des images Docker ────────────────────────

build_docker_images() {
    if [ "$SKIP_BUILD" = true ]; then
        info "Construction des images ignorée (--skip-build)."
        return
    fi

    info "Construction des images Docker locales..."
    bash "$LOCAL_DIR/scripts/build.sh"
    success "Images Docker construites."
}

# ── Export des images Docker en fichiers tar ──────────────

DOCKER_IMAGES=(
    "judi-web-backend"
    "judi-web-frontend"
    "judi-ocr"
    "ollama/ollama:latest"
    "qdrant/qdrant:latest"
)

export_docker_images() {
    local images_dir="$STAGING_DIR/docker-images"
    mkdir -p "$images_dir"

    if [ "$SKIP_EXPORT" = true ] && [ -d "$images_dir" ] && [ "$(ls -A "$images_dir" 2>/dev/null)" ]; then
        info "Export des images ignoré (--skip-export, cache existant)."
        return
    fi

    info "Export des images Docker en fichiers tar..."

    for image in "${DOCKER_IMAGES[@]}"; do
        local safe_name
        safe_name=$(echo "$image" | tr '/:' '_')
        local tar_file="$images_dir/${safe_name}.tar"

        info "  Export de ${image}..."
        if ! docker image inspect "$image" &>/dev/null; then
            warn "  Image ${image} non trouvée localement, tentative de pull..."
            docker pull "$image"
        fi
        docker save -o "$tar_file" "$image"
        success "  ${image} → ${safe_name}.tar"
    done

    success "Toutes les images Docker exportées."
}

# ── Préparation du répertoire de staging ──────────────────

prepare_staging() {
    info "Préparation du répertoire de staging..."

    rm -rf "$STAGING_DIR"
    mkdir -p "$STAGING_DIR"/{docker-images,config,scripts}

    # Copier les fichiers de configuration par défaut
    cp "$LOCAL_DIR/.env" "$STAGING_DIR/config/default.env"
    cp "$SCRIPT_DIR/common/default.env" "$STAGING_DIR/config/default.env" 2>/dev/null || true

    # Copier le docker-compose.yml (version installee, sans build)
    if [ -f "$SCRIPT_DIR/common/docker-compose.installed.yml" ]; then
        cp "$SCRIPT_DIR/common/docker-compose.installed.yml" "$STAGING_DIR/config/docker-compose.yml"
    else
        cp "$LOCAL_DIR/docker-compose.yml" "$STAGING_DIR/config/docker-compose.yml"
    fi

    # Copier l'Amorce (lanceurs)
    cp "$LOCAL_DIR/amorce.sh" "$STAGING_DIR/scripts/amorce.sh"
    cp "$LOCAL_DIR/amorce.bat" "$STAGING_DIR/scripts/amorce.bat"

    # Copier le script de vérification des prérequis
    cp "$SCRIPT_DIR/common/prerequisites_check.py" "$STAGING_DIR/scripts/prerequisites_check.py"

    # Copier l'entrypoint Ollama si présent
    if [ -f "$LOCAL_DIR/ollama-entrypoint.sh" ]; then
        cp "$LOCAL_DIR/ollama-entrypoint.sh" "$STAGING_DIR/config/ollama-entrypoint.sh"
    fi

    success "Staging préparé."
}

# ── Génération de l'installateur Windows (NSIS) ──────────

build_windows_installer() {
    info "Génération de l'installateur Windows via NSIS..."

    local nsis_script="$SCRIPT_DIR/nsis/judi-expert-installer.nsi"
    if [ ! -f "$nsis_script" ]; then
        error "Script NSIS introuvable : $nsis_script"
    fi

    mkdir -p "$OUTPUT_DIR"

    makensis \
        -DVERSION="$VERSION" \
        -DSTAGING_DIR="$STAGING_DIR" \
        -DOUTPUT_DIR="$OUTPUT_DIR" \
        "$nsis_script"

    local output_file="$OUTPUT_DIR/judi-expert-installer-${VERSION}-windows.exe"
    if [ -f "$output_file" ]; then
        success "Installateur Windows généré : $output_file"
    else
        # NSIS peut nommer le fichier différemment
        success "Installateur Windows généré dans : $OUTPUT_DIR/"
    fi
}

# ── Génération de l'installateur Unix (macOS/Linux) ──────

build_unix_installer() {
    local os_target="$1"
    info "Génération de l'installateur ${os_target}..."

    local install_script="$SCRIPT_DIR/unix/install.sh"
    if [ ! -f "$install_script" ]; then
        error "Script d'installation Unix introuvable : $install_script"
    fi

    mkdir -p "$OUTPUT_DIR"

    local output_file="$OUTPUT_DIR/judi-expert-installer-${VERSION}-${os_target}.sh"

    # Créer l'archive tar.gz du staging
    local payload_file
    payload_file=$(mktemp)
    tar -czf "$payload_file" -C "$STAGING_DIR" .

    # Construire le script auto-extractible :
    # 1. Script d'installation (header)
    # 2. Marqueur de séparation
    # 3. Archive tar.gz (payload)
    {
        # Injecter la version et l'OS cible dans le script
        sed \
            -e "s|__JUDI_VERSION__|${VERSION}|g" \
            -e "s|__JUDI_OS_TARGET__|${os_target}|g" \
            "$install_script"
        echo ""
        echo "__PAYLOAD_BELOW__"
    } > "$output_file"

    cat "$payload_file" >> "$output_file"
    chmod +x "$output_file"

    rm -f "$payload_file"

    local size
    size=$(du -h "$output_file" | cut -f1)
    success "Installateur ${os_target} généré : $output_file (${size})"
}

# ── Nettoyage ─────────────────────────────────────────────

cleanup() {
    info "Nettoyage du répertoire de staging..."
    rm -rf "$STAGING_DIR"
    success "Nettoyage terminé."
}

# ── Main ──────────────────────────────────────────────────

main() {
    print_banner

    check_build_prerequisites
    build_docker_images
    prepare_staging
    export_docker_images

    echo ""
    info "Génération des installateurs pour : ${TARGETS[*]}"
    echo ""

    for target in "${TARGETS[@]}"; do
        case "$target" in
            windows) build_windows_installer ;;
            macos)   build_unix_installer "macos" ;;
            linux)   build_unix_installer "linux" ;;
        esac
    done

    cleanup

    echo ""
    echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}${BOLD}  Packaging terminé avec succès !${NC}"
    echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  Installateurs disponibles dans : ${CYAN}${OUTPUT_DIR}/${NC}"
    echo ""
    ls -lh "$OUTPUT_DIR"/ 2>/dev/null || true
    echo ""
}

main "$@"
