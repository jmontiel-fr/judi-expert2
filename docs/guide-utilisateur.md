# Guide Utilisateur — Application Locale Judi-Expert

## Introduction

Ce guide décrit l'utilisation de l'Application Locale Judi-Expert, destinée aux experts judiciaires. L'application accompagne la production de rapports d'expertise en s'appuyant sur l'intelligence artificielle et une base de connaissances spécialisée dans votre domaine.

Deux **types de workflow** sont disponibles à la création du dossier :

| Workflow | Étapes | Usage |
|----------|--------|-------|
| **Standard** | 5 étapes + Step E/A (hors appli) | Expertise guidée de bout en bout : ordonnance → TRE → PREA → PRE → archivage |
| **Simple** | 2 étapes | Vous disposez déjà d'un **PRE** rédigé : mise en forme linguistique → archivage |

Toutes vos données d'expertise restent exclusivement sur votre PC. Seuls les tickets d'expertise transitent entre votre application et le Site Central.

> Pour la définition des termes et acronymes (TRE, PREA, PRE, PREF, REF, DAC, etc.), consultez le [Glossaire & Workflow](glossaire-workflow.md).

---

## 1. Installation et premier lancement (Amorce)

### Prérequis PC

- **Processeur** : CPU multi-cœurs récent (Intel i5/i7 ou AMD Ryzen 5/7)
- **Mémoire RAM** : 16 Go minimum (32 Go recommandé)
- **Espace disque** : 50 Go minimum disponibles
- **Chiffrement du disque** : BitLocker (Windows) ou FileVault (macOS) activé
- **Système d'exploitation** : Windows 10/11, macOS 12+ ou Linux (Ubuntu 22.04+)

### Installation

1. Téléchargez le package d'installation depuis la page **Téléchargements** du Site Central (https://judi-expert.fr/downloads)
2. Lancez l'installateur (`.exe` sous Windows, script sous macOS/Linux)
3. L'installateur vérifie les prérequis et installe Docker, les images et la configuration

### Premier lancement

1. Lancez l'application via l'**Amorce** (icône Judi-Expert)
2. L'Amorce démarre Docker puis les conteneurs de l'application
3. Votre navigateur s'ouvre sur http://localhost:3000

---

## 2. Configuration initiale

Au premier lancement, l'application vous guide à travers la configuration.

### Authentification

1. Connectez-vous avec vos identifiants du **Site Central** (email et mot de passe)
2. Une connexion Internet est requise pour l'authentification

### Sélection du domaine d'expertise

Choisissez votre domaine (psychologie, psychiatrie, médecine légale, bâtiment, comptabilité, etc.). Le domaine détermine le corpus RAG utilisé par l'IA.

### Installation du module RAG

Le module RAG contient la base de connaissances spécialisée. Son installation est **obligatoire** avant de créer des dossiers.

1. Accédez au menu **Configuration**
2. Consultez les **versions RAG disponibles**
3. Sélectionnez une version et cliquez sur **Installer**

### Configuration du TRE (Template de Rapport d'Expertise)

Pour le workflow **standard** :

1. Dans **Configuration**, section **TRE** (ou template rapport)
2. Téléversez votre `tre.docx` personnalisé, ou utilisez le TRE par défaut du domaine
3. Le TRE contient les placeholders `<<...>>` et les annotations `@type contenu@` utilisés tout au long du workflow

---

## 3. Création d'un dossier

### Prérequis

- Un **ticket d'expertise** valide, acheté sur le Site Central
- Le module RAG installé

### Procédure

1. Depuis la page d'accueil, cliquez sur **Nouveau dossier**
2. Saisissez le **nom du dossier** (ex. : « Expertise Dupont — TGI Paris »)
3. Saisissez le **token du ticket** reçu par email
4. Choisissez le **type de workflow** :
   - **Standard** — 5 étapes (expertise complète assistée)
   - **Simple** — 2 étapes (PRE déjà rédigé → PREF → archivage)
5. Cliquez sur **Créer**

L'application vérifie le ticket auprès du Site Central. Si le ticket est valide, le dossier est créé avec les étapes correspondantes au statut « initial ». Le type de workflow est **figé** à la création et ne peut plus être modifié.

---

## 4. Workflow standard (5 étapes + E/A)

Chaque étape doit être **validée** avant de passer à la suivante. Une étape validée est verrouillée.

### Step 1 — Création dossier

**Objectif** : importer l'ordonnance et les pièces, extraire le texte par OCR, identifier les questions du tribunal et les placeholders.

1. Accédez à l'étape 1 du dossier
2. Importez le **PDF de l'ordonnance** (réquisition)
3. Optionnel : ajoutez des **pièces complémentaires**
4. Cliquez sur **Extraire et structurer**
5. Vérifiez les fichiers produits : `demande.md`, `placeholders.csv`, `questions.md`
6. Validez l'étape

