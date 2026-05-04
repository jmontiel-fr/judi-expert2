# Architecture Globale — Judi-Expert

## Introduction

Ce document décrit l'architecture technique complète du système Judi-Expert, composé de deux parties principales : l'**Application Locale** installée sur le PC de l'expert et le **Site Central** déployé sur AWS.

> Pour la définition des termes et acronymes, consultez le [Glossaire & Workflow](glossaire-workflow.md).

---

## Vue d'ensemble

Judi-Expert est un système à deux composants :

1. **Application Locale** — PWA conteneurisée (4 conteneurs Docker) installée sur le PC de l'expert, intégrant un LLM local, une base RAG, un moteur OCR et une base de données relationnelle.
2. **Site Central** — PWA déployée sur AWS, gérant l'authentification, les paiements, la distribution des modules RAG et l'administration.

Les deux composants partagent la même stack technique : Python (FastAPI) pour le backend, React/Next.js pour le frontend PWA. Toutes les données d'expertise restent exclusivement sur le PC de l'expert ; seuls les tickets transitent entre l'Application Locale et le Site Central.

---

## Architecture globale

```mermaid
graph TB
    subgraph "PC Expert — Application Locale"
        AMORCE[Amorce / Lanceur]
        subgraph "Docker Compose"
            WEB[judi-web<br/>Next.js + FastAPI + SQLite<br/>Ports 3000, 8000]
            LLM_C[judi-llm<br/>Ollama + Mistral 7B<br/>Port 11434]
            RAG_C[judi-rag<br/>Qdrant + Corpus Domaine<br/>Ports 6333, 6334]
            OCR_C[judi-ocr<br/>Tesseract + pdf2image<br/>Port 8001]
        end
        AMORCE --> WEB
        AMORCE --> LLM_C
        AMORCE --> RAG_C
        AMORCE --> OCR_C
        WEB -->|API REST| LLM_C
        WEB -->|API REST/gRPC| RAG_C
        WEB -->|API interne| OCR_C
    end

    subgraph "AWS — Site Central"
        CF[CloudFront CDN<br/>HTTPS + ACM + Shield]
        LS[Lightsail Instance<br/>Docker Compose<br/>Caddy + FastAPI + Next.js]
        RDS[RDS PostgreSQL]
        COG[AWS Cognito]
        R53[Route 53 DNS]
        S3[S3 Bucket<br/>Images Docker .tar.gz<br/>+ package installateur]
        STRIPE[Stripe API]
        GMAIL[Gmail SMTP<br/>Envoi emails]
    end

    WEB -->|Vérification Ticket| CF
    WEB -->|Téléchargement images Docker| S3
    CF --> LS
    LS --> RDS
    LS --> COG
    LS --> STRIPE
    LS --> GMAIL
    R53 --> CF
```

---

## Application Locale — 4 conteneurs Docker

L'Application Locale fonctionne via Docker Compose avec 4 conteneurs isolés :

| Conteneur | Image | Rôle | Ports |
|-----------|-------|------|-------|
| `judi-web` | Next.js + FastAPI + SQLite | Frontend PWA, API backend, BD locale | 3000 (web), 8000 (api) |
| `judi-llm` | Ollama (Mistral 7B Instruct v0.3) | Inférence LLM locale | 11434 |
| `judi-rag` | Qdrant | Base vectorielle + corpus domaine | 6333 (REST), 6334 (gRPC) |
| `judi-ocr` | Python + Tesseract + pdf2image | Extraction OCR des PDF-scan | 8001 |

### Détail des conteneurs

#### judi-web (Frontend + Backend + BD)

- **Frontend** : Next.js PWA (React) — interface utilisateur professionnelle
- **Backend** : FastAPI — API REST pour le workflow d'expertise, la configuration, le ChatBot
- **Base de données** : SQLite via SQLAlchemy + Alembic — stockage des dossiers, étapes, fichiers, configuration
- **Dépendances** : passlib (bcrypt), python-jose (JWT), docxtpl (génération .docx), httpx (appels HTTP)

#### judi-llm (LLM local)

- **Runtime** : Ollama — serveur d'inférence LLM gratuit
- **Modèle** : Mistral 7B Instruct v0.3 (Apache 2.0, optimisé français, 7.25B paramètres)
- **API** : Compatible OpenAI (`/api/chat`, `/api/generate`)
- **Téléchargement automatique** du modèle au premier démarrage via script d'entrypoint

#### judi-rag (Base vectorielle)

- **Moteur** : Qdrant — base de données vectorielle open-source
- **Embedding** : `sentence-transformers/all-MiniLM-L6-v2` via FastEmbed
- **Collections** : `corpus_{domaine}`, `config_{domaine}`, `system_docs`
- **Persistance** : Volume Docker pour le stockage des vecteurs

#### judi-ocr (Extraction OCR)

- **Moteur OCR** : Tesseract OCR via pytesseract (langue `fra`)
- **Conversion PDF** : pdf2image (Poppler) pour les PDF-scan, PyMuPDF pour les PDF texte
- **API** : `POST /api/ocr/extract` — retourne `{ text, pages, confidence }`

