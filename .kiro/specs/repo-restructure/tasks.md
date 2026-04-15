# Implementation Plan: Restructuration du Dépôt

## Overview

Restructurer le dépôt en promouvant `site-central/local/` → `local-site/` et `site-central/aws/` → `central-site/` comme dossiers de premier niveau, puis mettre à jour systématiquement toutes les références (scripts, tests, code source, Docker Compose, documentation, configuration). Chaque tâche est incrémentale et vérifiable.

## Tasks

- [x] 1. Déplacement physique des dossiers via git mv
  - [x] 1.1 Déplacer `site-central/local/` vers `local-site/` via `git mv`
    - Exécuter `git mv site-central/local/ local-site/`
    - Vérifier que `local-site/` contient l'intégralité de l'arborescence (docker-compose.yml, .env, scripts/, ocr/, web/, rag/, amorce.bat, amorce.sh, ollama-entrypoint.sh)
    - _Requirements: 1.1, 1.4_

  - [x] 1.2 Déplacer `site-central/aws/` vers `central-site/` via `git mv`
    - Exécuter `git mv site-central/aws/ central-site/`
    - Vérifier que `central-site/` contient l'intégralité de l'arborescence (docker-compose.dev.yml, .env, terraform/, scripts/, app_locale_package/, web/)
    - _Requirements: 1.2, 1.4_

  - [x] 1.3 Supprimer le dossier `site-central/` résiduel
    - Supprimer `site-central/app_locale_package/output/` (artefact de build vide) et le dossier `site-central/` lui-même
    - Vérifier que `site-central/` n'existe plus dans le dépôt
    - _Requirements: 1.3_

- [x] 2. Mise à jour des scripts shell — chemins et profondeur
  - [x] 2.1 Mettre à jour `central-site/app_locale_package/package.sh`
    - Changer `PROJECT_ROOT="$SCRIPT_DIR/../../.."` → `PROJECT_ROOT="$SCRIPT_DIR/../.."`
    - Changer `LOCAL_DIR="$PROJECT_ROOT/site-central/local"` → `LOCAL_DIR="$PROJECT_ROOT/local-site"`
    - Mettre à jour toute autre référence à `site-central/` dans ce fichier
    - _Requirements: 2.3, 2.4, 8.1, 8.2_

  - [x] 2.2 Vérifier et mettre à jour les scripts dans `central-site/scripts/`
    - Vérifier `build.sh`, `deploy.sh`, `push-ecr.sh`, `update-rag.sh`, `site-start.sh`, `site-stop.sh`, `site-status.sh`
    - Remplacer toute occurrence de `site-central/aws/` par `central-site/` et `site-central/local/` par `local-site/`
    - Vérifier que les calculs `$SCRIPT_DIR/..` restent corrects (la structure interne est préservée)
    - _Requirements: 2.2, 2.4_

  - [x] 2.3 Vérifier et mettre à jour les scripts dans `local-site/scripts/`
    - Vérifier `build.sh`, `start.sh`, `stop.sh`, `restart.sh`, `prerequisites.py`
    - Remplacer toute occurrence de `site-central/local/` par `local-site/`
    - Vérifier que les calculs de chemin relatif restent corrects
    - _Requirements: 2.1_

- [x] 3. Mise à jour des fichiers de test — sys.path.insert()
  - [x] 3.1 Mettre à jour les `sys.path.insert()` dans `tests/unit/`
    - Remplacer `"site-central" / "local" / "web" / "backend"` → `"local-site" / "web" / "backend"` dans tous les fichiers de test unitaire concernés
    - Remplacer `"site-central" / "aws" / "web" / "backend"` → `"central-site" / "web" / "backend"` dans tous les fichiers de test unitaire concernés
    - Vérifier que `parents[2]` reste correct pour les tests à `tests/unit/test_*.py`
    - _Requirements: 3.1, 3.2, 3.5_

  - [x] 3.2 Mettre à jour les `sys.path.insert()` dans `tests/property/`
    - Remplacer `"site-central" / "local"` → `"local-site"` et `"site-central" / "aws"` → `"central-site"` dans tous les fichiers de test par propriétés
    - Inclure les chemins vers `ocr/` et `scripts/` en plus de `web/backend`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 3.3 Mettre à jour les `sys.path.insert()` dans `tests/integration/`
    - Remplacer les mêmes patterns que ci-dessus dans les fichiers de test d'intégration
    - _Requirements: 3.1, 3.2, 3.5_

