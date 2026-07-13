# Judi-Expert — Tech Stack & Commands

## Autonomie d'exécution

- **Exécuter toutes les commandes non-destructives sans attendre de confirmation** (pas de « Run » ou « >> » nécessaire)
- Seules les commandes qui détruisent des données (suppression de fichiers, drop de tables, reset --hard, etc.) nécessitent une confirmation explicite de l'utilisateur

## Infrastructure AWS — Règles absolues

- **Ne JAMAIS créer, modifier ou supprimer des ressources AWS via la CLI** (`aws s3 mb`, `aws ec2 run-instances`, etc.)
- **Toute modification d'infrastructure doit passer par Terraform** (fichiers dans `central-site/terraform/`)
- Si une ressource n'existe pas, **ajouter le module/resource Terraform** correspondant, puis appliquer via le script de déploiement
- Les seules commandes AWS CLI autorisées sont : lecture (`aws s3 ls`, `aws ecs describe-*`), upload de fichiers applicatifs (`aws s3 cp` pour des artefacts déjà gérés par un bucket Terraform), et opérations de déploiement encapsulées dans les scripts existants
- **Jamais de patch CLI pour contourner un manque dans Terraform** — corriger Terraform à la place

## Fiabilité des commandes et scripts

- **Ne JAMAIS laisser une commande échouer silencieusement** — chaque commande doit vérifier son code retour (`set -euo pipefail` dans les scripts bash)
- **Toujours tester les commandes après écriture** — exécuter le script ou la commande pour vérifier qu'il fonctionne avant de le considérer comme terminé
- **Vérifier les prérequis avant exécution** — si un script dépend d'un bucket S3, d'un service, ou d'une config, vérifier qu'ils existent avant de lancer l'opération
- **Afficher clairement les erreurs** — pas de `2>/dev/null` sur les commandes critiques, pas de `|| true` qui masque des échecs importants
- **Valider le résultat** — après un upload S3, un docker push, ou un déploiement, vérifier que l'opération a réellement abouti (ex: `aws s3 ls` après upload, `docker images` après build)

## Règles d'exécution des commandes

