# Document de Conception — Restructuration du Dépôt

## Vue d'ensemble

Cette conception décrit l'approche pour restructurer le dépôt Judi-Expert en promouvant les deux applications (`site-central/local/` et `site-central/aws/`) en dossiers de premier niveau (`local-site/` et `central-site/`), puis en mettant à jour toutes les références à travers le code, les scripts, les tests, la documentation et la configuration.

L'opération est essentiellement un déplacement de fichiers suivi d'un search-and-replace systématique, avec un ajustement ciblé des calculs de profondeur de répertoire (`parents[N]`, `$SCRIPT_DIR/../../..`).

### Principes directeurs

- **Atomicité** : toutes les modifications doivent être effectuées dans un seul commit pour éviter un état intermédiaire cassé
- **Exhaustivité** : chaque occurrence de `site-central/` dans le dépôt doit être traitée — aucune référence orpheline
- **Vérifiabilité** : après restructuration, un `grep -r "site-central" .` (hors `.git/` et `.kiro/specs/judi-expert/`) ne doit retourner aucun résultat dans les fichiers actifs

## Architecture

### Transformation de la structure

```
AVANT                                    APRÈS
─────                                    ─────
judi-expert/                             judi-expert/
├── site-central/                        ├── local-site/          ← site-central/local/
│   ├── local/          ──────────►      │   ├── docker-compose.yml
│   │   ├── docker-compose.yml           │   ├── .env
│   │   ├── .env                         │   ├── scripts/
│   │   ├── scripts/                     │   ├── ocr/
│   │   ├── ocr/                         │   ├── web/
│   │   ├── web/                         │   └── ...
│   │   └── ...                          │
│   └── aws/            ──────────►      ├── central-site/        ← site-central/aws/
│       ├── docker-compose.dev.yml       │   ├── docker-compose.dev.yml
│       ├── .env                         │   ├── .env
│       ├── terraform/                   │   ├── terraform/
│       ├── scripts/                     │   ├── scripts/
│       ├── app_locale_package/          │   ├── app_locale_package/
│       └── web/                         │   └── web/
│                                        │
├── corpus/                              ├── corpus/
├── domaines/                            ├── domaines/
├── prompts/                             ├── prompts/
├── tests/                               ├── tests/
└── docs/                                └── docs/
```

### Impact sur la profondeur de répertoire

Le changement clé est la suppression d'un niveau d'imbrication. Les fichiers qui étaient à `site-central/aws/...` (2 niveaux sous la racine) sont maintenant à `central-site/...` (1 niveau sous la racine).

| Chemin ancien | Profondeur | Chemin nouveau | Profondeur | Delta |
|---|---|---|---|---|
| `site-central/local/scripts/build.sh` | 3 | `local-site/scripts/build.sh` | 2 | -1 |
| `site-central/aws/scripts/build.sh` | 3 | `central-site/scripts/build.sh` | 2 | -1 |
| `site-central/aws/web/backend/` | 4 | `central-site/web/backend/` | 3 | -1 |
| `site-central/aws/app_locale_package/` | 3 | `central-site/app_locale_package/` | 2 | -1 |

## Composants et interfaces

### Catégorie 1 : Déplacement physique des dossiers

Deux opérations `git mv` :

1. `site-central/local/` → `local-site/`
2. `site-central/aws/` → `central-site/`

Puis suppression du dossier `site-central/` résiduel (contient `site-central/app_locale_package/output/` qui est un artefact de build vide).

### Catégorie 2 : Scripts shell — chemins relatifs et calculs de profondeur

**Fichiers impactés :**

| Fichier | Modification |
|---|---|
| `central-site/app_locale_package/package.sh` | `PROJECT_ROOT="$SCRIPT_DIR/../../.."` → `"$SCRIPT_DIR/../.."` ; `LOCAL_DIR="$PROJECT_ROOT/site-central/local"` → `"$PROJECT_ROOT/local-site"` |
| `central-site/scripts/build.sh` | Aucun changement de calcul (utilise `$SCRIPT_DIR/..` pour `AWS_DIR`, pas de `PROJECT_ROOT` absolu) |
| `local-site/scripts/build.sh` | Aucun changement de calcul (utilise `$SCRIPT_DIR/..` pour `PROJECT_DIR`) |
| `central-site/scripts/deploy.sh` | Vérifier les chemins relatifs |
| `central-site/scripts/push-ecr.sh` | Vérifier les chemins relatifs |
| `central-site/scripts/update-rag.sh` | Vérifier les chemins relatifs |
| `central-site/scripts/site-start.sh` | Vérifier les chemins relatifs |
| `central-site/scripts/site-stop.sh` | Vérifier les chemins relatifs |
| `central-site/scripts/site-status.sh` | Vérifier les chemins relatifs |

**Règle de transformation pour `$SCRIPT_DIR` :**
- Scripts dans `central-site/scripts/` : `$SCRIPT_DIR/..` pointe vers `central-site/` (inchangé, car la structure interne est préservée)
- Script `package.sh` dans `central-site/app_locale_package/` : `$SCRIPT_DIR/../../..` (3 niveaux) → `$SCRIPT_DIR/../..` (2 niveaux) pour atteindre la racine du projet

### Catégorie 3 : Fichiers de test — `sys.path.insert()`

Tous les fichiers de test utilisent le pattern :
```python
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "site-central" / "local" / "web" / "backend"))
```

**Transformation :**
- `parents[2]` reste correct (les tests sont à `tests/{catégorie}/test_*.py`, soit 2 niveaux sous la racine)
- Le segment de chemin change : `"site-central" / "local"` → `"local-site"` et `"site-central" / "aws"` → `"central-site"`

**Fichiers impactés (tous dans `tests/`) :**

