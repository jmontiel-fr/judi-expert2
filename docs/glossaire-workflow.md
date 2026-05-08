# Glossaire & Workflow — Judi-Expert

Ce document centralise les termes, acronymes et concepts du projet, ainsi que le workflow fonctionnel complet de l'expertise judiciaire assistée par IA.

> Voir aussi : [Architecture](architecture.md) · [Guide utilisateur](user-guide.md) · [Méthodologie](methodologie.md) · [Développement](developpement.md)

---

## 1. Workflow fonctionnel

### Vue d'ensemble

L'expert judiciaire utilise Judi-Expert pour produire un rapport d'expertise en 5 étapes séquentielles (plus une étape intermédiaire E/A réalisée par l'expert hors application). Chaque étape doit être validée avant de passer à la suivante. Une étape validée est verrouillée et ne peut plus être modifiée.

Le workflow supporte deux modes d'expertise :
- **Mode Entretien** : expertise basée sur des entretiens avec les parties (TPE → PE → PEA)
- **Mode Analyse** : expertise basée sur l'analyse documentaire des pièces (TPA → PA → PAA)

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              SITE CENTRAL (AWS)                                          │
│  Inscription → Achat ticket (Stripe) → Envoi ticket par email                           │
└──────────────────────────────────────┬──────────────────────────────────────────────────┘
                                       │ ticket
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          APPLICATION LOCALE (PC Expert)                                  │
│                                                                                         │
│  ┌────────────┐  ┌────────────┐  ┌─────────┐  ┌────────────┐  ┌──────────┐  ┌───────┐ │
│  │   Step 1    │  │   Step 2    │  │ Step E/A │  │   Step 3    │  │  Step 4   │  │Step 5│ │
│  │  Création   │  │Préparation  │  │Entretien │  │Consolidat°  │  │Production │  │Archi-│ │
│  │  dossier    │─►│investig.    │─►│ou Analyse │─►│document.   │─►│pré-rapport│─►│vage  │ │
│  │             │  │             │  │          │  │             │  │           │  │      │ │
│  │ordonnance   │  │ordonnance.md│  │ pe.docx  │  │diligence-  │  │ pea.docx  │  │ref.  │ │
│  │  .pdf       │  │tpe/tpa.docx│  │ ou       │  │ xxx-piece-  │  │  ou       │  │docx  │ │
│  │piece-xxx.*  │  │piece-xxx.md│  │ pa.docx  │  │ yyy.*       │  │ paa.docx  │  │  ↓   │ │
│  │     ↓       │  │     ↓       │  │     ↓    │  │     ↓       │  │tre.docx   │  │.zip  │ │
│  │ordonnance.md│  │ pe.md/.docx │  │ pea.docx │  │diligence-  │  │place_hold.│  │timbre│ │
│  │piece-xxx.md │  │ pa.md/.docx │  │ ou       │  │ xxx-piece-  │  │     ↓     │  │.txt  │ │
│  │questions.md │  │diligence.   │  │ paa.docx │  │ yyy.md      │  │ pre.docx  │  │      │ │
│  │place_hold.  │  │  docx       │  │          │  │             │  │ dac.docx  │  │      │ │
│  │  csv        │  │             │  │(hors app)│  │             │  │           │  │      │ │
│  └────────────┘  └────────────┘  └─────────┘  └────────────┘  └──────────┘  └───────┘ │
│       ▲                ▲                              ▲               ▲           ▲     │
│       │                │                              │               │           │     │
│    judi-ocr        judi-rag                        judi-ocr       judi-rag      S3     │
│    judi-llm        judi-llm                                       judi-llm             │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Prérequis avant le workflow

1. L'expert s'inscrit sur le **Site Central** et achète un **ticket** via Stripe
2. L'expert installe l'**Application Locale** sur son PC et configure :
   - Son **identifiant** (le mot de passe est celui du Site Central — une connexion Internet est nécessaire pour l'authentification)
   - Son **domaine d'expertise** (psychologie, psychiatrie, etc.)
3. L'expert peut personnaliser :
   - Son **corpus d'expertise** (documents de référence indexés dans la base RAG)
   - Son **TPE** ou **TPA** (trame personnelle d'entretien ou d'analyse)
   - Son **TRE** — Template de Rapport d'Expertise (`tre.docx`, modèle .docx avec placeholders `<<...>>`). Une liste de placeholders prédéfinis est disponible (voir section 8).

### Tableau récapitulatif Entrées / Opération / Sorties

<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<thead>
<tr style="background-color: #f0f0f0;">
  <th>Step</th><th>Nom</th><th>Fichiers d'entrée</th><th>Opération</th><th>Fichiers de sortie</th>
</tr>
</thead>
<tbody>
<tr>
  <td><strong>1</strong></td>
  <td>Création dossier</td>
  <td><code>ordonnance.pdf</code>, <code>piece-xxx.*</code></td>
  <td>Extraire et structurer</td>
  <td><code>ordonnance.md</code>, <code>piece-xxx.md</code>, <code>questions.md</code>, <code>place_holders.csv</code></td>
</tr>
<tr>
  <td><strong>2</strong></td>
  <td>Préparation investigations</td>
  <td><code>ordonnance.md</code>, TPE ou TPA, <code>piece-xxx.md</code></td>
  <td>Générer le plan</td>
  <td><strong>Entretien</strong> : <code>pe.md</code>, <code>pe.docx</code><br/><strong>Analyse</strong> : <code>pa.md</code>, <code>pa.docx</code>, <code>diligence-xxx.docx</code></td>
</tr>
<tr style="background-color: #fff8e1;">
  <td><strong>E/A</strong></td>
  <td>Entretien ou Analyse sur pièces</td>
  <td>PE ou PA généré au Step 2</td>
  <td><em>(action expert hors application)</em></td>
  <td><code>pea.docx</code> ou <code>paa.docx</code> (plan annoté)</td>
</tr>
<tr>
  <td><strong>3</strong></td>
  <td>Consolidation documentaire</td>
  <td><code>diligence-xxx-piece-yyy.*</code></td>
  <td>Extraire les documents</td>
  <td><code>diligence-xxx-piece-yyy.md</code></td>
</tr>
<tr>
  <td><strong>4</strong></td>
  <td>Production pré-rapport</td>
  <td><code>pea.docx</code> ou <code>paa.docx</code>, <code>tre.docx</code>, <code>place_holders.csv</code>, docs Step 3</td>
  <td>Générer le pré-rapport</td>
  <td><code>pre.docx</code>, <code>dac.docx</code></td>
</tr>
<tr>
  <td><strong>5</strong></td>
  <td>Finalisation et archivage</td>
  <td><code>ref.docx</code> (rapport final ajusté)</td>
  <td>Archiver le dossier</td>
  <td><code>&lt;dossier-xxx&gt;.zip</code>, <code>&lt;dossier-xxx&gt;-timbre.txt</code></td>
</tr>
</tbody>
</table>

### Légende des noms de fichiers

<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<thead>
<tr style="background-color: #f0f0f0;">
  <th>Fichier</th><th>Abréviation</th><th>Description</th>
</tr>
</thead>
<tbody>
<tr><td><code>ordonnance.pdf</code></td><td>—</td><td>PDF-scan de l'ordonnance du tribunal (réquisition)</td></tr>
<tr><td><code>ordonnance.md</code></td><td>—</td><td>Texte de l'ordonnance extrait par OCR, structuré en Markdown</td></tr>
<tr><td><code>piece-xxx.*</code></td><td>—</td><td>Pièce complémentaire (PDF, DOCX ou image)</td></tr>
<tr><td><code>piece-xxx.md</code></td><td>—</td><td>Texte extrait par OCR d'une pièce complémentaire</td></tr>
<tr><td><code>questions.md</code></td><td>QT</td><td>Liste numérotée Q1…Qn des questions extraites de l'ordonnance</td></tr>
<tr><td><code>tpe.md</code> / <code>tpe.docx</code></td><td>TPE</td><td>Template de Plan d'Entretien — trame personnelle de l'expert</td></tr>
<tr><td><code>tpa.md</code> / <code>tpa.docx</code></td><td>TPA</td><td>Template de Plan d'Analyse — trame personnelle de l'expert</td></tr>
<tr><td><code>pe.md</code></td><td>PE</td><td>Plan d'Entretien généré (Mode Entretien)</td></tr>
<tr><td><code>pe.docx</code></td><td>PE</td><td>Plan d'Entretien au format .docx (Mode Entretien)</td></tr>
<tr><td><code>pa.md</code></td><td>PA</td><td>Plan d'Analyse généré (Mode Analyse)</td></tr>
<tr><td><code>pa.docx</code></td><td>PA</td><td>Plan d'Analyse au format .docx</td></tr>
<tr><td><code>diligence-xxx.docx</code></td><td>—</td><td>Projet de courrier pour diligences complémentaires</td></tr>
<tr><td><code>diligence-xxx-piece-yyy.*</code></td><td>—</td><td>Pièce reçue en réponse à une diligence</td></tr>
<tr><td><code>diligence-xxx-piece-yyy.md</code></td><td>—</td><td>Texte extrait par OCR d'une pièce de diligence</td></tr>
<tr><td><code>pea.docx</code></td><td>PEA</td><td>Plan d'Entretien Annoté par l'expert (voir section 7)</td></tr>
<tr><td><code>paa.docx</code></td><td>PAA</td><td>Plan d'Analyse Annoté par l'expert (voir section 7)</td></tr>
<tr><td><code>tre.docx</code></td><td>TRE</td><td>Template de Rapport d'Expertise (modèle avec placeholders <code>&lt;&lt;...&gt;&gt;</code>)</td></tr>
<tr><td><code>place_holders.csv</code></td><td>—</td><td>Valeurs des placeholders extraites de la réquisition (Step 1), utilisées pour les substitutions dans <code>tre.docx</code> (Step 4)</td></tr>
<tr><td><code>pre.docx</code></td><td>PRE</td><td>Pré-Rapport d'Expertise généré</td></tr>
<tr><td><code>dac.docx</code></td><td>DAC</td><td>Document d'Analyse Contradictoire</td></tr>
<tr><td><code>ref.docx</code></td><td>REF</td><td>Rapport d'Expertise Final — pré-rapport ajusté et validé par l'expert</td></tr>
<tr><td><code>&lt;dossier-xxx&gt;.zip</code></td><td>—</td><td>Archive immuable contenant tous les fichiers du dossier</td></tr>
<tr><td><code>&lt;dossier-xxx&gt;-timbre.txt</code></td><td>—</td><td>Fichier timbre : date de création, hash SHA-256 du .zip. Stocké sur S3 pour horodatage technique.</td></tr>
</tbody>
</table>


### Détail par étape

### Step 1 — Création dossier

<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<tr><td style="width:150px;"><strong>Objectif</strong></td><td>Importer les fichiers du dossier, extraire le texte par OCR, identifier les questions et les valeurs de placeholders</td></tr>
<tr><td><strong>Entrée</strong></td><td><code>ordonnance.pdf</code> + zéro ou plusieurs <code>piece-xxx.pdf/.docx/.img</code></td></tr>
<tr><td><strong>Traitement</strong></td><td>OCR (judi-ocr) → conversion PDF/scan en Markdown. Extraction des questions numérotées Q1..Qn et des valeurs de placeholders depuis l'ordonnance.</td></tr>
<tr><td><strong>Sortie</strong></td><td><code>ordonnance.md</code>, <code>piece-xxx.md</code>, <code>questions.md</code>, <code>place_holders.csv</code></td></tr>
<tr><td><strong>Stockage</strong></td><td>Entrées dans <code>C:\judi-expert\&lt;nom-dossier&gt;\step1\in</code> · Sorties dans <code>step1\out</code></td></tr>
<tr><td><strong>Rôle expert</strong></td><td>Vérifier le texte extrait, corriger les erreurs OCR, valider</td></tr>
<tr><td><strong>Verrouillage</strong></td><td>Validation → passage au Step 2, Step 1 non modifiable</td></tr>
</table>

### Step 2 — Préparation investigations

<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<tr><td style="width:150px;"><strong>Objectif</strong></td><td>Générer un plan d'entretien (PE) ou un plan d'analyse (PA) structuré</td></tr>
<tr><td><strong>Entrée</strong></td><td><code>ordonnance.md</code> + TPE (Mode Entretien) ou TPA (Mode Analyse) + <code>piece-xxx.md</code></td></tr>
<tr><td><strong>Traitement</strong></td><td>Récupération template et corpus (judi-rag) → génération PE ou PA (judi-llm). En Mode Analyse, génération de courriers de diligence.</td></tr>
<tr><td><strong>Sortie (Mode Entretien)</strong></td><td><code>pe.md</code>, <code>pe.docx</code></td></tr>
<tr><td><strong>Sortie (Mode Analyse)</strong></td><td><code>pa.md</code>, <code>pa.docx</code>, <code>diligence-xxx.docx</code></td></tr>
<tr><td><strong>Stockage</strong></td><td>Entrées dans <code>C:\judi-expert\&lt;nom-dossier&gt;\step2\in</code> · Sorties dans <code>step2\out</code></td></tr>
<tr><td><strong>Rôle expert</strong></td><td>Télécharger le PE/PA, l'adapter, mener les entretiens ou analyses, valider</td></tr>
<tr><td><strong>Verrouillage</strong></td><td>Validation → passage au Step E/A (action expert), Step 2 non modifiable</td></tr>
</table>

### Step E/A — Entretien ou Analyse sur pièces (action expert)

<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<tr><td style="width:150px;"><strong>Objectif</strong></td><td>L'expert mène ses entretiens (Mode Entretien) ou ses analyses sur pièces (Mode Analyse) et annote le plan généré</td></tr>
<tr><td><strong>Entrée</strong></td><td>PE (<code>pe.md</code> / <code>pe.docx</code>) en Mode Entretien, ou PA (<code>pa.md</code> / <code>pa.docx</code>) en Mode Analyse</td></tr>
<tr><td><strong>Traitement</strong></td><td>Aucun traitement IA — travail de l'expert hors application</td></tr>
<tr><td><strong>Sortie</strong></td><td><code>pea.docx</code> (Plan d'Entretien Annoté) ou <code>paa.docx</code> (Plan d'Analyse Annoté) avec annotations balisées</td></tr>
<tr><td><strong>Rôle expert</strong></td><td>Mener les entretiens ou analyses, annoter le plan avec les conventions de balisage (@dires, @analyse, @verbatim, @question, @reference)</td></tr>
<tr><td><strong>Note</strong></td><td>Cette étape se déroule entre le Step 2 et le Step 3. Elle n'est pas gérée par l'application (pas de bouton d'action). L'expert travaille sur le document hors ligne puis l'importe au Step 4.</td></tr>
</table>

### Step 3 — Consolidation documentaire

<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<tr><td style="width:150px;"><strong>Objectif</strong></td><td>Importer les pièces complémentaires issues des diligences et les convertir en Markdown</td></tr>
<tr><td><strong>Entrée</strong></td><td><code>diligence-xxx-piece-yyy.pdf/.docx/.img</code> (fichiers de réponse aux diligences)</td></tr>
<tr><td><strong>Traitement</strong></td><td>OCR (judi-ocr) → extraction texte en format .md pour les pièces PDF/scan</td></tr>
<tr><td><strong>Sortie</strong></td><td><code>diligence-xxx-piece-yyy.md</code> pour chaque fichier nécessitant extraction</td></tr>
<tr><td><strong>Stockage</strong></td><td>Entrées dans <code>C:\judi-expert\&lt;nom-dossier&gt;\step3\in</code> · Sorties dans <code>step3\out</code></td></tr>
<tr><td><strong>Rôle expert</strong></td><td>Téléverser les pièces reçues, vérifier les extractions, valider</td></tr>
<tr><td><strong>Verrouillage</strong></td><td>Validation → passage au Step 4, Step 3 non modifiable</td></tr>
</table>

### Step 4 — Production pré-rapport

<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<tr><td style="width:150px;"><strong>Objectif</strong></td><td>Produire le pré-rapport d'expertise et le document d'analyse contradictoire</td></tr>
<tr><td><strong>Entrée</strong></td><td><code>pea.docx</code> (Mode Entretien) ou <code>paa.docx</code> (Mode Analyse) + <code>tre.docx</code> + <code>place_holders.csv</code> + documents complémentaires Step 3 (si existants)</td></tr>
<tr><td><strong>Traitement</strong></td><td>Interprétation des annotations balisées (@dires, @analyse, @verbatim, @question, @reference) → génération PRE et DAC (judi-llm) → substitution des placeholders et remplissage du <code>tre.docx</code> (docxtpl)</td></tr>
<tr><td><strong>Sortie</strong></td><td><code>pre.docx</code> (Pré-Rapport d'Expertise), <code>dac.docx</code> (Document d'Analyse Contradictoire)</td></tr>
<tr><td><strong>Stockage</strong></td><td>Entrées dans <code>C:\judi-expert\&lt;nom-dossier&gt;\step4\in</code> · Sorties dans <code>step4\out</code></td></tr>
<tr><td><strong>Rôle expert</strong></td><td>Relire PRE et DAC, affiner les conclusions, valider</td></tr>
<tr><td><strong>Verrouillage</strong></td><td>Validation → passage au Step 5, Step 4 non modifiable</td></tr>
</table>

### Step 5 — Finalisation et archivage sécurisé

<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<tr><td style="width:150px;"><strong>Objectif</strong></td><td>Importer le rapport final ajusté par l'expert et archiver l'ensemble du dossier avec horodatage</td></tr>
<tr><td><strong>Entrée</strong></td><td><code>ref.docx</code> — rapport d'expertise final (pré-rapport ajusté et validé par l'expert)</td></tr>
<tr><td><strong>Traitement</strong></td><td>Création d'une archive ZIP contenant tous les fichiers du dossier. Génération d'un fichier timbre (date + hash SHA-256 du .zip). Stockage du timbre sur S3.</td></tr>
<tr><td><strong>Sortie</strong></td><td><code>&lt;dossier-xxx&gt;.zip</code> (archive immuable), <code>&lt;dossier-xxx&gt;-timbre.txt</code> (horodatage technique)</td></tr>
<tr><td><strong>Stockage</strong></td><td>Entrées dans <code>C:\judi-expert\&lt;nom-dossier&gt;\step5\in</code> · Sorties dans <code>step5\out</code></td></tr>
<tr><td><strong>Rôle expert</strong></td><td>Importer le rapport final ajusté, valider pour archivage définitif. L'expert peut compléter par un horodatage juridiquement certifié (solutions externes proposées dans le manuel utilisateur).</td></tr>
<tr><td><strong>Verrouillage</strong></td><td>Validation → dossier fermé, aucune modification possible</td></tr>
</table>

### Cycle de vie d'un dossier

```
Création (ticket valide)
    │
    ▼
  Step 1 (Création dossier):           initial ──► en_cours ──► valide
    │
    ▼
  Step 2 (Préparation investigations): initial ──► en_cours ──► valide
    │
    ▼
  Step E/A (Entretien ou Analyse):     action expert hors application
    │                                  (annotation PE → PEA ou PA → PAA)
    ▼
  Step 3 (Consolidation documentaire): initial ──► en_cours ──► valide
    │
    ▼
  Step 4 (Production pré-rapport):     initial ──► en_cours ──► valide
    │
    ▼
  Step 5 (Finalisation et archivage):  initial ──► en_cours ──► valide
    │
    ▼
  Dossier: actif ──► fermé
```

---

## 2. Glossaire — Termes métier

<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<thead>
<tr style="background-color: #f0f0f0;">
  <th>Abréviation</th><th>Terme complet</th><th>Description</th>
</tr>
</thead>
<tbody>
<tr><td>Dossier</td><td>Dossier d'expertise</td><td>Unité de travail regroupant les 5 étapes d'une expertise judiciaire</td></tr>
<tr><td>QT</td><td>Questions du Tribunal</td><td>Questions posées par la juridiction auxquelles l'expert doit répondre, extraites de l'ordonnance</td></tr>
<tr><td>TPE</td><td>Template de Plan d'Entretien</td><td>Trame personnelle de l'expert définissant la structure de ses entretiens (<code>tpe.md</code> ou <code>tpe.docx</code>)</td></tr>
<tr><td>TPA</td><td>Template de Plan d'Analyse</td><td>Trame personnelle de l'expert définissant la structure de ses analyses sur pièces (<code>tpa.md</code> ou <code>tpa.docx</code>)</td></tr>
<tr><td>PE</td><td>Plan d'Entretien</td><td>Document <code>pe.md</code> / <code>pe.docx</code> généré au Step 2 (Mode Entretien)</td></tr>
<tr><td>PA</td><td>Plan d'Analyse</td><td>Document <code>pa.md</code> / <code>pa.docx</code> généré au Step 2 (Mode Analyse)</td></tr>
<tr><td>PEA</td><td>Plan d'Entretien Annoté</td><td>Document <code>pea.docx</code> — PE annoté par l'expert (voir section 7). Fichier d'entrée du Step 4 en Mode Entretien.</td></tr>
<tr><td>PAA</td><td>Plan d'Analyse Annoté</td><td>Document <code>paa.docx</code> — PA annoté par l'expert (voir section 7). Fichier d'entrée du Step 4 en Mode Analyse.</td></tr>
<tr><td>TRE</td><td>Template de Rapport d'Expertise</td><td>Fichier <code>tre.docx</code> avec placeholders <code>&lt;&lt;...&gt;&gt;</code> utilisé au Step 4.</td></tr>
<tr><td>PRE</td><td>Pré-Rapport d'Expertise</td><td>Document <code>pre.docx</code> généré au Step 4</td></tr>
<tr><td>DAC</td><td>Document d'Analyse Contradictoire</td><td>Document <code>dac.docx</code> généré au Step 4</td></tr>
<tr><td>REF</td><td>Rapport d'Expertise Final</td><td>Document <code>ref.docx</code> — pré-rapport ajusté, importé au Step 5</td></tr>
<tr><td>Réquisition</td><td>Ordonnance du tribunal</td><td>Document officiel (<code>ordonnance.pdf</code>)</td></tr>
<tr><td>Ticket</td><td>Code d'accès</td><td>Code unique acheté via Stripe</td></tr>
<tr><td>Domaine</td><td>Spécialité d'expertise</td><td>Psychologie, psychiatrie, médecine légale, bâtiment ou comptabilité</td></tr>
<tr><td>Corpus</td><td>Base documentaire</td><td>Documents de référence par domaine utilisés par le RAG</td></tr>
<tr><td>Mode Entretien</td><td>Mode d'expertise</td><td>Expertise basée sur des entretiens → TPE, PE, PEA</td></tr>
<tr><td>Mode Analyse</td><td>Mode d'expertise</td><td>Expertise basée sur l'analyse documentaire → TPA, PA, PAA</td></tr>
</tbody>
</table>

## 3. Glossaire — Infrastructure

<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<thead>
<tr style="background-color: #f0f0f0;">
  <th>Terme</th><th>Description</th>
</tr>
</thead>
<tbody>
<tr><td>Application Locale</td><td>Application desktop conteneurisée (Docker Compose, 4 conteneurs). Toutes les données restent en local.</td></tr>
<tr><td>Site Central</td><td>Plateforme web AWS (inscriptions, paiements Stripe, distribution corpus RAG, administration).</td></tr>
<tr><td>Amorce</td><td>Lanceur de l'Application Locale. Démarre Docker puis les 4 conteneurs et ouvre le navigateur.</td></tr>
</tbody>
</table>

## 4. Glossaire — Composants techniques

<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<thead>
<tr style="background-color: #f0f0f0;">
  <th>Composant</th><th>Description</th>
</tr>
</thead>
<tbody>
<tr><td>judi-web</td><td>Conteneur principal : frontend Next.js (port 3000) + backend FastAPI (port 8000) + base SQLite</td></tr>
<tr><td>judi-llm</td><td>Conteneur LLM : Ollama + Mistral 7B Instruct v0.3 (port 11434). Exécution locale.</td></tr>
<tr><td>judi-rag</td><td>Conteneur base vectorielle : Qdrant (ports 6333/6334). Stocke les embeddings du corpus domaine.</td></tr>
<tr><td>judi-ocr</td><td>Conteneur OCR : Tesseract + pdf2image + PyMuPDF (port 8001).</td></tr>
<tr><td>RAG</td><td>Retrieval-Augmented Generation.</td></tr>
<tr><td>LLM</td><td>Large Language Model. Modèle de langage (Mistral 7B).</td></tr>
<tr><td>OCR</td><td>Optical Character Recognition.</td></tr>
<tr><td>Embedding</td><td>Représentation vectorielle d'un texte. Modèle : <code>all-MiniLM-L6-v2</code>.</td></tr>
</tbody>
</table>

## 5. Glossaire — AWS (Site Central)

<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<thead>
<tr style="background-color: #f0f0f0;">
  <th>Service</th><th>Description</th>
</tr>
</thead>
<tbody>
<tr><td>ECS Fargate</td><td>Service AWS d'exécution de conteneurs sans serveur</td></tr>
<tr><td>ECR</td><td>Elastic Container Registry</td></tr>
<tr><td>RDS</td><td>Relational Database Service. Base PostgreSQL managée</td></tr>
<tr><td>Cognito</td><td>Service d'authentification AWS</td></tr>
<tr><td>ALB</td><td>Application Load Balancer</td></tr>
<tr><td>EventBridge</td><td>Scheduler AWS (arrêt 20h, démarrage 8h)</td></tr>
<tr><td>SES</td><td>Simple Email Service</td></tr>
<tr><td>CloudFront</td><td>CDN AWS</td></tr>
</tbody>
</table>

## 6. Statuts et cycles de vie

<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<thead>
<tr style="background-color: #f0f0f0;">
  <th>Entité</th><th>Transitions</th><th>Signification</th>
</tr>
</thead>
<tbody>
<tr><td>Step</td><td><code>initial</code> → <code>en_cours</code> → <code>valide</code></td><td>non commencée → en cours → verrouillée</td></tr>
<tr><td>Dossier</td><td><code>actif</code> → <code>fermé</code></td><td>fermé après validation du Step 5</td></tr>
<tr><td>Ticket</td><td><code>actif</code> → <code>utilise</code> / <code>expire</code></td><td>utilisé lors de la création d'un dossier</td></tr>
</tbody>
</table>

---

## 7. Conventions d'annotation des documents PEA / PAA

Les documents PEA et PAA sont les plans annotés par l'expert en style télégraphique. L'expert complète le PE ou le PA avec des annotations balisées interprétées lors de la génération du pré-rapport (Step 4).

### Balises d'annotation

<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<thead>
<tr style="background-color: #f0f0f0;">
  <th>Balise</th><th>Syntaxe</th><th>Signification</th>
</tr>
</thead>
<tbody>
<tr><td>@dires</td><td><code>@dires ..... \@</code></td><td>Selon les dires de l'interviewé</td></tr>
<tr><td>@analyse</td><td><code>@analyse ..... \@</code></td><td>Selon l'analyse de l'expert</td></tr>
<tr><td>@verbatim</td><td><code>@verbatim ..... \@</code></td><td>Expression textuelle mot pour mot</td></tr>
<tr><td>@question</td><td><code>@question n\@</code></td><td>Remplace par la question réquisition N° n</td></tr>
<tr><td>@reference</td><td><code>@reference section xxx \@</code></td><td>Substitue les sections dires et analyses relatives à la section xxx</td></tr>
</tbody>
</table>

### Exemple d'annotation

```
@question 3\@

@dires Le patient indique avoir ressenti des douleurs depuis mars 2024 \@

@analyse L'expert note une cohérence entre les déclarations et les pièces médicales \@

@verbatim "Je ne pouvais plus marcher sans aide depuis l'accident" \@

@reference section antécédents médicaux \@
```

### Règles d'utilisation

- Les balises sont ouvrantes (`@balise`) et fermantes (`\@`), y compris `@question n\@`
- Le contenu entre balises est en style télégraphique
- Plusieurs balises peuvent se succéder dans une même section
- L'expert est libre d'ajouter du texte non balisé entre les annotations

---

## 8. Placeholders du Template de Rapport (`tre.docx`)

Le fichier `tre.docx` (Template de Rapport d'Expertise) contient des champs `<<nom_placeholder>>` qui sont automatiquement substitués lors de la génération du pré-rapport au Step 4. Les valeurs sont extraites de l'ordonnance au Step 1 et stockées dans `place_holders.csv`.

### Fichier `place_holders.csv`

- **Format** : CSV séparateur `;` — `nom_placeholder;valeur`
- **Génération** : extrait au Step 1 depuis l'ordonnance
- **Validation** : l'expert vérifie les valeurs
- **Modification** : l'expert peut éditer directement
- **Utilisation au Step 4** : réutiliser ou importer modifié
- **Archivage** : fichier extrait et modifié conservés dans l'archive ZIP

### Exemple

```csv
nom_placeholder;valeur
nom_expert;Dr. Martin Dupont
prenom_expert;Martin
titre_expert;Expert judiciaire en psychologie
date_mission;15/03/2025
tribunal;Tribunal judiciaire de Paris
reference_dossier;RG 24/12345
nom_expertise;Expertise psychologique
nom_demandeur;Jean Durand
prenom_demandeur;Jean
nom_defendeur;Marie Lambert
prenom_defendeur;Marie
objet_mission;Évaluation du préjudice psychologique
date_ordonnance;10/02/2025
juridiction;Tribunal judiciaire
ville_juridiction;Paris
magistrat;Mme la Juge Lefèvre
date_rapport;
date_entretien;
lieu_entretien;
```

### Liste des placeholders prédéfinis

<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<thead>
<tr style="background-color: #f0f0f0;">
  <th>Placeholder</th><th>Description</th><th>Source d'extraction</th>
</tr>
</thead>
<tbody>
<tr><td><code>&lt;&lt;nom_expert&gt;&gt;</code></td><td>Nom de famille de l'expert</td><td>Configuration locale</td></tr>
<tr><td><code>&lt;&lt;prenom_expert&gt;&gt;</code></td><td>Prénom de l'expert</td><td>Configuration locale</td></tr>
<tr><td><code>&lt;&lt;titre_expert&gt;&gt;</code></td><td>Titre professionnel de l'expert</td><td>Configuration locale</td></tr>
<tr><td><code>&lt;&lt;date_mission&gt;&gt;</code></td><td>Date de la mission d'expertise</td><td>Ordonnance</td></tr>
<tr><td><code>&lt;&lt;tribunal&gt;&gt;</code></td><td>Nom complet du tribunal</td><td>Ordonnance</td></tr>
<tr><td><code>&lt;&lt;reference_dossier&gt;&gt;</code></td><td>Numéro de référence du dossier (RG)</td><td>Ordonnance</td></tr>
<tr><td><code>&lt;&lt;nom_expertise&gt;&gt;</code></td><td>Intitulé de l'expertise</td><td>Ordonnance</td></tr>
<tr><td><code>&lt;&lt;nom_demandeur&gt;&gt;</code></td><td>Nom du demandeur</td><td>Ordonnance</td></tr>
<tr><td><code>&lt;&lt;prenom_demandeur&gt;&gt;</code></td><td>Prénom du demandeur</td><td>Ordonnance</td></tr>
<tr><td><code>&lt;&lt;nom_defendeur&gt;&gt;</code></td><td>Nom du défendeur</td><td>Ordonnance</td></tr>
<tr><td><code>&lt;&lt;prenom_defendeur&gt;&gt;</code></td><td>Prénom du défendeur</td><td>Ordonnance</td></tr>
<tr><td><code>&lt;&lt;objet_mission&gt;&gt;</code></td><td>Objet de la mission d'expertise</td><td>Ordonnance</td></tr>
<tr><td><code>&lt;&lt;date_ordonnance&gt;&gt;</code></td><td>Date de l'ordonnance</td><td>Ordonnance</td></tr>
<tr><td><code>&lt;&lt;juridiction&gt;&gt;</code></td><td>Type de juridiction</td><td>Ordonnance</td></tr>
<tr><td><code>&lt;&lt;ville_juridiction&gt;&gt;</code></td><td>Ville de la juridiction</td><td>Ordonnance</td></tr>
<tr><td><code>&lt;&lt;magistrat&gt;&gt;</code></td><td>Nom du magistrat ayant ordonné l'expertise</td><td>Ordonnance</td></tr>
<tr><td><code>&lt;&lt;date_rapport&gt;&gt;</code></td><td>Date de rédaction du rapport</td><td>Saisie manuelle par l'expert</td></tr>
<tr><td><code>&lt;&lt;date_entretien&gt;&gt;</code></td><td>Date de l'entretien</td><td>Saisie manuelle par l'expert</td></tr>
<tr><td><code>&lt;&lt;lieu_entretien&gt;&gt;</code></td><td>Lieu de l'entretien</td><td>Saisie manuelle par l'expert</td></tr>
</tbody>
</table>

### Placeholders supplémentaires (détectés depuis le TRE)

<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<thead>
<tr style="background-color: #f0f0f0;">
  <th>Placeholder</th><th>Description</th><th>Source d'extraction</th>
</tr>
</thead>
<tbody>
<tr><td><code>&lt;&lt;date_naissance_demandeur&gt;&gt;</code></td><td>Date de naissance de la personne expertisée</td><td>Ordonnance</td></tr>
<tr><td><code>&lt;&lt;nom_requerant&gt;&gt;</code></td><td>Nom du requérant (OPJ, magistrat ayant requis)</td><td>Ordonnance</td></tr>
<tr><td><code>&lt;&lt;qualite_requerant&gt;&gt;</code></td><td>Qualité du requérant (ex: Officier de Police Judiciaire)</td><td>Ordonnance</td></tr>
<tr><td><code>&lt;&lt;ville_requerant&gt;&gt;</code></td><td>Ville de résidence du requérant</td><td>Ordonnance</td></tr>
<tr><td><code>&lt;&lt;heure_debut_entretien&gt;&gt;</code></td><td>Heure de début de l'entretien</td><td>Saisie manuelle par l'expert</td></tr>
<tr><td><code>&lt;&lt;duree_entretien&gt;&gt;</code></td><td>Durée totale de l'entretien</td><td>Saisie manuelle par l'expert</td></tr>
<tr><td><code>&lt;&lt;accompagnant_present&gt;&gt;</code></td><td>Présence d'un accompagnant (Oui/Non)</td><td>Saisie manuelle par l'expert</td></tr>
<tr><td><code>&lt;&lt;nom_accompagnant&gt;&gt;</code></td><td>Nom de l'accompagnant (si présent)</td><td>Saisie manuelle par l'expert</td></tr>
<tr><td><code>&lt;&lt;qualite_accompagnant&gt;&gt;</code></td><td>Qualité de l'accompagnant (parent, avocat, etc.)</td><td>Saisie manuelle par l'expert</td></tr>
<tr><td><code>&lt;&lt;pieces_consultees&gt;&gt;</code></td><td>Liste des pièces consultées pour l'expertise</td><td>Ordonnance + Step 1</td></tr>
<tr><td><code>&lt;&lt;dires_mere&gt;&gt;</code></td><td>Dires concernant la relation à la mère</td><td>PEA — @dires</td></tr>
<tr><td><code>&lt;&lt;analyse_mere&gt;&gt;</code></td><td>Analyse de la relation à la mère</td><td>PEA — @analyse</td></tr>
<tr><td><code>&lt;&lt;dires_pere&gt;&gt;</code></td><td>Dires concernant la relation au père</td><td>PEA — @dires</td></tr>
<tr><td><code>&lt;&lt;analyse_pere&gt;&gt;</code></td><td>Analyse de la relation au père</td><td>PEA — @analyse</td></tr>
<tr><td><code>&lt;&lt;dires_fratrie&gt;&gt;</code></td><td>Dires concernant la fratrie</td><td>PEA — @dires</td></tr>
<tr><td><code>&lt;&lt;analyse_fratrie&gt;&gt;</code></td><td>Analyse des relations fraternelles</td><td>PEA — @analyse</td></tr>
<tr><td><code>&lt;&lt;dires_loisirs&gt;&gt;</code></td><td>Dires sur les centres d'intérêt et loisirs</td><td>PEA — @dires</td></tr>
<tr><td><code>&lt;&lt;analyse_loisirs&gt;&gt;</code></td><td>Analyse des centres d'intérêt</td><td>PEA — @analyse</td></tr>
<tr><td><code>&lt;&lt;dires_social&gt;&gt;</code></td><td>Dires sur la vie sociale et amicale</td><td>PEA — @dires</td></tr>
<tr><td><code>&lt;&lt;analyse_social&gt;&gt;</code></td><td>Analyse de la vie sociale</td><td>PEA — @analyse</td></tr>
<tr><td><code>&lt;&lt;dires_amour&gt;&gt;</code></td><td>Dires sur la vie amoureuse et affective</td><td>PEA — @dires</td></tr>
<tr><td><code>&lt;&lt;analyse_amour&gt;&gt;</code></td><td>Analyse de la vie affective</td><td>PEA — @analyse</td></tr>
<tr><td><code>&lt;&lt;dires_scolarite&gt;&gt;</code></td><td>Dires sur la scolarité</td><td>PEA — @dires</td></tr>
<tr><td><code>&lt;&lt;analyse_scolarite&gt;&gt;</code></td><td>Analyse du parcours scolaire</td><td>PEA — @analyse</td></tr>
<tr><td><code>&lt;&lt;dires_pro&gt;&gt;</code></td><td>Dires sur la vie professionnelle</td><td>PEA — @dires</td></tr>
<tr><td><code>&lt;&lt;analyse_pro&gt;&gt;</code></td><td>Analyse de la vie professionnelle</td><td>PEA — @analyse</td></tr>
<tr><td><code>&lt;&lt;dires_avant_faits&gt;&gt;</code></td><td>Dires sur le contexte avant les faits</td><td>PEA — @dires</td></tr>
<tr><td><code>&lt;&lt;dires_pendant_faits&gt;&gt;</code></td><td>Dires sur le déroulement des faits</td><td>PEA — @dires</td></tr>
<tr><td><code>&lt;&lt;dires_revelation&gt;&gt;</code></td><td>Dires sur le contexte de la révélation</td><td>PEA — @dires</td></tr>
<tr><td><code>&lt;&lt;dires_apres_plainte&gt;&gt;</code></td><td>Dires sur la période après le dépôt de plainte</td><td>PEA — @dires</td></tr>
<tr><td><code>&lt;&lt;etude_pieces&gt;&gt;</code></td><td>Analyse comparative des pièces et des dires</td><td>PEA — @analyse + Step 1</td></tr>
<tr><td><code>&lt;&lt;dires_sante&gt;&gt;</code></td><td>Dires sur la relation au corps et à la santé</td><td>PEA — @dires</td></tr>
<tr><td><code>&lt;&lt;analyse_sante&gt;&gt;</code></td><td>Analyse de la santé physique et psychique</td><td>PEA — @analyse</td></tr>
<tr><td><code>&lt;&lt;analyse_cognitifs&gt;&gt;</code></td><td>Analyse des éléments cognitifs</td><td>PEA — @analyse</td></tr>
<tr><td><code>&lt;&lt;dires_personnalite&gt;&gt;</code></td><td>Dires sur les éléments de personnalité</td><td>PEA — @dires</td></tr>
<tr><td><code>&lt;&lt;analyse_personnalite&gt;&gt;</code></td><td>Analyse des éléments de personnalité</td><td>PEA — @analyse</td></tr>
<tr><td><code>&lt;&lt;analyse_entretien&gt;&gt;</code></td><td>Observation clinique pendant l'entretien</td><td>PEA — @analyse</td></tr>
<tr><td><code>&lt;&lt;rapport_sexualite&gt;&gt;</code></td><td>Évaluation du rapport à la sexualité</td><td>PEA — @dires / @analyse</td></tr>
<tr><td><code>&lt;&lt;analyse_echelle&gt;&gt;</code></td><td>Résultats et interprétation de l'échelle psychométrique (IES-R, etc.)</td><td>PEA — @analyse</td></tr>
<tr><td><code>&lt;&lt;symptomes_intrusion&gt;&gt;</code></td><td>Symptômes d'intrusion rapportés</td><td>PEA — @dires</td></tr>
<tr><td><code>&lt;&lt;symptomes_evitement&gt;&gt;</code></td><td>Symptômes d'évitement rapportés</td><td>PEA — @dires</td></tr>
<tr><td><code>&lt;&lt;symptomes_cognitions&gt;&gt;</code></td><td>Symptômes d'altération des cognitions et de l'humeur</td><td>PEA — @dires</td></tr>
<tr><td><code>&lt;&lt;symptomes_eveil&gt;&gt;</code></td><td>Symptômes d'éveil et de réactivité</td><td>PEA — @dires</td></tr>
<tr><td><code>&lt;&lt;symptomes_dissociatifs&gt;&gt;</code></td><td>Symptômes dissociatifs (dépersonnalisation, déréalisation)</td><td>PEA — @dires</td></tr>
<tr><td><code>&lt;&lt;analyse_retentissement&gt;&gt;</code></td><td>Synthèse de l'évaluation du retentissement psychologique</td><td>PEA — @analyse</td></tr>
<tr><td><code>&lt;&lt;conclusion_questions&gt;&gt;</code></td><td>Bloc conclusion : questions de la mission avec réponses (généré via @question + @reference)</td><td>PEA — @question / @reference + LLM</td></tr>
</tbody>
</table>

> **Note** : cette liste est extensible. L'expert peut ajouter des placeholders personnalisés dans son `tre.docx` et renseigner les valeurs correspondantes dans le CSV.
