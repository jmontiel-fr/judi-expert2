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
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CLIENT_DIR="$PROJECT_ROOT/client-site"
OUTPUT_DIR="$SCRIPT_DIR/output"
STAGING_DIR="$SCRIPT_DIR/.staging"

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

# Read version from client-site/VERSION file (first line, extract semver only)
VERSION_FILE="$PROJECT_ROOT/client-site/VERSION"
if [ ! -f "$VERSION_FILE" ]; then
    error "Fichier VERSION introuvable : $VERSION_FILE"
fi
VERSION=$(head -n 1 "$VERSION_FILE" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
if [ -z "$VERSION" ]; then
    error "Version vide ou invalide dans $VERSION_FILE"
fi

# ── Timestamp de build (YYYYMMDD-HHmmss) ─────────────────
BUILD_TIMESTAMP=$(date +"%Y%m%d-%H%M%S")

# ── S3 bucket pour les packages prod ─────────────────────
S3_BUCKET="judi-expert-assets-eu-west-3"
S3_PREFIX="packages/client"

print_banner() {
    echo ""
    echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}${BOLD}║   Judi-Expert — Packaging des installateurs     ║${NC}"
    echo -e "${CYAN}${BOLD}║   Version : ${VERSION}  |  Mode : ${PACKAGE_MODE}              ║${NC}"
    echo -e "${CYAN}${BOLD}║   Build   : ${BUILD_TIMESTAMP}                        ║${NC}"
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
    echo "  --mode MODE     Mode de déploiement : prod | local (défaut: prod)"
    echo "                    prod  → SITE_CENTRAL_URL=https://www.judi-expert.fr"
    echo "                    local → SITE_CENTRAL_URL=http://host.docker.internal:8002"
    echo "  --version VER   Version du package (défaut: lu depuis client-site/VERSION)"
    echo "  --skip-build    Ne pas reconstruire les images Docker"
    echo "  --skip-tars     Ne pas ré-exporter les images Docker en .tar (utiliser le cache)"
    echo "  --skip-upload   Ne pas pousser vers S3 (mode prod uniquement)"
    echo "  --publish       Publier la version sur le Site Central après upload S3"
    echo "  --update-type T Type de mise à jour : images | full (défaut: images)"
    echo "  --release-notes \"TEXT\"  Notes de version (optionnel, avec --publish)"
    echo "  --help           Afficher cette aide"
    echo ""
    echo "Exemples :"
    echo "  $0                              # Tous les OS, mode prod"
    echo "  $0 --mode local windows         # Windows, communication avec site central local"
    echo "  $0 --skip-build --mode local windows  # Rapide, sans rebuild"
    echo "  $0 linux macos                  # Linux et macOS, mode prod"
    echo "  $0 --version 2.0.0 windows"
    echo ""
    echo "  # Workflow complet : build + S3 + publication"
    echo "  $0 --publish windows"
    echo "  $0 --publish --update-type full --release-notes \"Nouvelle config Docker\" windows"
    exit 0
}

# ── Parsing des arguments ─────────────────────────────────

TARGETS=()
SKIP_BUILD=false
SKIP_TARS=false
SKIP_UPLOAD=false
PUBLISH=false
UPDATE_TYPE="images"
RELEASE_NOTES=""
PACKAGE_MODE="prod"  # prod | local

while [[ $# -gt 0 ]]; do
    case "$1" in
        --version)  VERSION="$2"; shift 2 ;;
        --skip-build)  SKIP_BUILD=true; shift ;;
        --skip-tars)   SKIP_TARS=true; shift ;;
        --skip-upload) SKIP_UPLOAD=true; shift ;;
        --publish)  PUBLISH=true; shift ;;
        --update-type) UPDATE_TYPE="$2"; shift 2 ;;
        --release-notes) RELEASE_NOTES="$2"; shift 2 ;;
        --mode)     PACKAGE_MODE="$2"; shift 2 ;;
        --help)     usage ;;
        windows|macos|linux|all) TARGETS+=("$1"); shift ;;
        *) error "Argument inconnu : $1. Utilisez --help pour l'aide." ;;
    esac