### Ordre de démarrage

Le Docker Compose orchestre le démarrage dans l'ordre suivant :

1. `judi-llm` — démarrage d'Ollama + téléchargement du modèle (healthcheck sur `/api/tags`)
2. `judi-rag` — démarrage de Qdrant (healthcheck sur `/healthz`)
3. `judi-ocr` — démarrage du service OCR (healthcheck sur `/health`)
4. `judi-web` (backend) — dépend de la disponibilité des 3 services précédents
5. `judi-web` (frontend) — dépend du backend

---

## Site Central — Infrastructure AWS

Le Site Central est déployé sur une instance AWS Lightsail avec Docker Compose et une base de données RDS PostgreSQL externe.

### Services AWS utilisés

| Service | Rôle |
|---------|------|
| **CloudFront** | CDN + HTTPS (certificat ACM) + protection DDoS (Shield Standard) |
| **Lightsail** | Instance Docker (backend FastAPI + frontend Next.js + Caddy reverse proxy) |
| **RDS PostgreSQL** | Base de données relationnelle (experts, tickets, domaines) — backups auto 7j |
| **AWS Cognito** | Authentification des experts (User Pools) |
| **ECR** | Registre d'images Docker (déploiement rapide via docker pull) |
| **ACM** | Certificat SSL/TLS pour www.judi-expert.fr (gratuit, renouvellement auto) |
| **Route 53** | DNS (zone hébergée judi-expert.fr) |
| **S3** | Stockage des images Docker (.tar.gz) pour le package installateur + assets |
| **Gmail SMTP** | Envoi d'emails (tickets, notifications) via compte Gmail dédié |

### Architecture réseau

```
Internet → CloudFront (HTTPS, ACM, cache, DDoS Shield) → Lightsail instance (HTTP port 80, Docker)
                                                          └→ RDS PostgreSQL (privé)
```

- **CloudFront** gère le HTTPS (certificat ACM), le cache des assets statiques, et la protection DDoS via AWS Shield Standard (gratuit).
- **Caddy** sur l'instance Lightsail sert de reverse proxy interne (HTTP uniquement) entre le frontend Next.js et le backend FastAPI.
- **L'instance Lightsail** n'est pas exposée directement sur Internet — seul CloudFront y accède.
- **ECR** stocke les images Docker du site central. Le déploiement se fait par `docker pull` depuis l'instance (~30s vs ~40 min par SCP).

### Migration vers ECS/Fargate

Quand le trafic le justifie (>500 experts), le même code Docker peut être déployé sur ECS/Fargate avec ALB. Seule l'infrastructure change, pas le code.

---

## Flux de données principal

```mermaid
sequenceDiagram
    participant E as Expert
    participant W as judi-web
    participant O as judi-ocr
    participant L as judi-llm
    participant R as judi-rag
    participant SC as Site Central

    Note over E,SC: Création de dossier
    E->>W: Nom + Ticket
    W->>SC: Vérification Ticket (HTTP)
    SC-->>W: Ticket valide / invalide
    W-->>E: Dossier créé (4 étapes)

    Note over E,SC: Step0 — Extraction OCR
    E->>W: Upload PDF-scan
    W->>O: Envoi PDF pour OCR
    O-->>W: Texte brut extrait
    W->>L: Structuration Markdown
    L-->>W: Markdown structuré (QT, destinataire)
    W-->>E: Affichage Markdown

    Note over E,SC: Step1 — PEMEC
    E->>W: Clic "Execute"
    W->>R: Récupération TPE + contexte domaine
    R-->>W: Documents pertinents
    W->>L: Génération QMEC
    L-->>W: QMEC généré
    W-->>E: Download QMEC

    Note over E,SC: Step2 — Upload
    E->>W: Upload NE.docx + REB.docx
    W-->>E: Confirmation stockage

    Note over E,SC: Step3 — REF + RAUX
    E->>W: Clic "Execute"
    W->>R: Récupération corpus domaine
    R-->>W: Documents pertinents
    W->>L: Génération REF + RAUX
    L-->>W: REF + RAUX générés
    W-->>E: Download REF + RAUX (.docx)
```

---

## Modèles de données

### Base de données Application Locale (SQLite)

```mermaid
erDiagram
    LocalConfig {
        int id PK
        string password_hash
        string domaine
        string rag_version
        boolean is_configured
        datetime created_at
        datetime updated_at
    }

    Dossier {
        int id PK
        string nom
        string ticket_id UK
        string domaine
        enum statut "actif|archive"
        datetime created_at
        datetime updated_at
    }

    Step {
        int id PK
        int dossier_id FK
        int step_number "0|1|2|3"
        enum statut "initial|realise|valide"
        datetime executed_at
        datetime validated_at
    }

    StepFile {
        int id PK
        int step_id FK
        string filename
        string file_path
        enum file_type "pdf_scan|markdown|qmec|ne|reb|ref|raux|archive"
        int file_size
        datetime created_at
    }

    ChatMessage {
        int id PK
        int session_id
        enum role "user|assistant"
        text content
        datetime created_at
    }

    Dossier ||--o{ Step : contient
    Step ||--o{ StepFile : contient
```

