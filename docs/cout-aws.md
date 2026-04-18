# Estimation des Coûts AWS — Judi-Expert

## Introduction

Ce document estime les coûts mensuels AWS pour le déploiement du Site Central Judi-Expert en production. L'architecture utilise **Lightsail + RDS** pour minimiser les coûts en phase de lancement, avec possibilité de migration vers ECS/Fargate quand le trafic le justifie.

**Hypothèses de dimensionnement :**
- Phase de lancement : 50 à 200 experts inscrits
- Trafic modéré : ~1 000 à 5 000 visites/mois
- ~100 à 500 tickets vendus/mois
- Emails via Gmail SMTP (pas de SES)

---

## Architecture de production

```
Internet → Lightsail (Caddy HTTPS + Docker) → RDS PostgreSQL
```

- **Lightsail** : instance Docker avec Caddy (reverse proxy HTTPS), backend FastAPI, frontend Next.js
- **RDS** : PostgreSQL managé avec backups automatiques
- **Cognito** : authentification (tier gratuit)
- **Gmail SMTP** : envoi d'emails (tickets, notifications)

---

## Services AWS utilisés

### 1. Lightsail (Compute — Backend + Frontend + Caddy)

Une seule instance Lightsail fait tourner Docker Compose avec 3 conteneurs (Caddy, backend, frontend). Remplace ECS Fargate + ALB.

| Plan | vCPU | RAM | SSD | Transfert | Coût |
|------|------|-----|-----|-----------|------|
| 2 Go (recommandé lancement) | 1 | 2 Go | 60 Go | 3 To | **12 $/mois** |
| 4 Go (croissance) | 2 | 4 Go | 80 Go | 4 To | **24 $/mois** |
| 8 Go (>500 experts) | 2 | 8 Go | 160 Go | 5 To | **48 $/mois** |

**IP statique Lightsail** : gratuite (tant qu'attachée à une instance).

### 2. RDS PostgreSQL

Base de données relationnelle managée avec backups automatiques.

| Paramètre | Valeur |
|-----------|--------|
| Instance | db.t4g.micro |
| Stockage | 20 Go gp3 |
| Multi-AZ | Non (phase lancement) |
| Backup | 7 jours (automatique) |

**Calcul :**
- Instance db.t4g.micro : ~12.41 $/mois
- Stockage 20 Go gp3 : ~2.30 $/mois
- Backup : ~0.95 $/mois
- **Total RDS : ~16 $/mois**

### 3. AWS Cognito (Authentification)

| Paramètre | Valeur |
|-----------|--------|
| MAU | 50 à 200 |
| Tier gratuit | 50 000 MAU |

**Total Cognito : 0 $/mois**

### 4. ECR (Images Docker — modules RAG)

| Paramètre | Valeur |
|-----------|--------|
| Stockage | ~15 Go |
| Transfert | ~50 Go/mois |

**Calcul :**
- Stockage : 15 Go × 0.10 $ = ~1.50 $/mois
- Transfert : 50 Go × 0.09 $ = ~4.50 $/mois
- **Total ECR : ~6 $/mois**

### 5. Route 53 (DNS)

- Zone hébergée : 0.50 $/mois
- Requêtes : ~0.04 $/mois
- **Total Route 53 : ~0.54 $/mois**

### 6. S3 + CloudFront (optionnel)

Pour les assets statiques et le package installateur.

- S3 : ~0.15 $/mois
- CloudFront : ~2.61 $/mois
- **Total S3 + CloudFront : ~3 $/mois** (optionnel, Caddy peut servir les assets)

### 7. Gmail SMTP (Emails)

Pas de coût AWS. Le compte Gmail est gratuit (500 emails/jour).

**Total emails : 0 $/mois**

---

## Récapitulatif mensuel

| Service | Coût ($/mois) |
|---------|---------------|
| Lightsail 2 Go | 12.00 |
| RDS PostgreSQL db.t4g.micro | 16.00 |
| Cognito | 0.00 |
| ECR | 6.00 |
| Route 53 | 0.54 |
| S3 + CloudFront (optionnel) | 3.00 |
| Gmail SMTP | 0.00 |
| **TOTAL** | **~29-38 $/mois** |

---

## Comparaison avec l'ancienne architecture (ECS/Fargate)

| Poste | ECS/Fargate + ALB | Lightsail + RDS | Économie |
|-------|-------------------|-----------------|----------|
| Compute | ECS ~18 $ | Lightsail ~12 $ | -33% |
| Load Balancer | ALB ~22 $ | Caddy (inclus) 0 $ | -100% |
| Base de données | RDS ~16 $ | RDS ~16 $ | 0% |
| Monitoring | CloudWatch ~6 $ | Docker logs 0 $ | -100% |
| Secrets | Secrets Manager ~2 $ | .env fichier 0 $ | -100% |
| Emails | SES ~0.10 $ | Gmail 0 $ | -100% |
| **TOTAL** | **~74 $/mois** | **~29 $/mois** | **-61%** |

---

## Estimation annuelle

| Scénario | Coût mensuel | Coût annuel |
|----------|-------------|-------------|
| Phase lancement (50 experts) | ~29 $ | ~348 $ |
| Croissance (200 experts) | ~38 $ | ~456 $ |
| Croissance (500 experts, Lightsail 4 Go) | ~50 $ | ~600 $ |
| Migration ECS/Fargate (>500 experts) | ~74-103 $ | ~888-1 236 $ |

---

## Coûts externes (hors AWS)

| Service | Coût |
|---------|------|
| Stripe | 1.5% + 0.25 € par transaction |
| Nom de domaine (judi-expert.fr) | ~10-15 €/an |
| Certificat SSL | Gratuit (Let's Encrypt via Caddy) |
| Compte Gmail | Gratuit |

---

## Seuil de rentabilité infrastructure

Avec un ticket à 49 € HT (58.80 € TTC) :
- Coût Stripe par ticket : ~1.13 € (1.5% + 0.25 €)
- Revenu net par ticket : ~57.67 €
- **Seuil de rentabilité : 1 ticket/mois** couvre l'infrastructure (~29 $)

---

## Optimisations possibles

### Court terme
- **RDS Reserved Instance (1 an)** : ~40% d'économie → ~9.50 $/mois au lieu de 16 $
- **Lightsail 3 ans** : réduction supplémentaire disponible

### Moyen terme (>200 experts)
- **Lightsail 4 Go** : upgrade simple sans migration
- **RDS scale-up** : db.t4g.small si nécessaire

### Long terme (>500 experts)
- **Migration ECS/Fargate** : le code Docker est identique, seule l'infra change
- **ALB + auto-scaling** : pour gérer les pics de trafic
- **RDS Multi-AZ** : haute disponibilité

---

## Plan de migration Lightsail → ECS/Fargate

Quand le trafic dépasse les capacités de Lightsail :

1. Pousser les images Docker vers ECR
2. Créer les task definitions ECS (même Dockerfile)
3. Configurer ALB + target groups
4. Basculer le DNS Route 53
5. Supprimer l'instance Lightsail

Le code applicatif ne change pas — seule l'infrastructure évolue.
