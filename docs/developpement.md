# Procédures de Développement — Judi-Expert

## Introduction

Ce document décrit les procédures de développement du projet Judi-Expert, incluant les prérequis, la configuration de l'environnement, la structure du dépôt et les conventions de code.

---

## Cycle de développement (important)

En développement, vous ne passez **jamais** par le `.exe` installateur. Vous travaillez directement depuis le dépôt Git :

```
Modifier le code → build.sh → restart.sh → tester sur localhost → commit
```

### Application Locale (http://localhost:3000)

```bash
cd site-central/local

# Modifier le code (backend, frontend, OCR, etc.)

# Rebuild seulement les images modifiées
./scripts/build.sh

# Relancer les conteneurs
./scripts/restart.sh

# Tester sur http://localhost:3000
```

### Site Central (http://localhost:3001)

```bash
# Rebuild et relancer
docker compose -f site-central/aws/docker-compose.dev.yml up -d --build
```

### Quand repackager le .exe ?

Le `.exe` installateur n'est généré que pour la **distribution aux experts** (release). Le cycle est :

1. Développer et tester localement (build.sh + restart.sh)
2. Quand la version est prête → `bash site-central/aws/app_locale_package/package.sh windows`
3. Le `.exe` est produit dans `site-central/aws/app_locale_package/output/`
4. Publier le `.exe` sur le Site Central (page Downloads)

---

## Prérequis

### Logiciels requis

| Logiciel | Version minimale | Usage |
|----------|-----------------|-------|
| Python | 3.11+ | Backend FastAPI (Application Locale + Site Central) |
| Node.js | 18+ | Frontend Next.js PWA |
| Docker | 24+ | Conteneurisation des services |
| Docker Compose | 2.20+ | Orchestration des conteneurs locaux |
| Git | 2.40+ | Gestion de version |
| Terraform | 1.5+ | Infrastructure AWS (Site Central) |
| AWS CLI | 2.x | Déploiement et gestion AWS |

### Comptes et accès

- **AWS** : compte avec permissions IAM pour ECS, ECR, RDS, S3, Cognito, CloudFront, ALB, EventBridge, Lambda, SES, CloudWatch, Route 53, Secrets Manager
- **Stripe** : compte développeur avec clés API de test
- **Docker Hub** : accès aux images officielles Ollama et Qdrant

---

## Configuration de l'environnement de développement

### 1. Cloner le dépôt

```bash
git clone <url-du-depot> judi-expert
cd judi-expert
```

### 2. Configurer le backend Application Locale

```bash
cd site-central/local/web/backend
python -m venv venv
source venv/bin/activate  # Linux/macOS
# ou venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 3. Configurer le frontend Application Locale

```bash
cd site-central/local/web/frontend
npm install
```

### 4. Configurer le backend Site Central

```bash
cd site-central/aws/web/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Configurer le frontend Site Central

```bash
cd site-central/aws/web/frontend
npm install
```

### 6. Configurer les variables d'environnement

Copier et adapter les fichiers `.env` :

```bash
# Application Locale
cp site-central/local/.env.example site-central/local/.env

# Site Central
cp site-central/aws/.env.example site-central/aws/.env
```

Variables d'environnement principales :

**Application Locale** (`site-central/local/.env`) :
```env
# Base de données
DATABASE_URL=sqlite:///./data/judi.db

# Services internes
LLM_URL=http://judi-llm:11434
RAG_URL=http://judi-rag:6333
OCR_URL=http://judi-ocr:8001

# Site Central
SITE_CENTRAL_URL=https://judi-expert.fr

# JWT
JWT_SECRET_KEY=<clé-secrète-locale>
JWT_ALGORITHM=HS256
```

**Site Central** (`site-central/aws/.env`) :
```env
# Base de données
DATABASE_URL=postgresql://user:password@host:5432/judi_expert

# AWS Cognito
COGNITO_USER_POOL_ID=<pool-id>
COGNITO_CLIENT_ID=<client-id>
COGNITO_REGION=eu-west-3

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# AWS
AWS_REGION=eu-west-3
ECR_REGISTRY=<account-id>.dkr.ecr.eu-west-3.amazonaws.com
```

### 7. Lancer l'Application Locale en développement

```bash
cd site-central/local
docker compose up --build
```

L'application sera accessible sur :
- Frontend : http://localhost:3000
- API Backend : http://localhost:8000
- API LLM (Ollama) : http://localhost:11434
- API RAG (Qdrant) : http://localhost:6333
- API OCR : http://localhost:8001

---

## Structure du dépôt

