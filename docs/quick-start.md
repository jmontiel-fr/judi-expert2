# Quick Start — Judi-Expert

Guide de démarrage rapide pour lancer le Site Central (en local ou sur AWS) et installer/configurer l'Application Locale.

> Pour la définition des termes et acronymes, consultez le [Glossaire & Workflow](glossaire-workflow.md).

---

## Organisation du dépôt

Le dépôt contient **deux applications distinctes** dans des dossiers de premier niveau :

| Dossier | Application | Rôle | Tourne sur |
|---------|-------------|------|------------|
| `local-site/` | **Application Locale** | Workflow d'expertise (OCR, LLM, RAG, rapports). Toutes les données restent sur le PC. | PC de l'expert (Docker Compose) |
| `central-site/` | **Site Central** | Inscription, paiements Stripe, distribution corpus, administration. | AWS (prod) **ou** en local via `docker-compose.dev.yml` (dev) |

### Les trois environnements exécutables

| Environnement | Commande de lancement | URL |
|---------------|----------------------|-----|
| Application Locale | `local-site/scripts/start.sh` | `localhost:3000` (web) / `:8000` (api) |
| Site Central — dev local | `docker compose -f central-site/docker-compose.dev.yml up -d` | `localhost:3001` |
| Site Central — prod AWS | `central-site/scripts/deploy.sh` | Domaine AWS configuré |

---

## Table des matières