| Pattern ancien | Pattern nouveau |
|---|---|
| `parents[2] / "site-central" / "local" / "web" / "backend"` | `parents[2] / "local-site" / "web" / "backend"` |
| `parents[2] / "site-central" / "aws" / "web" / "backend"` | `parents[2] / "central-site" / "web" / "backend"` |
| `parents[2] / "site-central" / "local" / "ocr"` | `parents[2] / "local-site" / "ocr"` |
| `parents[2] / "site-central" / "local" / "scripts"` | `parents[2] / "local-site" / "scripts"` |

### Catégorie 4 : Code source applicatif

| Fichier | Modification |
|---|---|
| `central-site/web/backend/routers/downloads.py` | Remplacer les instructions textuelles : `site-central/local/scripts` → `local-site/scripts`, `site-central/aws/app_locale_package` → `central-site/app_locale_package` |
| `central-site/web/backend/services/domaines_service.py` | `_BACKEND_DIR.parents[3]` → `_BACKEND_DIR.parents[2]` (le backend est maintenant à 3 niveaux de la racine au lieu de 4) |
| `central-site/app_locale_package/common/prerequisites_check.py` | Mettre à jour le commentaire docstring : `site-central/local/scripts/prerequisites.py` → `local-site/scripts/prerequisites.py` |

### Catégorie 5 : Docker Compose

| Fichier | Modification |
|---|---|
| `central-site/docker-compose.dev.yml` | Commentaire d'usage : `site-central/aws/docker-compose.dev.yml` → `central-site/docker-compose.dev.yml` |
| `central-site/docker-compose.dev.yml` | Volumes : `../../domaines` → `../domaines`, `../../corpus` → `../corpus` (un niveau de moins à remonter) |

### Catégorie 6 : Documentation

| Fichier | Type de modification |
|---|---|
| `docs/quick-start.md` | Remplacer toutes les occurrences `site-central/local/` → `local-site/`, `site-central/aws/` → `central-site/` ; supprimer l'avertissement ⚠️ sur la confusion de nommage |
| `docs/developpement.md` | Mettre à jour les diagrammes d'arborescence et les commandes |
| `docs/exploitation.md` | Mettre à jour toutes les commandes `cd site-central/...` |
| `docs/architecture.md` | Mettre à jour les références de structure |
| `docs/stripe.md` | Mettre à jour les chemins dans les exemples de commandes |
| `.kiro/steering/structure.md` | Réécrire le diagramme d'arborescence complet |
| `.kiro/steering/tech.md` | Mettre à jour toutes les commandes dans la section "Common Commands" |
| `prompts/prompt1` | Mettre à jour les références `site-central/local` → `local-site`, `site-central/aws` → `central-site` |

### Catégorie 7 : Configuration

| Fichier | Modification |
|---|---|
| `.gitignore` | `site-central/aws/app_locale_package/.staging/` → `central-site/app_locale_package/.staging/` ; idem pour `output/*.exe` et `output/*.sh` |

## Modèles de données

Aucun modèle de données n'est impacté. La restructuration ne touche que les chemins de fichiers et les références textuelles. Les modèles SQLAlchemy, les schémas Pydantic et les migrations Alembic restent inchangés.

## Gestion des erreurs

### Risques et mitigations

| Risque | Mitigation |
|---|---|
| Référence `site-central/` oubliée | Vérification post-restructuration via `grep -r "site-central" . --include="*.py" --include="*.sh" --include="*.md" --include="*.yml" --include="*.yaml" --exclude-dir=.git --exclude-dir=.kiro/specs/judi-expert` |
| Calcul de profondeur incorrect (`parents[N]`) | Vérification manuelle de chaque occurrence de `parents[` et `$SCRIPT_DIR/..` |
| Docker Compose volumes cassés | Tester `docker compose config` après modification pour valider la syntaxe |
| Tests cassés après déplacement | Exécuter `pytest tests/ -v` pour vérifier que tous les imports fonctionnent |
| Git history perdue | Utiliser `git mv` pour préserver l'historique des fichiers |

### Stratégie de rollback

En cas de problème, un simple `git reset --hard HEAD~1` annule l'intégralité de la restructuration puisque tout est dans un seul commit.

## Stratégie de test

### Pourquoi les tests par propriétés ne s'appliquent pas

Cette fonctionnalité est une opération de restructuration de fichiers (déplacement + search-and-replace). Il n'y a pas de fonctions pures avec des entrées/sorties variables, pas de logique métier à valider sur un espace d'entrées large, et pas de propriétés universelles à vérifier. Les tests appropriés sont :

- **Vérification exhaustive par grep** : aucune occurrence résiduelle de `site-central/` dans les fichiers actifs
- **Tests unitaires existants** : `pytest tests/unit/ -v` — vérifie que les imports `sys.path` fonctionnent correctement après mise à jour
- **Tests par propriétés existants** : `pytest tests/property/ -v` — vérifie que la logique métier n'a pas régressé
- **Validation Docker Compose** : `docker compose -f central-site/docker-compose.dev.yml config` pour vérifier la syntaxe
- **Validation des scripts shell** : `bash -n central-site/app_locale_package/package.sh` pour vérifier la syntaxe

### Plan de vérification

1. Exécuter `grep -rn "site-central" . --exclude-dir=.git --exclude-dir=.kiro/specs/judi-expert` → doit retourner 0 résultat (hors fichiers de spec historiques)
2. Exécuter `pytest tests/unit/ tests/property/ -v` → tous les tests passent
3. Vérifier que `docker compose -f central-site/docker-compose.dev.yml config` ne produit pas d'erreur
4. Vérifier que `bash -n` sur chaque script `.sh` ne produit pas d'erreur de syntaxe
