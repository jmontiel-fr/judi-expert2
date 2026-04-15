# Glossaire & Workflow — Judi-Expert

Ce document centralise les termes, acronymes et concepts du projet, ainsi que le workflow fonctionnel complet de l'expertise judiciaire assistée par IA.

> Voir aussi : [Architecture](architecture.md) · [Guide utilisateur](user-guide.md) · [Méthodologie](methodologie.md) · [Développement](developpement.md)

---

## 1. Workflow fonctionnel

### Vue d'ensemble

L'expert judiciaire utilise Judi-Expert pour produire un rapport d'expertise en 4 étapes séquentielles. Chaque étape doit être validée avant de passer à la suivante. Une étape validée est verrouillée et ne peut plus être modifiée.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SITE CENTRAL (AWS)                                    │
│  Inscription → Achat ticket (Stripe) → Envoi ticket par email           │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ ticket
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                APPLICATION LOCALE (PC Expert)                           │
│                                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────────────┐  │
│  │  Step0    │    │  Step1    │    │  Step2    │    │     Step3        │  │
│  │Extraction │───►│  PEMEC    │───►│  Upload   │───►│   REF + RAUX     │  │
│  │           │    │           │    │           │    │                  │  │
│  │ PDF-scan  │    │ QT + TPE  │    │ NE + REB  │    │ REB+QT+NE+TPL   │  │
│  │    ↓      │    │    ↓      │    │  (.docx)  │    │      ↓           │  │
│  │ Markdown  │    │  QMEC     │    │           │    │ REF + RAUX       │  │
│  │ (QT)      │    │           │    │           │    │ + archive ZIP    │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────────────┘  │
│       ▲               ▲                                ▲                │
│       │               │                                │                │
│    judi-ocr       judi-rag                         judi-rag             │
│    judi-llm       judi-llm                         judi-llm             │
└─────────────────────────────────────────────────────────────────────────┘
```

### Prérequis avant le workflow

1. L'expert s'inscrit sur le **Site Central** et achète un **ticket** via Stripe
2. L'expert installe l'**Application Locale** sur son PC et configure :
   - Son **mot de passe local**
   - Son **domaine d'expertise** (psychologie, psychiatrie, etc.)
   - Le **module RAG** (base de connaissances du domaine)
   - Son **TPE** (trame personnelle d'entretien)
   - Son **Template Rapport** (modèle .docx avec placeholders)

### Step0 — Extraction de la réquisition

| | |
|---|---|
| **Objectif** | Convertir le PDF-scan de la réquisition du tribunal en Markdown structuré |
| **Entrée** | PDF-scan de la réquisition (document papier numérisé) |
| **Traitement** | OCR (judi-ocr) → texte brut → structuration IA (judi-llm) → Markdown avec QT identifiées |
| **Sortie** | Fichier Markdown structuré contenant les QT, le destinataire et les sections |
| **Rôle expert** | Vérifier le texte extrait, corriger les erreurs OCR, valider |
| **Verrouillage** | Validation → passage au Step1, Step0 non modifiable |

### Step1 — PEMEC (Plan d'entretien)

| | |
|---|---|
| **Objectif** | Générer un plan d'entretien structuré pour les entretiens avec l'expertisé |
| **Entrée** | QT extraites au Step0 + TPE de l'expert + contexte domaine (RAG) |
| **Traitement** | Récupération TPE et corpus (judi-rag) → génération QMEC (judi-llm) |
| **Sortie** | QMEC — document structuré de questions pour l'entretien |
| **Rôle expert** | Télécharger le QMEC, l'adapter, mener les entretiens, valider |
| **Verrouillage** | Validation → passage au Step2, Step1 non modifiable |

### Step2 — Upload des notes et du rapport brut

| | |
|---|---|
| **Objectif** | Collecter les documents rédigés par l'expert après ses entretiens |
| **Entrée** | Deux fichiers `.docx` rédigés par l'expert hors application |
| **Documents** | **NE** (Notes d'Entretien) : notes télégraphiques · **REB** (Rapport d'Expertise Brut) : réponses argumentées aux QT |
| **Traitement** | Aucun traitement IA — simple stockage et validation de format |
| **Rôle expert** | Rédiger NE et REB, les uploader au format .docx, valider |
| **Verrouillage** | Validation → passage au Step3, Step2 non modifiable |

### Step3 — Génération du rapport final (REF + RAUX)

| | |
|---|---|
| **Objectif** | Produire le rapport d'expertise final et une analyse de contestations |
| **Entrée** | REB + QT + NE + Template Rapport + corpus domaine (RAG) |
| **Traitement** | Récupération corpus (judi-rag) → génération REF et RAUX (judi-llm) → remplissage du Template Rapport (docxtpl) |
| **Sorties** | **REF** (.docx) : rapport professionnel final · **RAUX** (.docx) : partie 1 = contestations possibles, partie 2 = REF révisé |
| **Rôle expert** | Relire REF et RAUX, valider pour archivage définitif |
| **Verrouillage** | Validation → dossier archivé (ZIP immuable contenant tous les fichiers : réquisition, Markdown, QMEC, NE, REB, REF, RAUX) |

### Cycle de vie d'un dossier

```
Création (ticket valide)
    │
    ▼
  Step0: initial ──► realise ──► valide
    │
    ▼
  Step1: initial ──► realise ──► valide
    │
    ▼
  Step2: initial ──► realise ──► valide
    │
    ▼
  Step3: initial ──► realise ──► valide
    │
    ▼
  Dossier: actif ──► archive (ZIP immuable)