1. [Prérequis](#1-prérequis)
2. [Démarrer le Site Central en local](#2-démarrer-le-site-central-en-local)
3. [Déployer le Site Central sur AWS](#3-déployer-le-site-central-sur-aws)
4. [Installer l'Application Locale](#4-installer-lapplication-locale)
5. [Configurer la communication Local ↔ Central](#5-configurer-la-communication-local--central)
6. [Vérification de bout en bout](#6-vérification-de-bout-en-bout)
7. [Commandes utiles](#7-commandes-utiles)

---

## 1. Prérequis

### Outils communs

| Outil | Version min. | Vérification |
|-------|-------------|--------------|
| Docker | 24.x | `docker --version` |
| Docker Compose | 2.x | `docker compose version` |
| Git | 2.x | `git --version` |
| Python | 3.11+ | `python --version` |
| Node.js | 18+ | `node --version` |

### Prérequis supplémentaires pour AWS

| Outil | Version min. | Vérification |
|-------|-------------|--------------|
| AWS CLI | 2.x | `aws --version` |
| Terraform | 1.5+ | `terraform --version` |
| Compte AWS | — | `aws sts get-caller-identity` |

### Prérequis PC pour l'Application Locale

L'Application Locale exige au minimum :
- **CPU** : 4 cœurs
- **RAM** : 8 Go
- **Disque** : 50 Go libres
- **Chiffrement** : BitLocker ou équivalent activé

---

## 2. Démarrer le Site Central en local

Le Site Central peut tourner en local via Docker Compose pour le développement et les tests.

### 2.1 Cloner le dépôt

```bash
git clone <url-du-depot> judi-expert
cd judi-expert
```

### 2.2 Configurer l'environnement

```bash
cp central-site/.env central-site/.env.local
```

Éditer `central-site/.env.local` avec les valeurs de test :

```dotenv
# Base de données locale (PostgreSQL via Docker)
DATABASE_URL=postgresql://judi:judi_dev@db:5432/judi_expert

# Stripe (mode test)
STRIPE_SECRET_KEY=sk_test_VOTRE_CLE
STRIPE_PUBLISHABLE_KEY=pk_test_VOTRE_CLE
STRIPE_WEBHOOK_SECRET=whsec_VOTRE_SECRET
STRIPE_PRICE_TICKET=price_VOTRE_PRIX

# Cognito — en local, utiliser un mock ou un User Pool de test
COGNITO_USER_POOL_ID=eu-west-3_XXXXXX
COGNITO_APP_CLIENT_ID=XXXXXX

# reCAPTCHA (clés de test Google)
RECAPTCHA_SITE_KEY=6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI
RECAPTCHA_SECRET_KEY=6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe

# Admin
ADMIN_EMAIL=admin@judi-expert.fr
ADMIN_DEFAULT_PASSWORD=change-me

APP_ENV=development
APP_URL=http://localhost:3000
```

### 2.3 Lancer le Site Central en local

Créer un fichier `docker-compose.dev.yml` à la racine du projet (ou utiliser celui existant) pour le Site Central :

```bash
# Depuis la racine du projet
docker compose -f central-site/docker-compose.dev.yml up -d
```

Ou lancer manuellement les composants :

```bash
# 1. Démarrer PostgreSQL
docker run -d --name judi-db \
  -e POSTGRES_USER=judi \
  -e POSTGRES_PASSWORD=judi_dev \
  -e POSTGRES_DB=judi_expert \
  -p 5432:5432 \
  postgres:16-alpine

# 2. Lancer les migrations
cd central-site/web/backend
pip install -r requirements.txt
alembic upgrade head

# 3. Démarrer le backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 4. Démarrer le frontend (dans un autre terminal)
cd central-site/web/frontend
npm install
npm run dev
```

### 2.4 Vérifier le Site Central local

- Frontend : http://localhost:3000
- Backend API : http://localhost:8000/docs (Swagger UI)
- Compte admin par défaut : `admin@judi-expert.fr` / `change-me`

---

## 3. Déployer le Site Central sur AWS

### 3.1 Configurer les variables AWS

Éditer `central-site/.env` :

```dotenv
AWS_REGION=eu-west-3
AWS_ACCOUNT_ID=123456789012
ECR_REGISTRY=123456789012.dkr.ecr.eu-west-3.amazonaws.com

DATABASE_URL=postgresql://user:password@host:5432/judi_expert

COGNITO_USER_POOL_ID=eu-west-3_XXXXXXX
COGNITO_APP_CLIENT_ID=XXXXXXXXXXXXXXX

STRIPE_SECRET_KEY=sk_live_VOTRE_CLE
STRIPE_PUBLISHABLE_KEY=pk_live_VOTRE_CLE
STRIPE_WEBHOOK_SECRET=whsec_VOTRE_SECRET
STRIPE_PRICE_TICKET=price_VOTRE_PRIX

SES_SENDER_EMAIL=no-reply@judi-expert.fr
APP_URL=https://www.judi-expert.fr
```

### 3.2 Déployer l'infrastructure Terraform

```bash
cd central-site/scripts

# Déployer VPC, RDS, ECS, Cognito, ALB, CloudFront, ECR, etc.
./deploy.sh
```

Le script exécute `terraform init`, `plan` et `apply`. Les outputs Terraform fournissent les ARN et endpoints nécessaires.

### 3.3 Build et push des images Docker

```bash
cd central-site/scripts

# Build des images de production
./build.sh v1.0.0

# Push vers ECR
./push-ecr.sh v1.0.0
```

### 3.4 Publier le module RAG psychologie

```bash
cd central-site/scripts

# Build et push de l'image RAG du domaine psychologie
./update-rag.sh psychologie v1.0.0
```

### 3.5 Vérifier le déploiement

```bash
cd central-site/scripts

# Vérifier l'état des services
./site-status.sh
```

Résultat attendu :
```
  ── ECS Fargate ──
  ● ECS : ACTIF — 1/1 tâches en cours (ACTIVE)

  ── RDS PostgreSQL ──
  ● RDS : DISPONIBLE (available)

  ── ALB (Load Balancer) ──
  ● ALB : ROUTAGE NORMAL (2 règles actives)
```

### 3.6 Gestion du Site Central (arrêt/démarrage)

```bash
# Arrêter le Site Central (maintenance ou économie)
./site-stop.sh

# Redémarrer le Site Central
./site-start.sh

# Vérifier l'état
./site-status.sh
```

Le scheduler EventBridge gère automatiquement l'arrêt à 20h et le démarrage à 8h (Europe/Paris).

---

## 4. Installer l'Application Locale

### 4.1 Build des images Docker locales

```bash
cd local-site/scripts

# Build des 3 images custom (judi-web-backend, judi-web-frontend, judi-ocr)
./build.sh
```

Les images `ollama/ollama:latest` (judi-llm) et `qdrant/qdrant:latest` (judi-rag) sont téléchargées automatiquement au premier démarrage.

### 4.2 Configurer l'environnement local

Éditer `local-site/.env` :

```dotenv
# Base de données locale (SQLite)
DATABASE_URL=sqlite:///./data/judi-expert.db

# Services internes Docker
LLM_HOST=http://judi-llm:11434
LLM_MODEL=mistral:7b-instruct-v0.3
QDRANT_HOST=http://judi-rag:6333
OCR_HOST=http://judi-ocr:8001

# JWT local
JWT_SECRET=GENEREZ_UN_SECRET_ALEATOIRE
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440

# Domaine d'expertise
DOMAINE=psychologie
```

### 4.3 Démarrer l'Application Locale

```bash
cd local-site/scripts

# Démarrer les 4 conteneurs
./start.sh
```

Services disponibles :
| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | Interface PWA |
| Backend API | http://localhost:8000 | API FastAPI |
| LLM (Ollama) | http://localhost:11434 | Mistral 7B |
| RAG (Qdrant) | http://localhost:6333 | Base vectorielle |
| OCR | http://localhost:8001 | Extraction PDF |

Au premier démarrage, Ollama télécharge automatiquement le modèle Mistral 7B (~4 Go). Cela peut prendre plusieurs minutes.

### 4.4 Configuration initiale

1. Ouvrir http://localhost:3000
2. Définir un mot de passe local et sélectionner le domaine (ex: psychologie)
3. Installer le module RAG depuis la page Configuration
4. Uploader le TPE et le Template Rapport (les fichiers exemples psychologie sont proposés par défaut)

---

## 5. Configurer la communication Local ↔ Central

L'Application Locale communique avec le Site Central uniquement pour :
- **Vérifier les tickets** lors de la création d'un dossier
- **Télécharger les modules RAG** depuis ECR

Toutes les données d'expertise restent exclusivement en local.

### 5.1 Pointer vers le Site Central local (développement)

Si le Site Central tourne en local, éditer `local-site/.env` :

```dotenv
# Pointer vers le Site Central local
SITE_CENTRAL_URL=http://host.docker.internal:8000
```

`host.docker.internal` permet aux conteneurs Docker d'accéder aux services de la machine hôte.

Sur Linux, ajouter dans `docker-compose.yml` :

```yaml
services:
  judi-web-backend:
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

### 5.2 Pointer vers le Site Central AWS (production)

Pour la production, éditer `local-site/.env` :

```dotenv
# Pointer vers le Site Central AWS
SITE_CENTRAL_URL=https://www.judi-expert.fr
```

### 5.3 Redémarrer après modification

```bash
cd local-site/scripts
./restart.sh
```

### 5.4 Gestion de l'indisponibilité du Site Central

Le Site Central fonctionne de 8h à 20h (heure de Paris). En dehors de ces horaires :
- Les étapes d'expertise (Step0 → Step3) fonctionnent normalement (tout est local)
- Le ChatBot fonctionne normalement (LLM + RAG locaux)
- La création de dossier (vérification de ticket) affiche un message d'indisponibilité temporaire

---

## 6. Vérification de bout en bout

### 6.1 Tester le flux complet

1. **Site Central** : créer un compte expert sur http://localhost:3000 (ou l'URL AWS)
2. **Site Central** : acheter un ticket via Stripe (mode test)
3. **Application Locale** : créer un dossier avec le ticket reçu par email
4. **Step0** : uploader un PDF-scan de réquisition → extraction OCR → Markdown
5. **Step1** : générer le plan d'entretien (QMEC) → valider
6. **Step2** : uploader NE.docx et REB.docx → valider
7. **Step3** : générer REF + RAUX → valider → archive ZIP

### 6.2 Vérifier la communication

```bash
# Depuis le conteneur backend local, tester la connexion au Site Central
docker exec judi-web-backend curl -sf ${SITE_CENTRAL_URL}/health
```

### 6.3 Lancer les tests

```bash
# Tests unitaires et par propriétés
python -m pytest tests/unit/ tests/property/ -v

# Tests d'intégration (nécessite Docker Compose actif)
python -m pytest tests/integration/ -v

# Tests de fumée
python -m pytest tests/smoke/ -v
```

---

## 7. Commandes utiles

### Application Locale

| Commande | Description |
|----------|-------------|
| `local-site/scripts/build.sh` | Build des images Docker locales |
| `local-site/scripts/start.sh` | Démarrer tous les conteneurs |
| `local-site/scripts/stop.sh` | Arrêter tous les conteneurs |
| `local-site/scripts/restart.sh` | Redémarrer tous les conteneurs |
| `docker logs judi-web-backend` | Logs du backend |
| `docker logs judi-llm` | Logs du LLM (Ollama) |

### Site Central AWS

| Commande | Description |
|----------|-------------|
| `central-site/scripts/build.sh [tag]` | Build des images de production |
| `central-site/scripts/push-ecr.sh [tag]` | Push vers ECR |
| `central-site/scripts/deploy.sh` | Déploiement Terraform |
| `central-site/scripts/update-rag.sh <domaine> [tag]` | Mise à jour image RAG |
| `central-site/scripts/site-start.sh` | Démarrer le Site Central |
| `central-site/scripts/site-stop.sh` | Arrêter le Site Central |
| `central-site/scripts/site-status.sh` | État des services AWS |

### Dépannage

| Problème | Solution |
|----------|----------|
| Ollama ne démarre pas | Vérifier l'espace disque (>10 Go pour le modèle) |
| Ticket refusé | Vérifier `SITE_CENTRAL_URL` dans `.env` et que le Site Central est actif |
| OCR échoue | Vérifier que le conteneur `judi-ocr` est healthy : `docker ps` |
| RAG non configuré | Aller dans Configuration → installer le module RAG |
| Site Central indisponible | Vérifier les horaires (8h-20h) ou lancer `site-start.sh` |
