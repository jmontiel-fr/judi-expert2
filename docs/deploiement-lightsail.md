# Déploiement Judi-Expert — Lightsail + RDS

## Architecture de production

```
Internet
    │
    ▼
┌─────────────────────────────────────────┐
│  AWS Lightsail (2 Go RAM, 12 $/mois)   │
│                                         │
│  ┌─────────┐  ┌─────────┐  ┌────────┐  │
│  │  Caddy   │  │ Backend │  │Frontend│  │
│  │ :80/:443 │→ │ FastAPI │  │Next.js │  │
│  │  HTTPS   │  │  :8000  │  │ :3000  │  │
│  └─────────┘  └────┬────┘  └────────┘  │
│                     │                    │
└─────────────────────┼────────────────────┘
                      │ VPC Peering
                      ▼
              ┌──────────────┐
              │  AWS RDS     │
              │  PostgreSQL  │
              │  db.t4g.micro│
              │  16 $/mois   │
              └──────────────┘
```

## Coût mensuel estimé

| Service | Coût |
|---------|------|
| Lightsail 2 Go RAM | 12 $/mois |
| RDS db.t4g.micro (20 Go) | 16 $/mois |
| Route 53 | 0.54 $/mois |
| Cognito | 0 $/mois (tier gratuit) |
| **TOTAL** | **~29 $/mois** |

## Prérequis

- Compte AWS avec accès Lightsail et RDS
- Nom de domaine configuré (Route 53 ou autre)
- Clés Stripe (live)
- Compte Gmail avec mot de passe d'application (voir docs/smtp-gmail.md)
- Clés reCAPTCHA V2 (voir https://www.google.com/recaptcha/admin)

## Étape 1 : Créer l'instance RDS

```bash
# Via AWS Console ou CLI
aws rds create-db-instance \
  --db-instance-identifier judi-expert-db \
  --db-instance-class db.t4g.micro \
  --engine postgres \
  --engine-version 16 \
  --master-username judi \
  --master-user-password VOTRE_MOT_DE_PASSE \
  --allocated-storage 20 \
  --storage-type gp3 \
  --backup-retention-period 7 \
  --no-multi-az \
  --vpc-security-group-ids sg-XXXXXXXX \
  --region eu-west-3
```

Créer la base de données :
```sql
CREATE DATABASE judi_expert;
```

Noter l'endpoint RDS (ex: `judi-expert-db.xxxx.eu-west-3.rds.amazonaws.com`).

## Étape 2 : Créer l'instance Lightsail

1. AWS Console → Lightsail → Create instance
2. Région : eu-west-3 (Paris)
3. OS : Ubuntu 22.04 LTS
4. Plan : 2 Go RAM (12 $/mois)
5. Nom : `judi-expert-prod`

## Étape 3 : Configurer le VPC Peering

Pour que Lightsail puisse accéder à RDS :

1. Lightsail Console → Account → Advanced → Enable VPC peering (eu-west-3)
2. RDS Security Group : autoriser le CIDR Lightsail (172.26.0.0/16) sur le port 5432

## Étape 4 : Installer Docker sur Lightsail

```bash
ssh ubuntu@IP_LIGHTSAIL

# Installer Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ubuntu
newgrp docker

# Installer Docker Compose plugin
sudo apt-get install -y docker-compose-plugin

# Vérifier
docker --version
docker compose version
```

## Étape 5 : Déployer l'application

```bash
# Cloner le repo (ou transférer les fichiers)
git clone https://github.com/VOTRE_REPO/judi-expert.git
cd judi-expert/central-site

# Créer le fichier .env.prod
cp .env.prod.example .env.prod
nano .env.prod  # Renseigner toutes les valeurs

# Copier les données (domaines, corpus)
cp -r ../domaines /opt/judi-expert/domaines
cp -r ../corpus /opt/judi-expert/corpus

# Lancer
docker compose -f docker-compose.prod.yml up -d --build

# Vérifier
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f
```

## Étape 6 : Configurer le DNS

Dans Route 53 (ou votre registrar) :
- A record : `judi-expert.fr` → IP statique Lightsail
- A record : `www.judi-expert.fr` → IP statique Lightsail

Attacher une IP statique dans Lightsail Console → Networking → Create static IP.

## Étape 7 : Exécuter les migrations

```bash
docker exec judi-central-backend alembic upgrade head
```

## Mises à jour

```bash
cd judi-expert
git pull
cd central-site
docker compose -f docker-compose.prod.yml up -d --build
docker exec judi-central-backend alembic upgrade head
```

## Sauvegardes

### Base de données (automatique via RDS)
- Backups automatiques quotidiens (rétention 7 jours)
- Snapshots manuels avant les mises à jour : `aws rds create-db-snapshot`

### Fichiers (corpus, domaines)
- Snapshot Lightsail hebdomadaire (automatique si activé)
- Ou backup S3 via cron :
```bash
# Ajouter dans crontab
0 2 * * * aws s3 sync /opt/judi-expert/corpus s3://judi-expert-backup/corpus/
```

## Monitoring

```bash
# Logs en temps réel
docker compose -f docker-compose.prod.yml logs -f

# Statut des conteneurs
docker compose -f docker-compose.prod.yml ps

# Espace disque
df -h
```

## Migration vers ECS/Fargate

Quand le trafic le justifie (>500 experts), migrer vers ECS/Fargate :
1. Pousser les images Docker vers ECR
2. Créer les task definitions ECS
3. Configurer ALB + target groups
4. Basculer le DNS

Le code Docker est identique — seule l'infrastructure change.
