# Judi-Expert — Répartition des régions AWS

## Principe

| Région | Ressources | Raison |
|--------|-----------|--------|
| **eu-west-1** (Irlande) | S3 tfstate, ECR | Services de stockage existants, pas de nécessité de migrer |
| **us-east-1** (Virginie) | ACM (certificats SSL) | Requis par CloudFront pour les certificats HTTPS |
| **eu-west-3** (Paris) | Tout le reste (+ S3 assets) | Région principale de l'infra runtime (latence France) |

## Détail par service

### eu-west-1 — Stockage et registre

- **S3 `tfstates-059247592146-s3bucket`** — Backend Terraform (state distant)
- **S3 `judi-expert-assets-eu-west-3`** — Packages Site Client (.exe, .tar.gz), images Docker archivées
- **ECR `judi-expert/central-backend`** — Images Docker du backend
- **ECR `judi-expert/central-frontend`** — Images Docker du frontend
- **IAM User `judi-expert-production-backend-s3`** — Accès presigned URLs S3

### us-east-1 — Certificats

- **ACM Certificate** — SSL pour `judi-expert.fr` + `www.judi-expert.fr` (imposé par CloudFront)

### eu-west-3 — Infrastructure runtime

- **Cognito User Pool** — Authentification des experts
- **Lightsail Instance** — Serveur applicatif (Docker Compose)
- **RDS PostgreSQL** — Base de données
- **Route 53** — Zone DNS `judi-expert.fr`
- **CloudFront** — CDN / reverse proxy HTTPS
- **Lambda + EventBridge** — Cron vérification abonnements
- **Secrets Manager** — Token cron
- **VPC + Peering** — Réseau privé RDS ↔ Lightsail

## Configuration dans le code

| Fichier | Variable | Valeur |
|---------|----------|--------|
| `terraform/terraform.tfvars` | `aws_region` | `eu-west-3` |
| `terraform/backend.tf` | `region` | `eu-west-1` |
| `terraform/providers.tf` | provider `aws` (default) | `eu-west-3` |
| `terraform/providers.tf` | provider `aws.us_east_1` | `us-east-1` |
| `terraform/providers.tf` | provider `aws.eu_west_1` | `eu-west-1` |
| `central-site/.env` | `AWS_REGION` | `eu-west-3` |
| `central-site/.env.aws` | `AWS_REGION` | `eu-west-3` |
| `scripts/push-ecr.sh` | `AWS_REGION` | `eu-west-1` |
| `scripts/push-deploy.sh` | `REGION` (Lightsail) | `eu-west-3` |
| `scripts/push-deploy.sh` | `ECR_REGION` | `eu-west-1` |
| `scripts/build.sh` | `ECR_REGISTRY` | `*.eu-west-1.amazonaws.com` |
