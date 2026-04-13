# Estimation des Coûts AWS — Judi-Expert

## Introduction

Ce document estime les coûts mensuels AWS pour le déploiement du Site Central Judi-Expert en production. Les estimations sont basées sur les tarifs AWS région eu-west-3 (Paris) en vigueur en 2026. Les coûts sont exprimés en USD/mois.

**Hypothèses de dimensionnement :**
- Phase de lancement : 50 à 200 experts inscrits
- Trafic modéré : ~1 000 à 5 000 visites/mois sur le site
- ~100 à 500 tickets vendus/mois
- Stockage ECR : ~10-20 Go d'images Docker (modules RAG + app locale)

---

## Services AWS utilisés

### 1. ECS Fargate (Site Central — Backend + Frontend)

Le Site Central tourne sur ECS Fargate avec un service Next.js + FastAPI.

| Paramètre | Valeur |
|-----------|--------|
| Nombre de tâches | 1 (min) à 2 (auto-scaling) |
| vCPU par tâche | 0.5 vCPU |
| Mémoire par tâche | 1 Go |
| Heures/mois | 730 h (24/7) |

**Calcul :**
- 1 tâche × 0.5 vCPU × 730 h × 0.04048 $/vCPU/h = ~14.78 $/mois
- 1 tâche × 1 Go × 730 h × 0.004445 $/Go/h = ~3.24 $/mois
- **Total Fargate : ~18 $/mois** (1 tâche) à **~36 $/mois** (2 tâches)

### 2. RDS PostgreSQL

Base de données relationnelle pour les experts, tickets, domaines.

| Paramètre | Valeur |
|-----------|--------|
| Instance | db.t4g.micro |
| Stockage | 20 Go gp3 |
| Multi-AZ | Non (phase lancement) |
| Backup | 7 jours |

**Calcul :**
- Instance db.t4g.micro : ~12.41 $/mois (on-demand)
- Stockage 20 Go gp3 : ~2.30 $/mois
- Backup : ~0.95 $/mois (20 Go × 0.095 $/Go × facteur rétention)
- **Total RDS : ~16 $/mois**

**Option économique :** RDS Aurora Serverless v2 (0.5 ACU min) à ~43 $/mois — plus cher mais auto-scaling. Non recommandé en phase lancement.

### 3. AWS Cognito (Authentification)

| Paramètre | Valeur |
|-----------|--------|
| Utilisateurs actifs/mois (MAU) | 50 à 200 |
| Tier gratuit | 50 000 MAU |

**Calcul :**
- **Total Cognito : 0 $/mois** (tier gratuit largement suffisant)

### 4. ECR (Elastic Container Registry)

Stockage des images Docker : app locale, modules RAG par domaine, site central.

| Paramètre | Valeur |
|-----------|--------|
| Stockage images | ~15 Go |
| Transfert données | ~50 Go/mois (téléchargements experts) |

**Calcul :**
- Stockage : 15 Go × 0.10 $/Go = ~1.50 $/mois
- Transfert sortant : 50 Go × 0.09 $/Go = ~4.50 $/mois (premiers 10 To)
- **Total ECR : ~6 $/mois**

**Note :** Les images RAG contenant le LLM Mistral 7B quantifié (~4-5 Go) représentent le gros du stockage. Le transfert augmentera avec le nombre d'experts.

### 5. S3 (Assets statiques + packages)

| Paramètre | Valeur |
|-----------|--------|
| Stockage | ~5 Go (assets, packages installateur) |
| Requêtes GET | ~10 000/mois |
| Transfert | ~20 Go/mois |

**Calcul :**
- Stockage : 5 Go × 0.023 $/Go = ~0.12 $/mois
- Requêtes GET : 10 000 × 0.0004 $/1000 = ~0.004 $/mois
- Transfert : inclus dans CloudFront
- **Total S3 : ~0.15 $/mois**

### 6. CloudFront (CDN)

| Paramètre | Valeur |
|-----------|--------|
| Transfert données | ~30 Go/mois |
| Requêtes HTTPS | ~50 000/mois |

**Calcul :**
- Transfert : 30 Go × 0.085 $/Go = ~2.55 $/mois
- Requêtes HTTPS : 50 000 × 0.012 $/10 000 = ~0.06 $/mois
- **Total CloudFront : ~2.61 $/mois**