**ORM** : SQLAlchemy (Mapped types) + Alembic pour les migrations versionnées.

### Base de données Site Central (PostgreSQL)

```mermaid
erDiagram
    Expert {
        int id PK
        string cognito_sub UK
        string email UK
        string nom
        string prenom
        string adresse
        string domaine
        boolean accept_newsletter
        datetime created_at
    }

    Ticket {
        int id PK
        string ticket_code UK
        int expert_id FK
        string domaine
        enum statut "actif|utilise|expire"
        decimal montant
        string stripe_payment_id
        datetime created_at
        datetime used_at
    }

    Domaine {
        int id PK
        string nom UK
        string repertoire
        boolean actif
    }

    CorpusVersion {
        int id PK
        int domaine_id FK
        string version
        text description
        string ecr_image_uri
        datetime published_at
    }

    ContactMessage {
        int id PK
        int expert_id FK
        string domaine
        string objet
        text message
        datetime created_at
    }

    Expert ||--o{ Ticket : achete
    Expert ||--o{ ContactMessage : envoie
    Domaine ||--o{ CorpusVersion : possede
```

**ORM** : SQLAlchemy (Mapped types) + Alembic pour les migrations versionnées.

---

## Communication entre composants

### Application Locale → Site Central

| Flux | Protocole | Description |
|------|-----------|-------------|
| Vérification ticket | HTTPS (POST) | L'App Locale envoie le ticket au Site Central via l'ALB |
| Téléchargement RAG | HTTPS (GET) | L'App Locale télécharge les images Docker depuis ECR |

### Communication interne (Docker Compose)

| Source | Destination | Protocole | Description |
|--------|-------------|-----------|-------------|
| judi-web | judi-llm | HTTP REST (port 11434) | Appels d'inférence LLM |
| judi-web | judi-rag | HTTP REST (port 6333) / gRPC (port 6334) | Recherche et indexation vectorielle |
| judi-web | judi-ocr | HTTP REST (port 8001) | Extraction OCR des PDF |

### Isolation des données

- Toutes les données d'expertise restent sur le PC de l'expert (SQLite + fichiers locaux)
- Seuls les tickets transitent entre l'Application Locale et le Site Central
- Le Site Central ne stocke que les données d'inscription, les tickets et les métadonnées des corpus

---

## Décisions techniques

| Décision | Choix | Justification |
|----------|-------|---------------|
| ORM | SQLAlchemy + Alembic | Standard Python, migrations versionnées |
| Base vectorielle | Qdrant | Open-source, API REST/gRPC, conteneur Docker officiel |
| OCR | Tesseract OCR (pytesseract) | Open-source (Apache 2.0), support français natif |
| LLM | Mistral 7B Instruct v0.3 | Apache 2.0, optimisé français, 7.25B paramètres |
| Runtime LLM | Ollama | Gratuit, API REST compatible OpenAI, gestion GPU/CPU |
| Template .docx | docxtpl (Jinja2) | Remplacement de placeholders avec préservation du style |
| Paiement | Stripe Checkout + Webhooks | Standard SaaS, SDK Python officiel |
| Auth | AWS Cognito + Amplify JS | Intégration native AWS, User Pools |
| Email | Gmail SMTP (smtplib) | Même config dev et prod, 500 emails/jour |
| Infra prod | CloudFront + Lightsail + RDS | Coût réduit (~28 $/mois), HTTPS ACM, DDoS Shield, migration ECS possible |
| Conteneurs | Docker Compose (local + prod), ECS/ECR (futur) | Orchestration simple, scalable |


---

## Sécurité

### Isolation réseau

L'application locale utilise deux réseaux Docker :

- **Réseau interne** (`internal: true`) : LLM, OCR, RAG, frontend — aucun accès Internet
- **Réseau externe** : backend uniquement — communication exclusive avec le Site Central

Cette architecture garantit que les données d'expertise ne peuvent pas fuiter vers Internet, même en cas de compromission d'un conteneur.

### Intégrité des conteneurs

- Images épinglées par version (pas de `latest` en production)
- Images personnalisées construites localement depuis le code source
- Images tierces (Ollama, Qdrant) depuis les registres officiels
- Scan de vulnérabilités via ECR en production AWS

### Protection des données

- Chiffrement du disque obligatoire (BitLocker / FileVault)
- Données d'expertise 100% locales — jamais transmises au cloud
- Hash SHA-256 de l'archive finale pour garantir l'intégrité
- JWT local avec expiration pour l'authentification

### Conformité

- **RGPD** : données traitées localement, droit à l'effacement, minimisation
- **AI Act** : IA comme assistant, validation humaine à chaque étape, modèle open-source local
- **Expertise judiciaire** : traçabilité, horodatage, non-répudiation

Pour le détail complet, voir [securite.md](securite.md).
