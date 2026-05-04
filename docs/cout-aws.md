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
Internet → CloudFront (HTTPS ACM + cache + DDoS Shield) → Lightsail (Caddy + Docker) → RDS PostgreSQL
```

- **CloudFront** : CDN, terminaison HTTPS (certificat ACM gratuit), protection DDoS (AWS Shield Standard gratuit), cache des assets statiques
- **Lightsail** : instance Docker avec Caddy (reverse proxy HTTP interne), backend FastAPI, frontend Next.js
- **RDS** : PostgreSQL managé avec backups automatiques
- **Cognito** : authentification (tier gratuit)
- **Route 53** : DNS (zone hébergée judi-expert.fr)
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

### 4. Route 53 (DNS)

- Zone hébergée : 0.50 $/mois
- Requêtes : ~0.04 $/mois
- **Total Route 53 : ~0.54 $/mois**

### 5. ECR (Images Docker — déploiement)

Stockage des images Docker du site central pour déploiement rapide sur Lightsail via `docker pull`.

| Paramètre | Valeur |
|-----------|--------|
| Stockage | ~2 Go (backend + frontend) |
| Transfert | intra-région (gratuit) |

**Calcul :**
- Stockage : 2 Go × 0.10 $ = ~0.20 $/mois
- Transfert intra-région : gratuit
- **Total ECR : ~0.20 $/mois**

### 6. CloudFront (CDN + HTTPS)

Terminaison HTTPS, cache des assets statiques, protection DDoS Shield Standard.

| Paramètre | Valeur |
|-----------|--------|
| Requêtes | ~10 000/mois |
| Transfert | < 1 Go/mois |
| Certificat ACM | Gratuit |
| Shield Standard | Gratuit (inclus) |

**Calcul :**
- Tier gratuit : 1 To transfert + 10M requêtes/mois (première année)
- Après tier gratuit : ~0.50 $/mois pour ce trafic
- **Total CloudFront : ~0 $/mois** (tier gratuit largement suffisant)

### 7. S3 (Images Docker App Locale + package installateur)

Stockage des images Docker de l'Application Locale (.tar.gz) téléchargées par le package auto-installable, plus le package installateur lui-même.

| Paramètre | Valeur |
|-----------|--------|
| Stockage | ~5 Go (images Docker + package) |
| Transfert | ~10 Go/mois (installations) |

**Calcul :**
- Stockage : 5 Go × 0.023 $ = ~0.12 $/mois
- Transfert : 10 Go × 0.09 $ = ~0.90 $/mois
- **Total S3 : ~1 $/mois**

### 8. Gmail SMTP (Emails)

Pas de coût AWS. Le compte Gmail est gratuit (500 emails/jour).

**Total emails : 0 $/mois**

---

## Récapitulatif mensuel

| Service | Coût ($/mois) |
|---------|---------------|
| Lightsail 2 Go | 12.00 |
| RDS PostgreSQL db.t4g.micro | 16.00 |
| CloudFront (HTTPS + CDN + DDoS) | 0.00 |
| ACM (certificat SSL) | 0.00 |
| ECR (images Docker déploiement) | 0.20 |
| Cognito | 0.00 |
| Route 53 | 0.54 |
| S3 (images Docker App Locale + package) | 1.00 |
| Gmail SMTP | 0.00 |
| **TOTAL** | **~30 $/mois** |

---

## Comparaison avec l'ancienne architecture (ECS/Fargate)

| Poste | ECS/Fargate + ALB | CloudFront + Lightsail + RDS | Économie |
|-------|-------------------|------------------------------|----------|
| Compute | ECS ~18 $ | Lightsail ~12 $ | -33% |
| Load Balancer | ALB ~22 $ | CloudFront 0 $ (tier gratuit) | -100% |
| HTTPS/SSL | ACM (gratuit avec ALB) | ACM (gratuit avec CloudFront) | 0% |
| DDoS | Shield Standard (gratuit) | Shield Standard (gratuit) | 0% |
| Base de données | RDS ~16 $ | RDS ~16 $ | 0% |
| Monitoring | CloudWatch ~6 $ | Docker logs 0 $ | -100% |
| Secrets | Secrets Manager ~2 $ | .env fichier 0 $ | -100% |
| Emails | SES ~0.10 $ | Gmail 0 $ | -100% |
| **TOTAL** | **~74 $/mois** | **~28 $/mois** | **-62%** |

---

## Estimation annuelle

| Scénario | Coût mensuel | Coût annuel |
|----------|-------------|-------------|
| Phase lancement (50 experts) | ~28 $ | ~336 $ |
| Croissance (200 experts) | ~29 $ | ~348 $ |
| Croissance (500 experts, Lightsail 4 Go) | ~41 $ | ~492 $ |
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
- **Seuil de rentabilité : 1 ticket/mois** couvre l'infrastructure (~28 $)

---

## Optimisations possibles

### Court terme
- **RDS Reserved Instance (1 an)** : ~40% d'économie → ~9.50 $/mois au lieu de 16 $
- **Lightsail 3 ans** : réduction supplémentaire disponible
- **CloudFront** : tier gratuit couvre largement le trafic phase lancement

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