done

# Valider le mode
case "$PACKAGE_MODE" in
    prod|local) ;;
    *) error "Mode invalide : $PACKAGE_MODE. Utilisez 'prod' ou 'local'." ;;
esac

# Valider update_type
case "$UPDATE_TYPE" in
    images|full) ;;
    *) error "update-type invalide : $UPDATE_TYPE. Utilisez 'images' ou 'full'." ;;
esac

# --publish n'a de sens qu'en mode prod
if [ "$PUBLISH" = true ] && [ "$PACKAGE_MODE" = "local" ]; then
    error "--publish n'est pas compatible avec --mode local. Publiez uniquement les builds prod."
fi

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
        if command -v makensis &>/dev/null; then
            MAKENSIS="makensis"
        elif [ -f "/c/Program Files (x86)/NSIS/makensis.exe" ]; then
            MAKENSIS="/c/Program Files (x86)/NSIS/makensis.exe"
        elif [ -f "/c/Program Files/NSIS/makensis.exe" ]; then
            MAKENSIS="/c/Program Files/NSIS/makensis.exe"
        else
            warn "NSIS (makensis) non trouvé. L'installateur Windows ne sera pas généré."
            warn "Installez NSIS : https://nsis.sourceforge.io/ (gratuit, open-source)"
            TARGETS=("${TARGETS[@]/windows/}")
            MAKENSIS=""
        fi
        if [ -n "${MAKENSIS:-}" ]; then
            success "NSIS trouvé : $MAKENSIS"
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
    docker compose -f "$CLIENT_DIR/docker-compose.yml" build
    success "Images Docker construites."
}

# ── Export des images Docker en fichiers tar ──────────────

DOCKER_IMAGES=(
    "client-site-judi-web-backend:latest"
    "client-site-judi-web-frontend:latest"
    "client-site-judi-ocr:latest"
    "ollama/ollama:latest"
    "qdrant/qdrant:latest"
)

# Mapping : image buildée (compose prefix) → image attendue par le compose installé
declare -A IMAGE_RENAME_MAP=(
    ["client-site-judi-web-backend:latest"]="judi-web-backend:latest"
    ["client-site-judi-web-frontend:latest"]="judi-web-frontend:latest"
    ["client-site-judi-ocr:latest"]="judi-ocr:latest"
)

