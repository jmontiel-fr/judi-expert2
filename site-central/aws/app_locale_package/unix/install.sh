#!/bin/bash
# ─────────────────────────────────────────────────────────
# install.sh — Installateur auto-extractible Judi-Expert
# Script shell pour macOS et Linux.
#
# Ce script est concaténé avec une archive tar.gz pour
# former un installateur autonome auto-extractible.
#
# Gratuit et open-source, compatible usage commercial.
#
# Exigences : 31.1, 31.2, 31.3, 31.4, 31.5, 31.6, 1.1, 1.2, 1.3
# ─────────────────────────────────────────────────────────

set -euo pipefail

JUDI_VERSION="__JUDI_VERSION__"
JUDI_OS_TARGET="__JUDI_OS_TARGET__"
INSTALL_DIR="${JUDI_INSTALL_DIR:-$HOME/judi-expert}"
TEMP_DIR=$(mktemp -d)

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
fail()    { echo -e "${RED}✖ ${NC} $1"; cleanup; exit 1; }

cleanup() {
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

print_banner() {
    echo ""
    echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}${BOLD}║   Judi-Expert — Installation ${JUDI_OS_TARGET}              ║${NC}"
    echo -e "${CYAN}${BOLD}║   Version : ${JUDI_VERSION}                                ║${NC}"
    echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ── Étape 1 : Vérification des prérequis système ─────────
# Exigences : 1.1, 1.2, 31.4

check_prerequisites() {
    info "Vérification des prérequis système..."
    echo ""

    local errors=()
    local MIN_CPU=4
    local MIN_RAM=8
    local MIN_DISK=50

    # CPU
    local cpu_cores
    if [ "$(uname -s)" = "Darwin" ]; then
        cpu_cores=$(sysctl -n hw.ncpu 2>/dev/null || echo 0)
    else
        cpu_cores=$(nproc 2>/dev/null || grep -c ^processor /proc/cpuinfo 2>/dev/null || echo 0)
    fi
    if [ "$cpu_cores" -lt "$MIN_CPU" ]; then
        errors+=("CPU insuffisant : ${cpu_cores} cœurs (minimum ${MIN_CPU})")
    else
        success "CPU : ${cpu_cores} cœurs (minimum ${MIN_CPU})"
    fi

    # RAM
    local ram_gb
    if [ "$(uname -s)" = "Darwin" ]; then
        local ram_bytes
        ram_bytes=$(sysctl -n hw.memsize 2>/dev/null || echo 0)
        ram_gb=$((ram_bytes / 1073741824))
    else
        local ram_kb
        ram_kb=$(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print $2}' || echo 0)
        ram_gb=$((ram_kb / 1048576))
    fi
    if [ "$ram_gb" -lt "$MIN_RAM" ]; then
        errors+=("RAM insuffisante : ${ram_gb} Go (minimum ${MIN_RAM} Go)")
    else
        success "RAM : ${ram_gb} Go (minimum ${MIN_RAM} Go)"
    fi

    # Espace disque
    local disk_free_gb
    local install_mount
    install_mount=$(df -P "$HOME" | tail -1 | awk '{print $4}')
    disk_free_gb=$((install_mount / 1048576))
    if [ "$disk_free_gb" -lt "$MIN_DISK" ]; then
        errors+=("Espace disque insuffisant : ${disk_free_gb} Go libres (minimum ${MIN_DISK} Go)")
    else
        success "Espace disque : ${disk_free_gb} Go libres (minimum ${MIN_DISK} Go)"
    fi

    # Chiffrement du disque
    local encrypted=false
    if [ "$(uname -s)" = "Darwin" ]; then
        if fdesetup status 2>/dev/null | grep -q "On"; then
            encrypted=true
        fi
    else
        # Linux : vérifier LUKS via lsblk ou dmsetup
        if command -v lsblk &>/dev/null; then
            if lsblk -o TYPE 2>/dev/null | grep -q "crypt"; then
                encrypted=true
            fi
        fi
        if command -v dmsetup &>/dev/null; then
            if dmsetup ls --target crypt 2>/dev/null | grep -q "."; then
                encrypted=true
            fi
        fi
    fi
    if [ "$encrypted" = false ]; then
        errors+=("Le disque n'est pas chiffré (FileVault/LUKS requis)")
    else
        success "Chiffrement du disque : Actif"
    fi

    echo ""

    # Afficher les erreurs et interrompre si nécessaire
    if [ ${#errors[@]} -gt 0 ]; then
        echo -e "${RED}${BOLD}Prérequis non satisfaits :${NC}"
        echo ""
        for err in "${errors[@]}"; do
            echo -e "  ${RED}✖${NC} $err"
        done
        echo ""
        fail "L'installation ne peut pas continuer. Veuillez corriger les problèmes ci-dessus."
    fi

    success "Tous les prérequis sont satisfaits."
    echo ""
}

# ── Étape 2 : Extraction de l'archive ────────────────────

extract_payload() {
    info "Extraction des fichiers d'installation..."

    # Trouver la ligne du marqueur __PAYLOAD_BELOW__
    local match
    match=$(grep -n "^__PAYLOAD_BELOW__$" "$0" | tail -1 | cut -d: -f1)
    if [ -z "$match" ]; then
        fail "Archive corrompue : marqueur de payload introuvable."
    fi

    # Extraire le payload (tout après le marqueur)
    local payload_start=$((match + 1))
    tail -n +"$payload_start" "$0" | tar -xzf - -C "$TEMP_DIR"

    success "Fichiers extraits."
}

# ── Étape 3 : Installation de Docker ─────────────────────
# Exigences : 1.3, 31.5

install_docker() {
    info "Vérification de Docker..."

    if command -v docker &>/dev/null; then
        success "Docker est déjà installé ($(docker --version))."
        return
    fi

    info "Docker n'est pas installé. Installation en cours..."

    if [ "$(uname -s)" = "Darwin" ]; then
        # macOS : télécharger Docker Desktop
        info "Téléchargement de Docker Desktop pour macOS..."
        local dmg_url="https://desktop.docker.com/mac/main/amd64/Docker.dmg"
        # Détecter Apple Silicon
        if [ "$(uname -m)" = "arm64" ]; then
            dmg_url="https://desktop.docker.com/mac/main/arm64/Docker.dmg"
        fi

        local dmg_file="$TEMP_DIR/Docker.dmg"
        curl -fSL "$dmg_url" -o "$dmg_file" || fail "Échec du téléchargement de Docker Desktop."

        info "Installation de Docker Desktop..."
        hdiutil attach "$dmg_file" -quiet
        cp -R "/Volumes/Docker/Docker.app" "/Applications/" 2>/dev/null || \
            sudo cp -R "/Volumes/Docker/Docker.app" "/Applications/"
        hdiutil detach "/Volumes/Docker" -quiet 2>/dev/null || true

        info "Lancement de Docker Desktop..."
        open -a Docker
        success "Docker Desktop installé. Veuillez accepter les conditions d'utilisation si demandé."

    else
        # Linux : installer via le script officiel
        info "Installation de Docker via le script officiel..."
        curl -fsSL https://get.docker.com | sh || fail "Échec de l'installation de Docker."

        # Ajouter l'utilisateur au groupe docker
        if command -v usermod &>/dev/null; then
            sudo usermod -aG docker "$USER" 2>/dev/null || true
            info "Utilisateur ajouté au groupe docker. Un redémarrage de session peut être nécessaire."
        fi

        # Démarrer le service Docker
        if command -v systemctl &>/dev/null; then
            sudo systemctl enable docker 2>/dev/null || true
            sudo systemctl start docker 2>/dev/null || true
        fi

        success "Docker installé."
    fi

    # Attendre que Docker soit prêt
    info "Attente du daemon Docker..."
    local elapsed=0
    local timeout=60
    while [ $elapsed -lt $timeout ]; do
        if docker info &>/dev/null; then
            success "Docker est prêt."
            return
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    warn "Docker n'a pas démarré dans le délai imparti. Vous devrez peut-être le démarrer manuellement."
}

# ── Étape 4 : Installation des fichiers ──────────────────
# Exigences : 31.2, 31.5

install_files() {
    info "Installation dans ${INSTALL_DIR}..."

    mkdir -p "$INSTALL_DIR"/{config,scripts,docker-images,data}

    # Copier les fichiers de configuration
    cp "$TEMP_DIR/config/docker-compose.yml" "$INSTALL_DIR/config/"
    cp "$TEMP_DIR/config/default.env" "$INSTALL_DIR/config/.env" 2>/dev/null || true
    if [ -f "$TEMP_DIR/config/ollama-entrypoint.sh" ]; then
        cp "$TEMP_DIR/config/ollama-entrypoint.sh" "$INSTALL_DIR/config/"
        chmod +x "$INSTALL_DIR/config/ollama-entrypoint.sh"
    fi

    # Copier les scripts
    cp "$TEMP_DIR/scripts/amorce.sh" "$INSTALL_DIR/scripts/"
    cp "$TEMP_DIR/scripts/prerequisites_check.py" "$INSTALL_DIR/scripts/"
    chmod +x "$INSTALL_DIR/scripts/amorce.sh"

    # Copier les images Docker
    if [ -d "$TEMP_DIR/docker-images" ]; then
        cp "$TEMP_DIR/docker-images/"*.tar "$INSTALL_DIR/docker-images/" 2>/dev/null || true
    fi

    # Adapter le docker-compose.yml pour pointer vers le bon répertoire
    if [ -f "$INSTALL_DIR/config/ollama-entrypoint.sh" ]; then
        sed -i.bak "s|./ollama-entrypoint.sh|$INSTALL_DIR/config/ollama-entrypoint.sh|g" \
            "$INSTALL_DIR/config/docker-compose.yml" 2>/dev/null || true
        rm -f "$INSTALL_DIR/config/docker-compose.yml.bak"
    fi

    success "Fichiers installés."
}

# ── Étape 5 : Chargement des images Docker ───────────────
# Exigences : 31.2, 31.5

load_docker_images() {
    info "Chargement des images Docker..."

    local images_dir="$INSTALL_DIR/docker-images"
    if [ ! -d "$images_dir" ] || [ -z "$(ls -A "$images_dir" 2>/dev/null)" ]; then
        warn "Aucune image Docker trouvée dans le package."
        return
    fi

    for tar_file in "$images_dir"/*.tar; do
        local name
        name=$(basename "$tar_file")
        info "  Chargement de ${name}..."
        docker load -i "$tar_file" || warn "Échec du chargement de ${name}"
    done

    success "Images Docker chargées."

    # Optionnel : supprimer les fichiers tar pour libérer de l'espace
    read -rp "Supprimer les fichiers tar des images Docker pour libérer de l'espace ? [O/n] " response
    if [[ "$response" =~ ^[Oo]?$ ]]; then
        rm -f "$images_dir"/*.tar
        success "Fichiers tar supprimés."
    fi
}

# ── Étape 6 : Création du lanceur ────────────────────────

create_launcher() {
    info "Création du lanceur..."

    # Créer un script lanceur dans le répertoire d'installation
    cat > "$INSTALL_DIR/judi-expert.sh" << 'LAUNCHER'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/scripts/amorce.sh"
LAUNCHER
    chmod +x "$INSTALL_DIR/judi-expert.sh"

    # Créer un lien symbolique dans /usr/local/bin si possible
    if [ -w "/usr/local/bin" ] || [ "$(id -u)" -eq 0 ]; then
        ln -sf "$INSTALL_DIR/judi-expert.sh" "/usr/local/bin/judi-expert" 2>/dev/null || true
        success "Commande 'judi-expert' disponible dans le PATH."
    fi

    # macOS : créer une application .app
    if [ "$(uname -s)" = "Darwin" ]; then
        local app_dir="$HOME/Applications/Judi-Expert.app/Contents/MacOS"
        mkdir -p "$app_dir"
        cat > "$app_dir/Judi-Expert" << MACAPP
#!/bin/bash
exec "$INSTALL_DIR/judi-expert.sh"
MACAPP
        chmod +x "$app_dir/Judi-Expert"

        # Info.plist minimal
        cat > "$HOME/Applications/Judi-Expert.app/Contents/Info.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>Judi-Expert</string>
    <key>CFBundleVersion</key>
    <string>${JUDI_VERSION}</string>
    <key>CFBundleExecutable</key>
    <string>Judi-Expert</string>
    <key>CFBundleIdentifier</key>
    <string>fr.itechsource.judi-expert</string>
</dict>
</plist>
PLIST
        success "Application Judi-Expert.app créée dans ~/Applications/"
    fi

    # Linux : créer un fichier .desktop
    if [ "$(uname -s)" = "Linux" ]; then
        local desktop_dir="$HOME/.local/share/applications"
        mkdir -p "$desktop_dir"
        cat > "$desktop_dir/judi-expert.desktop" << DESKTOP
[Desktop Entry]
Name=Judi-Expert
Comment=Application Locale d'expertise judiciaire
Exec=$INSTALL_DIR/judi-expert.sh
Terminal=true
Type=Application
Categories=Office;
DESKTOP
        success "Raccourci Judi-Expert créé dans le menu des applications."
    fi
}

# ── Résumé final ──────────────────────────────────────────

print_summary() {
    echo ""
    echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}${BOLD}  Installation de Judi-Expert ${JUDI_VERSION} terminée !${NC}"
    echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${BOLD}Répertoire d'installation :${NC} ${INSTALL_DIR}"
    echo ""
    echo -e "  ${BOLD}Pour lancer Judi-Expert :${NC}"
    if [ "$(uname -s)" = "Darwin" ]; then
        echo -e "    • Ouvrez l'application ${CYAN}Judi-Expert${NC} dans ~/Applications/"
    else
        echo -e "    • Lancez ${CYAN}judi-expert${NC} depuis le terminal"
        echo -e "    • Ou utilisez le raccourci dans le menu des applications"
    fi
    echo -e "    • Ou exécutez : ${CYAN}${INSTALL_DIR}/judi-expert.sh${NC}"
    echo ""
    echo -e "  ${BOLD}Services disponibles après lancement :${NC}"
    echo -e "    • Application : ${CYAN}http://localhost:3000${NC}"
    echo -e "    • API         : ${CYAN}http://localhost:8000${NC}"
    echo ""
}

# ── Main ──────────────────────────────────────────────────

main() {
    print_banner

    # 1. Vérifier les prérequis système
    check_prerequisites

    # 2. Extraire l'archive
    extract_payload

    # 3. Installer Docker si nécessaire
    install_docker

    # 4. Installer les fichiers
    install_files

    # 5. Charger les images Docker
    load_docker_images

    # 6. Créer le lanceur
    create_launcher

    # 7. Résumé
    print_summary
}

main "$@"

# Ne pas supprimer la ligne ci-dessous — elle sert de marqueur
# pour séparer le script de l'archive tar.gz.
exit 0