- [x] 4. Checkpoint — Vérifier les tests après déplacement et mise à jour des imports
  - Exécuter `pytest tests/unit/ tests/property/ -v` pour vérifier que tous les imports fonctionnent
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Mise à jour du code source applicatif
  - [x] 5.1 Mettre à jour `central-site/web/backend/routers/downloads.py`
    - Remplacer les instructions textuelles : `site-central/local/scripts` → `local-site/scripts`, `site-central/aws/app_locale_package` → `central-site/app_locale_package`
    - _Requirements: 6.1_

  - [x] 5.2 Mettre à jour `central-site/web/backend/services/domaines_service.py`
    - Changer `_BACKEND_DIR.parents[3]` → `_BACKEND_DIR.parents[2]` (3 niveaux au lieu de 4 pour atteindre la racine)
    - Mettre à jour tout commentaire référençant `site-central/aws/web/backend`
    - _Requirements: 6.2, 6.3, 8.1_

  - [x] 5.3 Mettre à jour `central-site/app_locale_package/common/prerequisites_check.py`
    - Mettre à jour le commentaire docstring : `site-central/local/scripts/prerequisites.py` → `local-site/scripts/prerequisites.py`
    - _Requirements: 6.4_

- [x] 6. Mise à jour de Docker Compose
  - [x] 6.1 Mettre à jour `central-site/docker-compose.dev.yml`
    - Mettre à jour le commentaire d'usage : `site-central/aws/docker-compose.dev.yml` → `central-site/docker-compose.dev.yml`
    - Changer les volumes : `../../domaines` → `../domaines`, `../../corpus` → `../corpus` (un niveau de moins à remonter)
    - Remplacer toute autre occurrence de `site-central/` dans le fichier
    - _Requirements: 5.2_

- [x] 7. Mise à jour de la documentation
  - [x] 7.1 Mettre à jour `docs/quick-start.md`
    - Remplacer toutes les occurrences `site-central/local/` → `local-site/`, `site-central/aws/` → `central-site/`
    - Supprimer l'avertissement ⚠️ sur la confusion de nommage `site-central/local/`
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 7.2 Mettre à jour `docs/developpement.md`
    - Mettre à jour les diagrammes d'arborescence et les commandes
    - Remplacer toutes les occurrences `site-central/local/` → `local-site/`, `site-central/aws/` → `central-site/`
    - _Requirements: 4.1, 4.2, 4.3, 4.5_

  - [x] 7.3 Mettre à jour `docs/exploitation.md`
    - Mettre à jour toutes les commandes `cd site-central/...`
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 7.4 Mettre à jour `docs/architecture.md`
    - Mettre à jour les références de structure
    - _Requirements: 4.1, 4.2, 4.3, 4.5_

  - [x] 7.5 Mettre à jour `docs/stripe.md`
    - Mettre à jour les chemins dans les exemples de commandes
    - _Requirements: 4.1, 4.2_

  - [x] 7.6 Mettre à jour `.kiro/steering/structure.md`
    - Réécrire le diagramme d'arborescence complet pour refléter `local-site/` et `central-site/`
    - _Requirements: 4.5_

  - [x] 7.7 Mettre à jour `.kiro/steering/tech.md`
    - Mettre à jour toutes les commandes dans la section "Common Commands" : `site-central/local` → `local-site`, `site-central/aws` → `central-site`, `site-central/` → `local-site/` et `central-site/`
    - _Requirements: 5.3_

  - [x] 7.8 Mettre à jour `prompts/prompt1`
    - Remplacer les références `site-central/local` → `local-site`, `site-central/aws` → `central-site`
    - _Requirements: 7.1_

- [x] 8. Mise à jour de la configuration
  - [x] 8.1 Mettre à jour `.gitignore`
    - Remplacer `site-central/aws/app_locale_package/.staging/` → `central-site/app_locale_package/.staging/`
    - Remplacer les chemins `output/*.exe` et `output/*.sh` sous `site-central/` → `central-site/`
    - Remplacer toute autre occurrence de `site-central/` dans `.gitignore`
    - _Requirements: 5.1_

- [x] 9. Vérification exhaustive et tests finaux
  - [x] 9.1 Vérification grep — aucune référence résiduelle à `site-central/`
    - Exécuter `grep -rn "site-central" . --exclude-dir=.git --exclude-dir=.kiro/specs/judi-expert --exclude-dir=.kiro/specs/repo-restructure`
    - Le résultat doit être vide (aucune occurrence dans les fichiers actifs)
    - Corriger toute occurrence trouvée
    - _Requirements: 1.3, 4.3_

  - [x] 9.2 Exécuter la suite de tests complète
    - Exécuter `pytest tests/unit/ tests/property/ -v` — tous les tests doivent passer
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 9.3 Valider la syntaxe des scripts shell
    - Exécuter `bash -n` sur `central-site/app_locale_package/package.sh` et les scripts dans `central-site/scripts/`
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 10. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Toutes les modifications doivent être effectuées dans un seul commit pour garantir l'atomicité
- Les fichiers dans `.kiro/specs/judi-expert/` et `.kiro/specs/repo-restructure/` sont exclus de la vérification grep (références historiques)
- Les tests par propriétés ne s'appliquent pas à cette fonctionnalité (restructuration de fichiers, pas de fonctions pures)
- Chaque tâche référence les exigences spécifiques pour la traçabilité
- Les checkpoints permettent une validation incrémentale