### 7. Application Load Balancer (ALB)

| Paramètre | Valeur |
|-----------|--------|
| Heures ALB | 730 h/mois |
| LCU (Load Balancer Capacity Units) | ~1 LCU |

**Calcul :**
- Heures : 730 × 0.0225 $/h = ~16.43 $/mois
- LCU : 730 × 1 × 0.008 $/LCU/h = ~5.84 $/mois
- **Total ALB : ~22.27 $/mois**

### 8. SES (Simple Email Service) — Envoi tickets par email

| Paramètre | Valeur |
|-----------|--------|
| Emails envoyés | ~500/mois (tickets + notifications) |

**Calcul :**
- 500 emails × 0.10 $/1000 = ~0.05 $/mois
- **Total SES : ~0.10 $/mois**

### 9. CloudWatch (Monitoring + Logs)

| Paramètre | Valeur |
|-----------|--------|
| Logs ingérés | ~5 Go/mois |
| Métriques custom | ~10 |
| Alarmes | ~5 |

**Calcul :**
- Logs : 5 Go × 0.50 $/Go = ~2.50 $/mois
- Métriques : 10 × 0.30 $/métrique = ~3.00 $/mois
- Alarmes : 5 × 0.10 $/alarme = ~0.50 $/mois
- **Total CloudWatch : ~6 $/mois**

### 10. Route 53 (DNS)

| Paramètre | Valeur |
|-----------|--------|
| Zone hébergée | 1 |
| Requêtes DNS | ~100 000/mois |

**Calcul :**
- Zone : 0.50 $/mois
- Requêtes : 100 000 × 0.40 $/million = ~0.04 $/mois
- **Total Route 53 : ~0.54 $/mois**

### 11. Secrets Manager (Clés API Stripe, etc.)

| Paramètre | Valeur |
|-----------|--------|
| Secrets stockés | ~5 (Stripe, Cognito, DB, admin) |

**Calcul :**
- 5 secrets × 0.40 $/secret/mois = ~2.00 $/mois
- **Total Secrets Manager : ~2 $/mois**

---

## Récapitulatif mensuel

| Service | Coût min ($/mois) | Coût max ($/mois) |
|---------|-------------------|-------------------|
| ECS Fargate | 18.00 | 36.00 |
| RDS PostgreSQL | 16.00 | 16.00 |
| AWS Cognito | 0.00 | 0.00 |
| ECR | 6.00 | 10.00 |
| S3 | 0.15 | 0.50 |
| CloudFront | 2.61 | 5.00 |
| ALB | 22.27 | 22.27 |
| SES | 0.10 | 0.50 |
| CloudWatch | 6.00 | 10.00 |
| Route 53 | 0.54 | 0.54 |
| Secrets Manager | 2.00 | 2.00 |
| **TOTAL** | **~74 $/mois** | **~103 $/mois** |

---

## Estimation annuelle

| Scénario | Mode | Coût mensuel | Coût annuel |
|----------|------|-------------|-------------|
| Phase lancement (50 experts) | 24/7 | ~74 $ | ~888 $ |
| Phase lancement (50 experts) | 8h-20h | ~57 $ | ~684 $ |
| Phase lancement (50 experts) | 8h-20h + tier gratuit | ~36 $ | ~432 $ |
| Croissance (200 experts) | 24/7 | ~103 $ | ~1 236 $ |
| Croissance (200 experts) | 8h-20h | ~80 $ | ~960 $ |
| Croissance (500 experts) | 24/7 | ~150 $ | ~1 800 $ |
| Croissance (500 experts) | 8h-20h | ~115 $ | ~1 380 $ |

**Mode recommandé en phase de lancement : 8h-20h** — les experts judiciaires travaillent en heures ouvrables, le site affiche une page explicite "Le site est ouvert pendant les horaires bureau de 8h à 20h" en dehors de ces horaires.

---

## Coûts externes (hors AWS)

| Service | Coût |
|---------|------|
| Stripe | 1.5% + 0.25 € par transaction (Europe) |
| Nom de domaine (judi-expert.fr) | ~10-15 €/an |
| Certificat SSL | Gratuit (AWS Certificate Manager) |

---

## Optimisations possibles

### Fonctionnement heures ouvrables uniquement (8h-20h)