### Step 2 — Validation TRE → PREA

**Objectif** : valider la syntaxe du TRE et produire le **PREA** (`prea.docx`) — copie du TRE validée.

1. Le TRE est résolu depuis la configuration ou un upload dans le dossier
2. Cliquez sur **Valider le TRE**
3. Vérifiez le `prea.docx` en sortie
4. Validez l'étape

### Step 3 — Consolidation documentaire

**Objectif** : importer les pièces reçues en réponse aux diligences et les convertir en Markdown.

1. Importez les pièces (`diligence-xxx-piece-yyy.*`)
2. Cliquez sur **Extraire les documents**
3. Vérifiez les extractions OCR
4. Validez l'étape (ou **Sans objet** s'il n'y a pas de pièces)

### Step E/A — Entretien ou Analyse (hors application)

**Après le Step 3**, menez vos entretiens ou analyses sur pièces. Remplissez les annotations du **PREA** en style télégraphique (`@dires`, `@analyse`, `@verbatim`, etc.), directement dans Word ou via l'outil d'édition PREA.

Cette étape n'a pas de bouton dans l'application : vous travaillez hors ligne puis importez le PREA complété au Step 4.

### Step 4 — Production pré-rapport

**Objectif** : produire le **PRE** (`pre.docx`) à partir du PREA complété.

1. Importez le **PREA annoté** (`pea.docx` / PREA complété)
2. Cliquez sur **Générer le PRE**
3. Relisez le `pre.docx` produit
4. Optionnel : cliquez sur **Générer le DAC** pour l'analyse contradictoire
5. Validez l'étape

### Step 5 — Finalisation et archivage

**Objectif** : archiver le dossier avec horodatage technique.

1. Importez le **REF** (`ref.docx`) — rapport final ajusté par l'expert
2. L'application crée l'archive ZIP et le fichier **timbre** (hash SHA-256)
3. Validez l'étape, puis **Clore le dossier** depuis la page du dossier

---

## 5. Workflow simple (2 étapes)

Pour les expertises où le **Pré-Rapport** (`pre.docx`) est déjà rédigé en dehors de Judi-Expert.

### Step 1 — Mise en forme linguistique

**Objectif** : produire le **PREF** (`pref.docx`) par révision linguistique du PRE.

1. Importez votre **`pre.docx`**
2. Cliquez sur **Mettre en forme linguistique**
3. Consultez le **`pref.docx`** généré
4. Optionnel : cliquez sur **Générer le DAC**
5. Vous pouvez **relancer** la mise en forme après modification du PRE ou du PREF (tant que l'étape n'est pas validée)
6. Validez l'étape

### Step 2 — Archivage

**Objectif** : créer l'archive ZIP et le timbre d'horodatage.

1. Par défaut, le **PREF** du Step 1 est utilisé
2. Optionnel : importez une version ajustée du PREF
3. Cliquez sur **Archiver le dossier**
4. Validez l'étape, puis **Clore le dossier**

---

## 6. Gestion du dossier

Depuis la page de détail d'un dossier :

- **Progression** : pastilles de statut par étape (initial, en cours, fait, validé)
- **Reset** d'une étape ou **reset complet** (dossier actif uniquement)
- **Clore le dossier** lorsque toutes les étapes sont validées
- **Archiver** et **Télécharger** une fois le dossier fermé

Les fichiers sont stockés localement sous `C:\judi-expert\<nom-dossier>\step{n}\in|out\`.

---

## 7. Utilisation du ChatBot

L'assistant conversationnel est accessible depuis le menu principal.

- Réponses basées sur le **corpus de votre domaine** et la **documentation du système**
- Historique conservé localement
- LLM local — aucune donnée transmise à l'extérieur

---

## 8. FAQ utilisateur

### Comment obtenir un ticket d'expertise ?

Connectez-vous au Site Central, accédez à **Mon Espace → Tickets** et achetez un ticket via Stripe. Le code est envoyé par email.

### Quelle différence entre workflow standard et simple ?

- **Standard** : vous partez de l'ordonnance et construisez le rapport pas à pas avec l'IA (TRE, PREA, PRE).
- **Simple** : vous avez déjà un PRE rédigé ; l'application applique une révision linguistique (PREF) puis archive.

### Puis-je utiliser l'application hors connexion ?

Oui, sauf pour la création de dossier (vérification du ticket) et la mise à jour du module RAG.

### Mes données sont-elles sécurisées ?

Toutes les données d'expertise restent sur votre PC. Aucun document n'est transmis au Site Central.

### Puis-je modifier une étape après validation ?

Non. Une étape validée est verrouillée. Utilisez **Reset** avant validation si vous devez recommencer une étape (dossier actif).

### Comment contacter le support ?

Formulaire de contact sur le Site Central (https://judi-expert.fr/contact).
