#!/usr/bin/env bash
# =============================================================================
# validate-terminology-refactoring.sh
# Script de validation post-refactoring terminologique
# Vérifie qu'aucune occurrence résiduelle de l'ancienne terminologie "local"
# (au sens du composant client) ne subsiste dans le dépôt.
# =============================================================================

set -euo pipefail

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Compteurs
ERRORS=0

# Répertoire racine du projet (parent de scripts-dev/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE} Validation post-refactoring terminologique${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Répertoire projet: $PROJECT_ROOT"
echo ""

# =============================================================================
# CHECK 1: Vérifier que local-site/ n'existe plus
# =============================================================================
echo -e "${BLUE}[CHECK 1] Vérification que local-site/ n'existe plus...${NC}"
if [ -d "$PROJECT_ROOT/local-site" ]; then
    echo -e "  ${RED}ERREUR: Le répertoire local-site/ existe encore !${NC}"
    ERRORS=$((ERRORS + 1))
else
    echo -e "  ${GREEN}OK: local-site/ n'existe plus.${NC}"
fi
echo ""

# =============================================================================
# CHECK 2: Vérifier qu'aucun scripts-dev/dev-local-* n'existe
# =============================================================================
echo -e "${BLUE}[CHECK 2] Vérification qu'aucun scripts-dev/dev-local-* n'existe...${NC}"
OLD_SCRIPTS=$(find "$PROJECT_ROOT/scripts-dev" -name "dev-local-*" 2>/dev/null || true)
if [ -n "$OLD_SCRIPTS" ]; then
    echo -e "  ${RED}ERREUR: Des scripts dev-local-* existent encore :${NC}"
    echo "$OLD_SCRIPTS" | while read -r f; do echo -e "    ${RED}- $f${NC}"; done
    ERRORS=$((ERRORS + 1))
else
    echo -e "  ${GREEN}OK: Aucun script dev-local-* trouvé.${NC}"
fi
echo ""

# =============================================================================
# CHECK 3: Vérifier que central-site/app_locale_package/ n'existe plus
# =============================================================================
echo -e "${BLUE}[CHECK 3] Vérification que central-site/app_locale_package/ n'existe plus...${NC}"
if [ -d "$PROJECT_ROOT/central-site/app_locale_package" ]; then
    echo -e "  ${RED}ERREUR: Le répertoire central-site/app_locale_package/ existe encore !${NC}"
    ERRORS=$((ERRORS + 1))
else
    echo -e "  ${GREEN}OK: central-site/app_locale_package/ n'existe plus.${NC}"
fi
echo ""

# =============================================================================
# CHECK 4: Grep exhaustif pour les occurrences résiduelles
# =============================================================================
echo -e "${BLUE}[CHECK 4] Recherche d'occurrences résiduelles dans les fichiers source...${NC}"
echo -e "${YELLOW}  (Exclusions: .git/, node_modules/, .hypothesis/, __pycache__/, .kiro/specs/, .next/)${NC}"
echo ""

# Patterns à rechercher (ancienne terminologie au sens composant)
PATTERNS=(
    "local-site"
    "dev-local-"
    "app_locale_package"
    "judi-expert-local-"
)

# Extensions de fichiers à analyser
INCLUDE_EXTENSIONS="--include=*.sh --include=*.md --include=*.yml --include=*.yaml --include=*.ts --include=*.tsx --include=*.py --include=*.json --include=*.nsi --include=*.env --include=*.tf"

# Répertoires à exclure
# - .git/ : historique Git
# - node_modules/ : dépendances
# - .hypothesis/ : données de test Hypothesis
# - __pycache__/ : cache Python
# - .kiro/specs/ : documentation des specs (référence l'ancien nommage dans les descriptions)
# - .next/ : artefacts de build Next.js (générés, contiennent des chemins absolus figés)
EXCLUDE_DIRS="--exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.hypothesis --exclude-dir=__pycache__ --exclude-dir=.next --exclude-dir=specs"

ISSUE_COUNT=0

for pattern in "${PATTERNS[@]}"; do
    echo -e "  Recherche de '${YELLOW}$pattern${NC}'..."

    # Exécuter grep avec les options appropriées
    GREP_RESULTS=$(grep -rn $INCLUDE_EXTENSIONS $EXCLUDE_DIRS "$pattern" "$PROJECT_ROOT" 2>/dev/null || true)

    if [ -n "$GREP_RESULTS" ]; then
        while IFS= read -r line; do
            # Extraire le chemin relatif
            REL_PATH="${line#$PROJECT_ROOT/}"

            # Exclure le script de validation lui-même
            if echo "$REL_PATH" | grep -q "validate-terminology-refactoring.sh"; then
                continue
            fi

            # Exclure les fichiers dans .kiro/specs/ (documentation des specs)
            if echo "$REL_PATH" | grep -q "\.kiro/specs/"; then
                continue
            fi

            # Exclure les fichiers .next/ (artefacts de build Next.js)
            if echo "$REL_PATH" | grep -q "\.next/"; then
                continue
            fi

            echo -e "    ${RED}TROUVÉ: $REL_PATH${NC}"
            ISSUE_COUNT=$((ISSUE_COUNT + 1))

        done <<< "$GREP_RESULTS"
    fi
done

echo ""

# =============================================================================
# RÉSUMÉ
# =============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE} RÉSUMÉ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

TOTAL_ERRORS=$((ERRORS + ISSUE_COUNT))

echo -e "  Erreurs structurelles (répertoires/fichiers) : $ERRORS"
echo -e "  Occurrences résiduelles dans le code         : $ISSUE_COUNT"
echo ""

if [ "$TOTAL_ERRORS" -eq 0 ]; then
    echo -e "${GREEN}✓ VALIDATION RÉUSSIE : Aucun résidu de l'ancienne terminologie détecté.${NC}"
    echo -e "${GREEN}  Le refactoring terminologique est complet.${NC}"
    exit 0
else
    echo -e "${RED}✗ VALIDATION ÉCHOUÉE : $TOTAL_ERRORS problème(s) détecté(s).${NC}"
    echo -e "${RED}  Des corrections sont nécessaires avant de finaliser le refactoring.${NC}"
    echo ""
    echo -e "${YELLOW}Note: Le terme « local » reste acceptable uniquement pour :${NC}"
    echo -e "${YELLOW}  - Le mode de déploiement dev (localhost, mode local, déploiement local)${NC}"
    echo -e "${YELLOW}  - Les variables SQLite/DB locales (aucun changement requis)${NC}"
    echo -e "${YELLOW}  - Les références à des fichiers .local ou configurations locales${NC}"
    echo ""
    echo -e "${YELLOW}Exclusions (non comptabilisées) :${NC}"
    echo -e "${YELLOW}  - .kiro/specs/ : documentation historique des specs${NC}"
    echo -e "${YELLOW}  - .next/ : artefacts de build Next.js (sera résolu au prochain build)${NC}"
    exit 1
fi