export_docker_images() {
    local images_dir="$STAGING_DIR/docker-images"
    mkdir -p "$images_dir"

    if [ "$SKIP_TARS" = true ]; then
        info "Sauvegarde des images ignorée (--skip-tars)."
        return
    fi

    if [ -d "$images_dir" ] && [ "$(ls -A "$images_dir" 2>/dev/null)" ]; then
        info "Images .tar déjà présentes dans le cache, utilisation du cache."
        return
    fi

    info "Export des images Docker en fichiers tar..."

    # Re-tagger les images pour qu'elles correspondent au compose installé
    for src in "${!IMAGE_RENAME_MAP[@]}"; do
        local dst="${IMAGE_RENAME_MAP[$src]}"
        info "  Tag : ${src} → ${dst}"
        docker tag "$src" "$dst"
    done

    # Exporter les images avec les noms attendus par le compose installé
    # Note: ollama et qdrant sont pull automatiquement au premier lancement (trop gros pour NSIS)
    local EXPORT_IMAGES=(
        "judi-web-backend:latest"
        "judi-web-frontend:latest"
        "judi-ocr:latest"
    )

    for image in "${EXPORT_IMAGES[@]}"; do
        local safe_name
        safe_name=$(echo "$image" | sed 's/:latest$//' | tr '/:' '_')
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
    info "Préparation du répertoire de staging (mode: ${PACKAGE_MODE})..."

    rm -rf "$STAGING_DIR"
    mkdir -p "$STAGING_DIR"/{docker-images,config,scripts}

    # Copier le fichier .env approprié selon le mode
    if [ "$PACKAGE_MODE" = "local" ]; then
        cp "$CLIENT_DIR/.env.local" "$STAGING_DIR/config/default.env"
        info "  Mode local → .env.local copié"
    else
        cp "$CLIENT_DIR/.env.prod" "$STAGING_DIR/config/default.env"
        info "  Mode prod → .env.prod copié"
    fi

    # Copier le docker-compose.yml (version installee, sans build)
    if [ -f "$SCRIPT_DIR/common/docker-compose.installed.yml" ]; then
        cp "$SCRIPT_DIR/common/docker-compose.installed.yml" "$STAGING_DIR/config/docker-compose.yml"
    else
        cp "$CLIENT_DIR/docker-compose.yml" "$STAGING_DIR/config/docker-compose.yml"
    fi

    # Copier l'Amorce (lanceurs)
    cp "$CLIENT_DIR/amorce.sh" "$STAGING_DIR/scripts/amorce.sh"
    cp "$CLIENT_DIR/amorce.bat" "$STAGING_DIR/scripts/amorce.bat"

    # Copier le script de vérification des prérequis
    cp "$SCRIPT_DIR/common/prerequisites_check.py" "$STAGING_DIR/scripts/prerequisites_check.py"

    # Copier l'entrypoint Ollama si présent
    if [ -f "$CLIENT_DIR/ollama-entrypoint.sh" ]; then
        cp "$CLIENT_DIR/ollama-entrypoint.sh" "$STAGING_DIR/config/ollama-entrypoint.sh"
    fi

    # Écrire le fichier BUILD_INFO (embarqué dans l'installateur)
    cat > "$STAGING_DIR/config/BUILD_INFO" <<EOF
version=${VERSION}
build_timestamp=${BUILD_TIMESTAMP}
mode=${PACKAGE_MODE}
EOF

    success "Staging préparé (mode: ${PACKAGE_MODE}, build: ${BUILD_TIMESTAMP})."
}

# ── Génération de l'installateur Windows (NSIS) ──────────