- **Toujours utiliser `bash` pour exécuter les scripts shell** (ex: `bash scripts-dev/dev-client-start.sh`, `bash central-site/app_client_package/package.sh`). Ne jamais utiliser `sh`, `./`, ou d'autres shells.
- **Ne JAMAIS lancer les commandes en arrière-plan** (pas de `control_pwsh_process` / background process)
- Toujours exécuter les commandes en **foreground** avec `execute_pwsh` et un `timeout` suffisant
- Les **traces d'exécution doivent être visibles** dans la sortie (pas de `skipPruning: true` sauf si nécessaire pour debug)
- **Ne JAMAIS utiliser `tail`, `head`, ou pipes pour masquer/tronquer la sortie des commandes** — toujours afficher la sortie complète
- Pour les builds Docker longs, utiliser `timeout: 300000` (5 min) ou plus
- **Pour le déploiement, utiliser UNIQUEMENT les scripts `scripts-dev/`** — jamais de commandes Docker directes (`docker compose build`, `docker compose up`, etc.)
- Si un script ne couvre pas un besoin (ex: rebuild d'un seul service), **ajouter une option au script existant** plutôt que de lancer une commande directe
- Scripts disponibles : `dev-client-start.sh [--build] [--no-cache] [--pull-llm]`, `dev-client-stop.sh`, `dev-client-restart.sh`, `dev-client-status.sh`

## Backend (Python)

- **Framework**: FastAPI 0.115.x + Uvicorn
- **ORM**: SQLAlchemy 2.0 (Mapped types) + Alembic migrations
- **Local DB**: SQLite (via aiosqlite)
- **Central DB**: PostgreSQL (via asyncpg / psycopg2-binary)
- **Auth (local)**: passlib (bcrypt) + python-jose (JWT, HS256)
- **Auth (central)**: AWS Cognito + python-jose
- **Payments**: Stripe SDK 11.x
- **HTTP client**: httpx
- **Doc generation**: docxtpl (Jinja2 templates for .docx)
- **OCR**: pytesseract + pdf2image + PyMuPDF
- **RAG**: Qdrant client + FastEmbed (sentence-transformers/all-MiniLM-L6-v2)
- **LLM runtime**: Ollama (Mistral 7B Instruct v0.3)
- **AWS SDK**: boto3

## Frontend (TypeScript)

- **Framework**: Next.js 14 (App Router) + React 18
- **HTTP client**: axios
- **AWS auth (central only)**: aws-amplify 6.x
- **Payments (central only)**: @stripe/stripe-js
- **Style**: functional components with hooks, no class components

## Infrastructure

- **Containerization**: Docker + Docker Compose (local), ECS Fargate + ECR (AWS)
- **IaC**: Terraform
- **AWS services**: ECS, RDS, Cognito, S3, ECR, CloudFront, ALB, EventBridge, Lambda, SES, CloudWatch, Route 53, Secrets Manager

## Python Conventions

- PEP 8, formatted with `black` (88 char line), imports sorted with `isort`
- Type annotations required, checked with `mypy`
- Google-style docstrings for public functions
- Naming: `snake_case` (vars/functions), `PascalCase` (classes), `UPPER_SNAKE_CASE` (constants)

## TypeScript Conventions

- ESLint (Next.js config) + Prettier
- Naming: `camelCase` (vars/functions), `PascalCase` (components/files)

## Git Conventions

- Commit format: `type(scope): description`
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
- Messages in French or English

## Database Migrations

- **Ne JAMAIS modifier le schéma DB manuellement** (pas de `CREATE TABLE`, `ALTER TABLE` direct, ni via SQLAlchemy `create_all`)
- Toute modification de schéma (ajout/suppression de colonne, nouvelle table, changement de type) **doit passer par une migration Alembic**
- Quand un modèle SQLAlchemy est modifié, créer immédiatement la migration correspondante : `alembic revision --autogenerate -m "description"` ou manuellement dans `alembic/versions/`
- Convention de nommage des fichiers : `NNN_description.py` (ex: `004_add_expert_profile_columns.py`)
- Les migrations doivent être réversibles (implémenter `upgrade()` ET `downgrade()`)
- Tester la migration en local avant de déployer

## Testing

- **Framework**: pytest
- **Property-based testing**: Hypothesis (tests in `tests/property/`)
- **Test categories**: unit, property, integration, smoke

### Common Commands

```bash
# --- Dev Scripts (preferred — run from repo root) ---
# IMPORTANT: All dev start/stop/restart scripts are in scripts-dev/ at repo root.
# Do NOT use client-site/scripts/ or central-site/scripts/dev-* (deleted).
# client-site/scripts/ only contains prerequisites.py.
# central-site/scripts/ contains only AWS prod deployment scripts.
bash scripts-dev/dev-client-start.sh              # Start Site Client
bash scripts-dev/dev-client-start.sh --build      # Start + rebuild images
bash scripts-dev/dev-client-start.sh --pull-llm   # Start + download LLM model if missing
bash scripts-dev/dev-client-stop.sh               # Stop Site Client
bash scripts-dev/dev-client-restart.sh             # Restart Site Client
bash scripts-dev/dev-client-status.sh              # Check client containers status
bash scripts-dev/dev-central-start.sh             # Start Site Central
bash scripts-dev/dev-central-start.sh --build     # Start + rebuild images
bash scripts-dev/dev-central-stop.sh              # Stop Site Central
bash scripts-dev/dev-central-restart.sh            # Restart Site Central
bash scripts-dev/dev-central-status.sh             # Check central containers status
# Local: http://localhost:3000 (web), http://localhost:8000 (api)
# Central: http://localhost:3001 (web), http://localhost:8002/docs (api), localhost:5433 (pg)

# --- Tests ---
pytest tests/unit/ -v                  # Unit tests
pytest tests/property/ -v              # Property-based tests (Hypothesis)
pytest tests/integration/ -v           # Integration tests
pytest tests/smoke/ -v                 # Smoke tests

# --- Linting / Formatting (Python) ---
black client-site/ central-site/
isort client-site/ central-site/
flake8 client-site/ central-site/
mypy client-site/ central-site/

# --- Linting (Frontend) ---
cd client-site/web/frontend && npx eslint src/
cd central-site/web/frontend && npx eslint src/

# --- DB Migrations ---
cd client-site/web/backend && alembic upgrade head
cd central-site/web/backend && alembic upgrade head
# New migration: alembic revision --autogenerate -m "description"

# --- AWS Deployment (from repo root) ---
cd central-site/scripts
./build.sh && ./push-ecr.sh && ./deploy.sh
# deploy.sh runs: terraform init → plan → apply (eu-west-3)
# Config: central-site/terraform/terraform.tfvars

# --- Packaging installer (.exe) ---
bash central-site/app_client_package/package.sh windows
```
