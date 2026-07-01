# Judi-Expert — Survival Guide

Guide rapide des commandes essentielles pour le développement et le déploiement.

---

## 1. Déploiement Local (dev)

Toutes les commandes depuis la racine du repo.

```bash
# Démarrer l'Application Locale (5 conteneurs : frontend, backend, OCR, LLM, RAG)
bash scripts-dev/dev-local-start.sh

# Avec rebuild des images Docker
bash scripts-dev/dev-local-start.sh --build

# Avec pull du modèle LLM (Mistral 7B)
bash scripts-dev/dev-local-start.sh --pull-llm

# Arrêter
bash scripts-dev/dev-local-stop.sh

# Redémarrer
bash scripts-dev/dev-local-restart.sh

# Statut des conteneurs
bash scripts-dev/dev-local-status.sh
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

Les 3 étapes, depuis la racine du repo :

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

### Application Locale

L'auth locale passe par le Site Central (pas de compte local indépendant).
Se connecter avec le même email/password que le compte expert sur le Site Central.

### SMTP (notifications)

| Champ | Valeur |
|-------|--------|
| Host | `mail.gandi.net:587` |
| User | `admin@judi-expert.fr` |
| Password | `Jm0ntiel$1?` |

---

## 6. Migrations base de données

```bash
# Local (SQLite)
cd local-site/web/backend && alembic upgrade head

# Central dev (PostgreSQL local)
cd central-site/web/backend && alembic upgrade head

# Nouvelle migration
cd <site>/web/backend && alembic revision --autogenerate -m "description"
```

En production, les migrations sont exécutées automatiquement par `push-deploy.sh`.

---

## 7. Versions

Les fichiers VERSION sont à la racine de chaque site :
- `local-site/VERSION` — version de l'Application Locale
- `central-site/VERSION` — version du Site Central

Le backend lit `/app/VERSION` au démarrage (copié dans l'image Docker par `build.sh`).

---

## 8. Git

```bash
# Format de commit
type(scope): description

# Types : feat, fix, docs, style, refactor, test, chore
# Exemples :
git commit -m "feat(pea-editor): ajout palette d'injection annotations"
git commit -m "fix(step1): correction extraction questions multi-lignes"
git commit -m "chore(deploy): ajout tag latest dans push-ecr"
```