build_windows_installer() {
    info "Génération de l'installateur Windows via NSIS..."

    local nsis_script="$SCRIPT_DIR/nsis/judi-expert-installer.nsi"
    if [ ! -f "$nsis_script" ]; then
        error "Script NSIS introuvable : $nsis_script"
    fi

    mkdir -p "$OUTPUT_DIR"

    "$MAKENSIS" \
        -DVERSION="$VERSION" \
        -DSTAGING_DIR="$STAGING_DIR" \
        -DOUTPUT_DIR="$OUTPUT_DIR" \
        "$nsis_script"

    local suffix=""
    if [ "$PACKAGE_MODE" = "local" ]; then
        suffix="-dev"
    fi
    local output_file="$OUTPUT_DIR/judi-expert-installer-${VERSION}${suffix}-windows.exe"
    # Rename the generated file if dev mode (NSIS generates without suffix)
    local nsis_output="$OUTPUT_DIR/judi-expert-installer-${VERSION}-windows.exe"
    if [ "$PACKAGE_MODE" = "local" ] && [ -f "$nsis_output" ]; then
        mv "$nsis_output" "$output_file"
    fi
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

# ── Upload vers S3 (mode prod uniquement) ────────────────

upload_to_s3() {
    if [ "$PACKAGE_MODE" != "prod" ]; then
        info "Mode local — pas d'upload vers S3."
        return
    fi
    if [ "$SKIP_UPLOAD" = true ]; then
        info "Upload S3 ignoré (--skip-upload)."
        return
    fi

    if ! command -v aws &>/dev/null; then
        warn "AWS CLI non trouvé — upload S3 impossible."
        warn "Installez AWS CLI et configurez 'aws configure' pour activer l'upload automatique."
        return
    fi

    info "Upload des installateurs vers s3://${S3_BUCKET}/${S3_PREFIX}/..."

    local suffix=""
    if [ "$PACKAGE_MODE" = "local" ]; then
        suffix="-dev"
    fi
    local target_file="$OUTPUT_DIR/judi-expert-installer-${VERSION}${suffix}-windows.exe"

    if [ ! -f "$target_file" ]; then
        warn "Fichier introuvable : $target_file"
        warn "Upload S3 ignoré."
        return
    fi

    local filename
    filename=$(basename "$target_file")
    info "  Upload de ${filename} ($(du -h "$target_file" | cut -f1))..."
    aws s3 cp "$target_file" "s3://${S3_BUCKET}/${S3_PREFIX}/${filename}"
    if [ $? -ne 0 ]; then
        error "Échec de l'upload vers S3. Vérifiez vos credentials AWS et que le bucket existe."
    fi
    success "  ${filename} → s3://${S3_BUCKET}/${S3_PREFIX}/${filename}"

    success "Upload S3 terminé."
}

# ── Publication de la version sur le Site Central ─────────

SITE_CENTRAL_PROD_URL="https://www.judi-expert.fr"

publish_version() {
    if [ "$PUBLISH" != true ]; then
        return
    fi

    info "Publication de la version ${VERSION} sur le Site Central..."

    # Construire l'URL de téléchargement
    local download_url="https://downloads.judi-expert.fr/judi-expert-installer-${VERSION}-windows.exe"

    # Vérifier que JUDI_ADMIN_TOKEN est défini
    if [ -z "${JUDI_ADMIN_TOKEN:-}" ]; then
        warn "Variable JUDI_ADMIN_TOKEN non définie."
        warn "Pour publier automatiquement, définissez-la :"
        warn "  export JUDI_ADMIN_TOKEN=\"votre-token-admin\""
        warn ""
        warn "Publication manuelle possible avec :"
        echo ""
        echo "  curl -X POST ${SITE_CENTRAL_PROD_URL}/api/admin/versions \\"
        echo "    -H \"Authorization: Bearer \$JUDI_ADMIN_TOKEN\" \\"
        echo "    -H \"Content-Type: application/json\" \\"
        echo "    -d '{\"version\":\"${VERSION}\",\"download_url\":\"${download_url}\",\"update_type\":\"${UPDATE_TYPE}\",\"mandatory\":true,\"release_notes\":\"${RELEASE_NOTES}\"}'"
        echo ""
        return
    fi

    # Construire le body JSON
    local json_body
    if [ -n "$RELEASE_NOTES" ]; then
        json_body=$(printf '{"version":"%s","download_url":"%s","update_type":"%s","mandatory":true,"release_notes":"%s"}' \
            "$VERSION" "$download_url" "$UPDATE_TYPE" "$RELEASE_NOTES")
    else
        json_body=$(printf '{"version":"%s","download_url":"%s","update_type":"%s","mandatory":true}' \
            "$VERSION" "$download_url" "$UPDATE_TYPE")
    fi

    # Appel API
    local http_code
    http_code=$(curl -s -o /tmp/judi-publish-response.json -w "%{http_code}" \
        -X POST "${SITE_CENTRAL_PROD_URL}/api/admin/versions" \
        -H "Authorization: Bearer ${JUDI_ADMIN_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "$json_body")

    if [ "$http_code" = "201" ]; then
        success "Version ${VERSION} publiée sur le Site Central (update_type=${UPDATE_TYPE})"
        if [ -n "$RELEASE_NOTES" ]; then
            info "  Notes : ${RELEASE_NOTES}"
        fi
    else
        warn "Échec de la publication (HTTP ${http_code})."
        warn "Réponse : $(cat /tmp/judi-publish-response.json 2>/dev/null)"
        warn ""
        warn "Publiez manuellement via le tableau de bord admin ou la commande curl ci-dessus."
    fi
    rm -f /tmp/judi-publish-response.json
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

    upload_to_s3
    publish_version
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