```

---

## 2. Glossaire — Termes métier

| Terme | Signification | Description |
|-------|--------------|-------------|
| **Dossier** | Dossier d'expertise | Unité de travail regroupant les 4 étapes d'une expertise judiciaire |
| **QT** | Questions du Tribunal | Questions posées par la juridiction auxquelles l'expert doit répondre, extraites de la réquisition |
| **TPE** | Trame Personnelle d'Entretien | Document personnel de l'expert définissant la structure de ses entretiens, indexé dans la base RAG |
| **PEMEC** | Plan d'Entretien Médico-Expert Complet | Nom de l'étape (Step1) de génération du plan d'entretien |
| **QMEC** | Questionnaire Médico-Expert Complet | Document généré au Step1 : plan d'entretien structuré à partir des QT et du TPE |
| **NE** | Notes d'Entretien | Document `.docx` rédigé par l'expert contenant ses notes d'entretien sous forme télégraphique, uploadé au Step2 |
| **REB** | Rapport d'Expertise Brut | Document `.docx` rédigé par l'expert contenant ses réponses argumentées aux QT, uploadé au Step2 |
| **REF** | Rapport d'Expertise Final | Document `.docx` généré au Step3 : rapport professionnel produit à partir du REB, des QT, des NE et du Template Rapport |
| **RAUX** | Rapport Auxiliaire | Document `.docx` généré au Step3 en deux parties : (1) analyse des contestations possibles du REF, (2) version révisée du REF |
| **Template Rapport** | Modèle de rapport | Fichier `.docx` avec champs de fusion (placeholders) utilisé pour la génération du REF |
| **Réquisition** | Ordonnance du tribunal | Document officiel du tribunal confiant la mission d'expertise à l'expert |
| **Ticket** | Code d'accès | Code unique acheté sur le Site Central via Stripe, nécessaire pour créer un dossier dans l'Application Locale |
| **Domaine** | Spécialité d'expertise | Psychologie, psychiatrie, médecine légale, bâtiment ou comptabilité. Détermine le corpus RAG utilisé. |
| **Corpus** | Base documentaire | Ensemble de documents de référence par domaine (guides, textes réglementaires, référentiels) utilisés par le RAG |

## 3. Glossaire — Infrastructure

| Terme | Description |
|-------|-------------|
| **Application Locale** | Application desktop conteneurisée (Docker Compose, 4 conteneurs) installée sur le PC de l'expert. Gère le workflow d'expertise. Toutes les données restent en local. |
| **Site Central** | Plateforme web AWS gérant l'inscription des experts, les paiements Stripe, la distribution des corpus RAG et l'administration. |
| **Amorce** | Lanceur de l'Application Locale. Démarre Docker puis les 4 conteneurs et ouvre le navigateur. |

## 4. Glossaire — Composants techniques

| Terme | Description |
|-------|-------------|
| **judi-web** | Conteneur principal : frontend Next.js (port 3000) + backend FastAPI (port 8000) + base SQLite |
| **judi-llm** | Conteneur LLM : Ollama + Mistral 7B Instruct v0.3 (port 11434). Exécution locale, aucune connexion internet requise. |
| **judi-rag** | Conteneur base vectorielle : Qdrant (ports 6333/6334). Stocke les embeddings du corpus domaine. |
| **judi-ocr** | Conteneur OCR : Tesseract + pdf2image + PyMuPDF (port 8001). Extraction de texte depuis les PDF-scan. |
| **RAG** | Retrieval-Augmented Generation. Technique enrichissant les réponses du LLM avec des documents factuels issus du corpus. |
| **LLM** | Large Language Model. Modèle de langage (Mistral 7B) utilisé pour la génération de texte. |
| **OCR** | Optical Character Recognition. Reconnaissance optique de caractères pour extraire le texte des documents scannés. |
| **Embedding** | Représentation vectorielle d'un texte, utilisée pour la recherche sémantique dans Qdrant. Modèle : `all-MiniLM-L6-v2`. |

## 5. Glossaire — AWS (Site Central)

| Terme | Description |
|-------|-------------|
| **ECS Fargate** | Service AWS d'exécution de conteneurs sans serveur, héberge le backend + frontend du Site Central |
| **ECR** | Elastic Container Registry. Registre d'images Docker AWS, stocke les modules RAG et les images de l'app locale |
| **RDS** | Relational Database Service. Base PostgreSQL managée pour le Site Central |
| **Cognito** | Service d'authentification AWS. Gère les comptes experts (User Pools) |
| **ALB** | Application Load Balancer. Répartiteur de charge avec page de maintenance hors heures ouvrables |
| **EventBridge** | Scheduler AWS. Gère l'arrêt (20h) et le démarrage (8h) automatiques du Site Central |
| **SES** | Simple Email Service. Envoi d'emails (tickets, notifications) |
| **CloudFront** | CDN AWS pour la distribution des assets statiques |

## 6. Statuts et cycles de vie

| Entité | Statuts possibles | Description |
|--------|-------------------|-------------|
| **Step** | `initial` → `realise` → `valide` | Progression d'une étape : non commencée → exécutée → verrouillée |
| **Dossier** | `actif` → `archive` | Un dossier est archivé après validation du Step3 |
| **Ticket** | `actif` → `utilise` / `expire` | Un ticket est utilisé lors de la création d'un dossier |
