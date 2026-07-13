# Judi-Expert — Survival Guide

Guide rapide des commandes essentielles pour le développement et le déploiement.

## Sommaire

1. [Déploiement Local (dev)](#1-déploiement-local-dev)
2. [Déploiement Site Central (dev)](#2-déploiement-site-central-dev)
3. [Déploiement Production (AWS Lightsail)](#3-déploiement-production-aws-lightsail)
4. [Statut et diagnostic en production](#4-statut-et-diagnostic-en-production)
5. [Connexions et comptes](#5-connexions-et-comptes)
6. [Packaging du Site Client (installateur)](#6-packaging-du-site-client-installateur)
7. [Migrations base de données](#7-migrations-base-de-données)
8. [Gestion des versions](#8-gestion-des-versions)
9. [Git](#9-git)
10. [Cycle de vie d'une mise à jour du Site Client](#10-cycle-de-vie-dune-mise-à-jour-du-site-client)

---

## 1. Déploiement Local (dev)

Toutes les commandes depuis la racine du repo.

### Script tout-en-un (recommandé)

```bash
# Build complet + démarrage
bash scripts-dev/build-and-deploy-client.sh

# Avec rebuild sans cache Docker
bash scripts-dev/build-and-deploy-client.sh --no-cache

# Avec téléchargement du modèle LLM
bash scripts-dev/build-and-deploy-client.sh --pull-llm
```

### Scripts individuels

```bash
# Démarrer le Site Client (5 conteneurs : frontend, backend, OCR, LLM, RAG)
bash scripts-dev/dev-client-start.sh

# Avec rebuild des images Docker
bash scripts-dev/dev-client-start.sh --build

# Avec pull du modèle LLM (Mistral 7B)
bash scripts-dev/dev-client-start.sh --pull-llm

# Arrêter
bash scripts-dev/dev-client-stop.sh

# Redémarrer
bash scripts-dev/dev-client-restart.sh

# Statut des conteneurs
bash scripts-dev/dev-client-status.sh
```

**URLs locales :**
- Frontend : http://localhost:3000
- Backend API : http://localhost:8000
- OCR : http://localhost:8001
- Ollama (LLM) : http://localhost:11434
- Qdrant (RAG) : http://localhost:6333

---

## 2. Déploiement Site Central (dev)

```bash
# Démarrer le Site Central (3 conteneurs : PostgreSQL, backend, frontend)
bash scripts-dev/dev-central-start.sh

# Avec rebuild
bash scripts-dev/dev-central-start.sh --build

# Arrêter
bash scripts-dev/dev-central-stop.sh

# Redémarrer
bash scripts-dev/dev-central-restart.sh

# Statut
bash scripts-dev/dev-central-status.sh
```

**URLs Site Central dev :**
- Frontend : http://localhost:3001
- Backend API + Docs : http://localhost:8002/docs
- PostgreSQL : localhost:5433

---

## 3. Déploiement Production (AWS Lightsail)

### Script tout-en-un (recommandé)

```bash
# Déploiement complet : Terraform + Build + Push + Deploy
bash central-site/scripts/build-and-deploy-aws.sh

# Sans Terraform (infra déjà à jour)
bash central-site/scripts/build-and-deploy-aws.sh --skip-terraform

# Sans rebuild (images déjà buildées)
bash central-site/scripts/build-and-deploy-aws.sh --skip-build
```

### Étapes individuelles

```bash
# 1. Build des images Docker (backend + frontend)
bash central-site/scripts/build.sh

# 2. Push vers ECR (tag version + latest)
bash central-site/scripts/push-ecr.sh

# 3. Deploy sur Lightsail (pull + restart + migrations)
bash central-site/scripts/push-deploy.sh
```

**Prérequis :**
- Docker Desktop lancé
- AWS CLI configuré (`aws configure`)
- GitHub CLI authentifié (`gh auth login`) — pour le token des dépendances privées
- Terraform installé (si --skip-terraform n'est pas utilisé)

---

## 4. Statut et diagnostic en production

```bash
# SSH vers l'instance
ssh -i central-site/scripts/lightsail-key.pem ec2-user@52.213.106.237

# Logs des conteneurs (depuis l'instance)
cd /opt/judi-expert && sudo docker compose logs -f

# Logs backend uniquement
cd /opt/judi-expert && sudo docker compose logs --tail=50 backend

# Redémarrer un service
cd /opt/judi-expert && sudo docker compose restart backend

# Statut
cd /opt/judi-expert && sudo docker compose ps
```

**URLs production :**
- Site : https://www.judi-expert.fr
- IP directe : http://52.213.106.237
- Backend health check : http://52.213.106.237:8000/health

---

## 5. Connexions et comptes

### Site Central — Admin

| Champ | Valeur |
|-------|--------|
| Email | `admin@judi-expert.fr` |
| Mot de passe | `JudiAdmin2026!` |

### Base de données PostgreSQL (production RDS)

| Champ | Valeur |
|-------|--------|
| Host | `judi-expert-production-db.c27j5ex6h65s.eu-west-1.rds.amazonaws.com` |
| Port | `5432` |
| DB | `judi_expert` |
| User | `judi_admin` |
| Password | `JudiExpert2026!Prod` |

### Site Client

L'auth locale passe par le Site Central (pas de compte local indépendant).
Se connecter avec le même email/password que le compte expert sur le Site Central.

### SMTP (notifications)

| Champ | Valeur |
|-------|--------|
| Host | `mail.gandi.net:587` |
| User | `admin@judi-expert.fr` |
| Password | `Jm0ntiel$1?` |

---

## 6. Packaging du Site Client (installateur)

Toutes les commandes depuis la racine du repo.

### Mode Production (défaut)

L'installateur se connecte au Site Central sur `https://www.judi-expert.fr`.

```bash
# Tous les OS (Windows + macOS + Linux), mode prod
bash central-site/app_client_package/package.sh

# Windows uniquement, mode prod
bash central-site/app_client_package/package.sh windows

# macOS + Linux
bash central-site/app_client_package/package.sh macos linux

# Sans rebuild des images Docker (utilise le cache)
bash central-site/app_client_package/package.sh --skip-build windows

# Sans ré-export des images (encore plus rapide)
bash central-site/app_client_package/package.sh --skip-build --skip-export windows

# Forcer une version spécifique
bash central-site/app_client_package/package.sh --version 2.0.0 windows
```

### Mode Local (dev)

L'installateur se connecte au Site Central local sur `http://host.docker.internal:8002`.
Utile pour tester l'installateur en mode dev sans dépendre du serveur AWS.

```bash
# Windows, mode local (dev)
bash central-site/app_client_package/package.sh --mode local windows

# Rapide : sans rebuild ni ré-export, mode local
bash central-site/app_client_package/package.sh --skip-build --skip-export --mode local windows

# Tous les OS, mode local
bash central-site/app_client_package/package.sh --mode local all
```

### Comportement lors d'une mise à jour (PC avec installation existante)

L'installateur détecte automatiquement une installation existante dans `C:\judi-expert\` :

1. **Arrêt** des conteneurs Docker en cours
2. **Backup horodaté** — les données utilisateur (`.env` + `data/`) sont copiées dans `_backup-YYYYMMDD-HHmm/` (jamais écrasé, jamais supprimé automatiquement)
3. **Écrasement** des fichiers `config/`, `scripts/`, `docker-images/` par la nouvelle version
4. **Restauration** du `.env` et de `data/` depuis le backup
5. **Raccourci Bureau** — recréé au même emplacement, reste fonctionnel

Le backup horodaté est conservé indéfiniment comme filet de sécurité. L'expert peut le supprimer manuellement une fois satisfait du bon fonctionnement.

> **Note** : pas de désinstallation préalable nécessaire. C'est une mise à jour in-place.

### Output

Les installateurs sont générés dans :
```
central-site/app_client_package/output/
├── judi-expert-installer-{version}-windows.exe        # mode prod
├── judi-expert-installer-{version}-dev-windows.exe    # mode local
├── judi-expert-installer-{version}-macos.sh
└── judi-expert-installer-{version}-linux.sh
```

### Prérequis

- Docker Desktop lancé
- NSIS installé (pour Windows) : https://nsis.sourceforge.io/
- Version définie dans `client-site/VERSION` (ligne 1 = semver)

---

## 7. Migrations base de données

```bash
# Local (SQLite)
cd client-site/web/backend && alembic upgrade head

# Central dev (PostgreSQL local)
cd central-site/web/backend && alembic upgrade head

# Nouvelle migration
cd <site>/web/backend && alembic revision --autogenerate -m "description"
```

En production, les migrations sont exécutées automatiquement par `push-deploy.sh`.

---

## 8. Gestion des versions

### Format du fichier VERSION

Chaque site possède un fichier `VERSION` à sa racine :
- `client-site/VERSION`
- `central-site/VERSION`

**Format strict (2 lignes) :**

```
1.0.1
6 juillet 2026
```

- **Ligne 1** : numéro de version sémantique uniquement (`x.y.z`). Pas de texte, pas d'espaces, pas de date. Ce numéro est utilisé comme tag Docker — tout caractère spécial ou espace provoquera une erreur de build.
- **Ligne 2** : date de publication en texte libre (ex: `6 juillet 2026`, `2026-07-06`, `Juin 2026`). Ce champ est affiché dans l'API `/health` et dans le footer, mais n'est pas utilisé par Docker.

### Règles

- Ne jamais mettre la date sur la ligne 1
- Ne jamais mettre d'espace ou de tiret dans le numéro de version
- Formats valides pour la ligne 1 : `1.0.0`, `2.1.3`, `0.9.0-beta`
- Formats invalides : `1.0.1 - 6 juillet 2026`, `v1.0.1`, `1.0.1 (2026)`

### Lecture au démarrage

Le backend lit `/app/VERSION` au démarrage (copié dans l'image Docker par `build.sh`).
Le service `version_reader.py` parse les 2 lignes et expose :
- `APP_VERSION` → ligne 1 (numéro)
- `APP_VERSION_DATE` → ligne 2 (date texte)

---

## 9. Git

```bash
# Format de commit
type(scope): description

# Types : feat, fix, docs, style, refactor, test, chore
# Exemples :
git commit -m "feat(pea-editor): ajout palette d'injection annotations"
git commit -m "fix(step1): correction extraction questions multi-lignes"
git commit -m "chore(deploy): ajout tag latest dans push-ecr"
```

---

## 10. Cycle de vie d'une mise à jour du Site Client

### Vue d'ensemble du processus

```
┌─────────────┐    ┌─────────────┐    ┌──────────────┐    ┌───────────────┐
│  Développer │───▶│  Valider    │───▶│  Publier     │───▶│  Mise à jour  │
│  (repo)     │    │  (dev)      │    │  (prod)      │    │  (PC expert)  │
└─────────────┘    └─────────────┘    └──────────────┘    └───────────────┘
```

### Étape 1 : Développement (repo)

1. Modifier le code dans `client-site/`
2. Tester localement avec `bash scripts-dev/dev-client-start.sh --build`
3. Bumper la version dans `client-site/VERSION` (ligne 1 = semver, ligne 2 = date)
4. Commit + push sur la branche

### Étape 2 : Validation en dev (package local)

Générer un installateur en mode local pour tester le packaging :

```bash
bash central-site/app_client_package/package.sh --mode local windows
```

Cela produit `judi-expert-installer-{version}-dev-windows.exe` qui communique avec le Site Central local (`http://host.docker.internal:8002`). Ce suffixe `-dev` distingue clairement l'exe dev de l'exe prod.

Installer sur un PC de test et vérifier que tout fonctionne.

### Étape 3 : Publication en production

#### 3a. Générer le package prod

```bash
bash central-site/app_client_package/package.sh windows
```

Produit `judi-expert-installer-{version}-windows.exe` (mode prod, connecté à `https://www.judi-expert.fr`).

#### 3b. Uploader sur S3

L'upload est automatique si `--publish` est utilisé (ou via `--skip-upload` désactivé par défaut).
Le fichier est uploadé sur :
```
s3://judi-expert-production-assets/packages/client/judi-expert-installer-{version}-windows.exe
```

L'endpoint `GET /api/downloads/app` (authentifié) génère un **presigned URL S3** valide 4h pour l'expert. Pas besoin d'accès direct au bucket.

#### 3c. Publier la version via l'API admin du Site Central

**Méthode recommandée — une seule commande :**

```bash
# Tout-en-un : build + upload S3 + publication
bash central-site/scripts/publish-client-package.sh

# Avec réinstallation complète + notes
bash central-site/scripts/publish-client-package.sh --update-type full --release-notes "Nouvelle config Docker"

# Test en local
bash central-site/scripts/publish-client-package.sh --mode local
```

Le script :
1. Se connecte automatiquement au Site Central (admin)
2. Génère le package
3. Upload sur S3
4. Publie la version

**Credentials admin** (3 méthodes, par priorité) :
- Fichier `.env.publish` à la racine du repo (non versionné)
- Variables d'environnement `JUDI_ADMIN_EMAIL` / `JUDI_ADMIN_PASSWORD`
- Saisie interactive du mot de passe

### Étape 4 : Mise à jour automatique côté PC expert

Le processus est **semi-automatique** :

1. **Détection** — À chaque accès, le backend du Site Client appelle `GET /api/version` sur le Site Central (uniquement pendant les heures ouvrables 8h-20h)
2. **Comparaison** — Si `latest_version` > `current_version` ET `mandatory=true`, le frontend affiche une notification de mise à jour
3. **Selon le `update_type` retourné :**

   **Type `images` (mise à jour légère)** — seuls les conteneurs changent :
   - Le Site Client télécharge les nouvelles images Docker depuis `download_url`
   - `docker load` → arrêt → redémarrage
   - Transparent pour l'expert (quelques minutes)

   **Type `full` (réinstallation complète)** — la config/scripts/compose changent :
   - L'expert voit un écran "Téléchargez le nouvel installateur"
   - Il clique le lien, télécharge le `.exe`, et le relance
   - L'installateur fait un backup horodaté puis écrase les fichiers
   - Ses données sont préservées automatiquement

> **Note** : si le Site Central est hors heures ouvrables ou injoignable, la vérification retourne silencieusement `update_available=false`. L'expert continue de travailler normalement.

### Quand utiliser `images` vs `full` ?

| Ce qui a changé | `update_type` |
|-----------------|---------------|
| Code backend/frontend/OCR (images Docker) | `images` |
| `docker-compose.yml` (services, ports, volumes) | `full` |
| `.env` (nouvelles variables requises) | `full` |
| `amorce.bat` / scripts de lancement | `full` |
| `ollama-entrypoint.sh` | `full` |
| Ajout/suppression d'un conteneur | `full` |

### Résumé des artefacts

| Artefact | Fichier | Usage |
|----------|---------|-------|
| Installateur dev | `judi-expert-installer-{v}-dev-windows.exe` | Test local (→ host.docker.internal:8002) |
| Installateur prod | `judi-expert-installer-{v}-windows.exe` | Distribution aux experts (→ judi-expert.fr) |
| Version publiée | Table `app_version` (Site Central) | Déclenche la mise à jour chez les experts |
| Images Docker | `.tar` dans l'installateur | Chargées au premier install ou lors d'update |