Le Site Central peut être limité aux heures ouvrables (12h/jour au lieu de 24h) via un scheduler AWS (EventBridge + Lambda) qui démarre/arrête ECS et RDS. L'Application Locale fonctionne normalement 24/7 car tout est local — seules la création de dossier (vérification ticket) et l'achat de tickets nécessitent le Site Central.

**Impact sur les coûts :**

| Service | 24/7 ($/mois) | 8h-20h ($/mois) | Économie |
|---------|--------------|-----------------|----------|
| ECS Fargate (1 tâche) | 18.00 | 9.00 | -50% |
| RDS PostgreSQL | 16.00 | 8.00 | -50% |
| ALB | 22.27 | 22.27 | 0% (reste actif) |
| Autres services | 17.40 | 17.40 | 0% |
| **TOTAL** | **~74** | **~57** | **-23%** |

**Note :** L'ALB reste actif 24/7 pour servir une page de maintenance hors heures ouvrables. Son coût (~22 $/mois) est incompressible.

**Implémentation technique :**
- EventBridge Rule : cron `0 8 * * ? *` (start) et `0 20 * * ? *` (stop), timezone Europe/Paris
- Lambda de contrôle : met à jour le `desiredCount` ECS à 1 (start) ou 0 (stop), et appelle `start-db-instance` / `stop-db-instance` sur RDS
- ALB : target group vide hors heures → renvoie une page HTML statique "Service disponible de 8h à 20h"
- Coût Lambda + EventBridge : négligeable (<0.10 $/mois)

**Récapitulatif avec heures ouvrables :**

| Scénario | 24/7 | 8h-20h | 8h-20h + tier gratuit |
|----------|------|--------|----------------------|
| Phase lancement (50 experts) | ~74 $/mois | ~57 $/mois | ~36 $/mois |
| Croissance (200 experts) | ~103 $/mois | ~80 $/mois | ~59 $/mois |

### Autres optimisations

#### Court terme
- **ECS Fargate Spot** : jusqu'à -70% sur les tâches non critiques (non recommandé pour la prod principale)
- **RDS Reserved Instance (1 an)** : ~40% d'économie sur db.t4g.micro → ~7.50 $/mois au lieu de 12.41 $
- **S3 Intelligent-Tiering** : économie automatique sur les objets peu accédés

### Moyen terme (>200 experts)
- **ECS auto-scaling** : scale-to-zero la nuit si le trafic est faible
- **RDS Aurora Serverless v2** : pertinent si le trafic est très variable
- **CloudFront caching agressif** : réduire les requêtes vers l'ALB

### Long terme (>1000 experts)
- **Savings Plans (Compute)** : engagement 1 ou 3 ans pour -20% à -40%
- **ECR lifecycle policies** : suppression automatique des anciennes images
- **Multi-région** : si expansion internationale

---

## Comparaison avec le tier gratuit AWS (Free Tier)

Certains services bénéficient du tier gratuit AWS pendant les 12 premiers mois :

| Service | Tier gratuit (12 mois) | Économie |
|---------|----------------------|----------|
| ECS Fargate | Non inclus | 0 $ |
| RDS | 750 h/mois db.t4g.micro | ~12 $/mois |
| S3 | 5 Go stockage + 20 000 GET | ~0.15 $/mois |
| CloudFront | 1 To transfert | ~2.61 $/mois |
| SES | 62 000 emails/mois (depuis EC2) | ~0.10 $/mois |
| CloudWatch | 10 métriques + 5 Go logs | ~6 $/mois |

**Économie tier gratuit (12 premiers mois) : ~21 $/mois → coût réel ~53 $/mois**

---

## Conclusion

Le coût AWS pour Judi-Expert en phase de lancement est estimé entre **74 et 103 $/mois** en 24/7. En limitant le fonctionnement aux heures ouvrables (8h-20h), le coût descend à **~57 $/mois** (-23%), et à **~36 $/mois** avec le tier gratuit la première année.

Le poste incompressible est l'ALB (~22 $/mois). ECS et RDS sont les seuls postes réellement optimisables par le scheduling.

Le modèle économique basé sur la vente de tickets doit couvrir ces coûts : avec un ticket à 15-20 €, il suffit de vendre ~3-4 tickets/mois (mode heures ouvrables) pour atteindre le seuil de rentabilité infrastructure.
