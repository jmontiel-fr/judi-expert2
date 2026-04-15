# Document d'Exigences — Restructuration du Dépôt

## Introduction

Le dépôt Judi-Expert utilise actuellement un dossier parent `site-central/` contenant deux sous-dossiers (`local/` et `aws/`) pour deux applications distinctes. Cette organisation prête à confusion : `site-central/local/` laisse penser qu'il s'agit d'une version locale du Site Central, alors qu'il s'agit de l'Application Locale — un produit complètement différent. La restructuration vise à promouvoir chaque application en dossier de premier niveau avec un nom explicite : `local-site/` (Application Locale) et `central-site/` (Site Central).

## Glossaire

- **Dépôt** : Le dépôt Git `judi-expert` contenant l'ensemble du code source du projet
- **Application_Locale** : L'application desktop conteneurisée (Docker Compose, 4 conteneurs) installée sur le PC de l'expert judiciaire
- **Site_Central** : La plateforme web AWS gérant l'inscription, les paiements, la distribution des corpus RAG et l'administration
- **local-site** : Nouveau nom du dossier de premier niveau contenant l'Application_Locale (anciennement `site-central/local/`)
- **central-site** : Nouveau nom du dossier de premier niveau contenant le Site_Central (anciennement `site-central/aws/`)
- **Référence_de_chemin** : Toute occurrence textuelle d'un chemin de fichier ou dossier dans le code source, les scripts, la documentation ou la configuration
- **Script_shell** : Fichier `.sh` exécutable utilisé pour le build, le démarrage, l'arrêt ou le déploiement des services
- **Fichier_de_configuration** : Fichier `.env`, `docker-compose.yml`, `alembic.ini`, `.gitignore`, ou tout fichier définissant des paramètres du projet
- **Documentation_projet** : Fichiers Markdown dans `docs/`, `.kiro/steering/`, et tout autre fichier `.md` décrivant le projet
- **Fichier_de_test** : Fichier Python dans `tests/` contenant des tests unitaires, par propriétés, d'intégration ou de fumée
- **Chemin_sys.path** : Instruction `sys.path.insert()` dans un Fichier_de_test qui ajoute un répertoire backend ou service au chemin d'import Python

## Exigences

### Exigence 1 : Déplacement des dossiers applicatifs

**User Story :** En tant que développeur, je veux que chaque application ait son propre dossier de premier niveau avec un nom explicite, afin de comprendre immédiatement à quelle application correspond chaque dossier.

#### Critères d'acceptation

1. THE Dépôt SHALL contenir un dossier `local-site/` à la racine avec l'intégralité du contenu précédemment situé dans `site-central/local/`
2. THE Dépôt SHALL contenir un dossier `central-site/` à la racine avec l'intégralité du contenu précédemment situé dans `site-central/aws/`
3. THE Dépôt SHALL ne plus contenir le dossier `site-central/`
4. WHEN le contenu est déplacé vers `local-site/` et `central-site/`, THE Dépôt SHALL préserver l'arborescence interne de chaque application sans modification de la structure des sous-dossiers

### Exigence 2 : Mise à jour des scripts shell

**User Story :** En tant que développeur, je veux que tous les scripts shell fonctionnent correctement après la restructuration, afin de pouvoir builder, démarrer, arrêter et déployer les services sans modification manuelle.

#### Critères d'acceptation

1. WHEN un Script_shell dans `local-site/scripts/` référence un chemin relatif vers le dossier projet, THE Script_shell SHALL utiliser des chemins cohérents avec la nouvelle structure `local-site/`
2. WHEN un Script_shell dans `central-site/scripts/` référence un chemin relatif vers le dossier projet, THE Script_shell SHALL utiliser des chemins cohérents avec la nouvelle structure `central-site/`
3. WHEN le script `central-site/app_locale_package/package.sh` calcule le chemin vers l'Application_Locale, THE Script_shell SHALL pointer vers `local-site/` au lieu de `site-central/local/`
4. WHEN un Script_shell dans `central-site/scripts/` référence le chemin du projet parent, THE Script_shell SHALL calculer correctement la racine du projet en tenant compte de la nouvelle profondeur de répertoire (un niveau au lieu de deux)

### Exigence 3 : Mise à jour des fichiers de test

**User Story :** En tant que développeur, je veux que tous les tests continuent de passer après la restructuration, afin de garantir la non-régression du projet.

#### Critères d'acceptation

1. WHEN un Fichier_de_test contient un Chemin_sys.path vers `site-central/local/web/backend`, THE Fichier_de_test SHALL utiliser le chemin `local-site/web/backend`
2. WHEN un Fichier_de_test contient un Chemin_sys.path vers `site-central/aws/web/backend`, THE Fichier_de_test SHALL utiliser le chemin `central-site/web/backend`
3. WHEN un Fichier_de_test contient un Chemin_sys.path vers `site-central/local/ocr`, THE Fichier_de_test SHALL utiliser le chemin `local-site/ocr`
4. WHEN un Fichier_de_test contient un Chemin_sys.path vers `site-central/local/scripts`, THE Fichier_de_test SHALL utiliser le chemin `local-site/scripts`
5. WHEN un Fichier_de_test calcule le nombre de niveaux parents pour atteindre la racine du projet, THE Fichier_de_test SHALL utiliser `parents[2]` pour les chemins à deux niveaux de profondeur depuis `tests/{catégorie}/`