```
judi-expert/
├── site-central/
│   ├── local/                      # Application Locale
│   │   ├── scripts/                # Scripts de gestion (build, start, stop, restart)
│   │   │   ├── build.sh
│   │   │   ├── start.sh
│   │   │   ├── stop.sh
│   │   │   ├── restart.sh
│   │   │   └── prerequisites.py
│   │   ├── web/
│   │   │   ├── backend/            # FastAPI + SQLAlchemy + SQLite
│   │   │   │   ├── models/         # Modèles SQLAlchemy
│   │   │   │   ├── routes/         # Routes API
│   │   │   │   ├── services/       # Services métier (LLM, RAG, workflow)
│   │   │   │   ├── alembic/        # Migrations de base de données
│   │   │   │   ├── main.py
│   │   │   │   ├── requirements.txt
│   │   │   │   └── Dockerfile
│   │   │   └── frontend/           # Next.js PWA
│   │   │       ├── src/
│   │   │       ├── package.json
│   │   │       ├── next.config.js
│   │   │       └── Dockerfile
│   │   ├── ocr/                    # Service OCR
│   │   │   ├── main.py
│   │   │   ├── requirements.txt
│   │   │   └── Dockerfile
│   │   ├── docker-compose.yml
│   │   ├── ollama-entrypoint.sh
│   │   └── .env
│   │
│   └── aws/                        # Site Central
│       ├── terraform/              # Infrastructure AWS (Terraform)
│       │   ├── main.tf
│       │   ├── variables.tf
│       │   ├── outputs.tf
│       │   └── modules/
│       ├── scripts/                # Scripts de déploiement
│       │   ├── build.sh
│       │   ├── push-ecr.sh
│       │   ├── deploy.sh
│       │   ├── update-rag.sh
│       │   ├── site-start.sh
│       │   ├── site-stop.sh
│       │   └── site-status.sh
│       ├── web/
│       │   ├── backend/            # FastAPI + SQLAlchemy + PostgreSQL
│       │   │   ├── models/
│       │   │   ├── routes/
│       │   │   ├── services/
│       │   │   ├── alembic/
│       │   │   ├── main.py
│       │   │   ├── requirements.txt
│       │   │   └── Dockerfile
│       │   └── frontend/           # Next.js PWA
│       │       ├── src/
│       │       ├── package.json
│       │       ├── next.config.js
│       │       └── Dockerfile
│       ├── app_locale_package/     # Script de packaging installateur
│       └── .env
│
├── corpus/                         # Corpus par domaine
│   ├── psychologie/                # Domaine actif
│   │   ├── documents/              # Documents PDF publics
│   │   ├── urls/
│   │   │   └── urls.yaml           # URLs publiques de référence
│   │   ├── contenu.yaml            # Description du contenu
│   │   ├── TPE_psychologie.tpl     # Trame d'entretien par défaut
│   │   └── template_rapport_psychologie.docx
│   ├── psychiatrie/
│   ├── medecine_legale/
│   ├── batiment/
│   └── comptabilite/
│
├── domaines/
│   └── domaines.yaml               # Configuration des 5 domaines
│
├── docs/                           # Documentation projet (Markdown, français)
│   ├── architecture.md
│   ├── developpement.md
│   ├── exploitation.md
│   ├── stripe.md
│   ├── user-guide.md
│   ├── methodologie.md
│   ├── cout-aws.md
│   ├── cgu.md
│   ├── mentions_legales.md
│   ├── politique_confidentialite.md
│   ├── faq.md
│   └── licences.md
│
└── tests/                          # Tests
    ├── unit/                       # Tests unitaires (pytest)
    ├── property/                   # Tests par propriétés (Hypothesis)
    ├── integration/                # Tests d'intégration
    └── smoke/                      # Tests de fumée
```

---

## Conventions de code

### Python (Backend)

- **Style** : PEP 8 (vérification via `flake8` ou `ruff`)
- **Formatage** : `black` (ligne max 88 caractères)
- **Imports** : triés via `isort`
- **Types** : annotations de type obligatoires (vérification via `mypy`)
- **Docstrings** : format Google pour les fonctions publiques
- **Nommage** :
  - Variables et fonctions : `snake_case`
  - Classes : `PascalCase`
  - Constantes : `UPPER_SNAKE_CASE`
  - Fichiers : `snake_case.py`

### JavaScript / TypeScript (Frontend)

- **Style** : ESLint avec configuration Next.js
- **Formatage** : Prettier
- **Nommage** :
  - Variables et fonctions : `camelCase`
  - Composants React : `PascalCase`
  - Fichiers composants : `PascalCase.tsx`
  - Fichiers utilitaires : `camelCase.ts`
- **Composants** : fonctionnels avec hooks (pas de classes)

### Commits Git

- Messages en français ou anglais
- Format : `type(scope): description`
- Types : `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
- Exemples :
  - `feat(ocr): ajouter extraction PDF-scan`
  - `fix(workflow): corriger transition Step1 → Step2`
  - `docs: mettre à jour architecture.md`

---

## Commandes de build et test

### Build des images Docker (Application Locale)

```bash
cd site-central/local
./scripts/build.sh
```

### Démarrage / Arrêt de l'Application Locale

```bash
./scripts/start.sh    # Démarrage
./scripts/stop.sh     # Arrêt
./scripts/restart.sh  # Redémarrage
```

### Tests unitaires

```bash
# Tous les tests unitaires
pytest tests/unit/ -v

# Un fichier spécifique
pytest tests/unit/test_ocr_service.py -v
```

### Tests par propriétés (Hypothesis)

```bash
# Tous les tests par propriétés
pytest tests/property/ -v

# Une propriété spécifique
pytest tests/property/test_prop_workflow_fsm.py -v
```

### Tests d'intégration

```bash
pytest tests/integration/ -v
```

### Tests de fumée

```bash
pytest tests/smoke/ -v
```

### Linting et formatage

```bash
# Python
black site-central/
isort site-central/
flake8 site-central/
mypy site-central/

# JavaScript
cd site-central/local/web/frontend && npx eslint src/
cd site-central/aws/web/frontend && npx eslint src/
```

### Migrations de base de données

```bash
# Application Locale
cd site-central/local/web/backend
alembic upgrade head          # Appliquer les migrations
alembic revision --autogenerate -m "description"  # Nouvelle migration

# Site Central
cd site-central/aws/web/backend
alembic upgrade head
alembic revision --autogenerate -m "description"
```

### Build et déploiement AWS

```bash
cd site-central/aws/scripts
./build.sh          # Build des images de production
./push-ecr.sh       # Push vers ECR
./deploy.sh         # Déploiement Terraform
./update-rag.sh     # Mise à jour des modules RAG
```