### Exigence 4 : Mise à jour de la documentation projet

**User Story :** En tant que développeur ou contributeur, je veux que toute la documentation reflète la nouvelle structure de dossiers, afin d'éviter toute confusion lors de la consultation des guides.

#### Critères d'acceptation

1. WHEN la Documentation_projet mentionne le chemin `site-central/local/`, THE Documentation_projet SHALL utiliser `local-site/` à la place
2. WHEN la Documentation_projet mentionne le chemin `site-central/aws/`, THE Documentation_projet SHALL utiliser `central-site/` à la place
3. WHEN la Documentation_projet mentionne le dossier parent `site-central/`, THE Documentation_projet SHALL supprimer cette référence ou la remplacer par une description des deux dossiers de premier niveau `local-site/` et `central-site/`
4. WHEN le fichier `docs/quick-start.md` contient l'avertissement sur la confusion de nommage `site-central/local/`, THE Documentation_projet SHALL supprimer cet avertissement devenu obsolète grâce à la nouvelle structure explicite
5. THE Documentation_projet SHALL mettre à jour les diagrammes d'arborescence dans `docs/developpement.md`, `.kiro/steering/structure.md` et tout autre fichier contenant une représentation de la structure du dépôt

### Exigence 5 : Mise à jour des fichiers de configuration

**User Story :** En tant que développeur, je veux que tous les fichiers de configuration référencent les bons chemins après la restructuration, afin que le build, le linting et les migrations fonctionnent correctement.

#### Critères d'acceptation

1. WHEN le fichier `.gitignore` contient des chemins commençant par `site-central/`, THE Fichier_de_configuration SHALL utiliser les chemins équivalents sous `central-site/` ou `local-site/`
2. WHEN le fichier `docker-compose.dev.yml` dans `central-site/` contient un commentaire de commande d'usage référençant `site-central/aws/`, THE Fichier_de_configuration SHALL utiliser `central-site/` à la place
3. WHEN les commandes de linting dans `.kiro/steering/tech.md` référencent `site-central/`, THE Fichier_de_configuration SHALL utiliser `local-site/` et `central-site/` respectivement

### Exigence 6 : Mise à jour des références dans le code source

**User Story :** En tant que développeur, je veux que le code source applicatif ne contienne plus de références aux anciens chemins, afin d'éviter des erreurs d'exécution.

#### Critères d'acceptation

1. WHEN le fichier `central-site/web/backend/routers/downloads.py` contient des instructions textuelles référençant `site-central/local/` ou `site-central/aws/`, THE code source SHALL utiliser `local-site/` et `central-site/` respectivement
2. WHEN le fichier `central-site/web/backend/services/domaines_service.py` contient un commentaire référençant `site-central/aws/web/backend`, THE code source SHALL utiliser `central-site/web/backend`
3. WHEN le fichier `central-site/web/backend/services/domaines_service.py` calcule le chemin vers la racine du projet via `_BACKEND_DIR.parents[3]`, THE code source SHALL utiliser `_BACKEND_DIR.parents[2]` pour refléter la nouvelle profondeur de répertoire (3 niveaux au lieu de 4)
4. WHEN le fichier `central-site/app_locale_package/common/prerequisites_check.py` contient un commentaire référençant `site-central/local/scripts/prerequisites.py`, THE code source SHALL utiliser `local-site/scripts/prerequisites.py`

### Exigence 7 : Mise à jour du fichier de prompts

**User Story :** En tant que développeur, je veux que le fichier de prompts LLM reflète la nouvelle structure, afin que les descriptions de l'arborescence du projet soient correctes.

#### Critères d'acceptation

1. WHEN le fichier `prompts/prompt1` décrit l'arborescence du projet avec `site-central/local` et `site-central/aws`, THE fichier de prompts SHALL utiliser `local-site` et `central-site` respectivement

### Exigence 8 : Cohérence du calcul de profondeur de répertoire

**User Story :** En tant que développeur, je veux que tous les calculs de chemins relatifs (parents[N]) soient ajustés à la nouvelle profondeur, afin d'éviter des erreurs de résolution de chemin à l'exécution.

#### Critères d'acceptation

1. WHEN un script shell calcule `PROJECT_ROOT` en remontant depuis un sous-dossier, THE Script_shell SHALL ajuster le nombre de niveaux parents pour refléter la suppression du niveau `site-central/`
2. WHEN le script `central-site/app_locale_package/package.sh` calcule `PROJECT_ROOT` via `$SCRIPT_DIR/../../..`, THE Script_shell SHALL utiliser `$SCRIPT_DIR/../..` car `app_locale_package/` est maintenant à deux niveaux de la racine au lieu de trois
