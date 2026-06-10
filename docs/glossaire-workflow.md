# Glossaire & Workflow — Judi-Expert

Ce document centralise les termes, acronymes et concepts du projet, ainsi que le workflow fonctionnel complet de l'expertise judiciaire assistée par IA.

> Voir aussi : [Architecture](architecture.md) · [Guide utilisateur](guide-utilisateur.md) · [Méthodologie](methodologie.md) · [Développement](developpement.md)

---

## 1. Workflow fonctionnel

### Vue d'ensemble

Judi-Expert propose **deux types de workflow**, choisis à la **création du dossier** :

| Type | Étapes applicatives | Usage typique |
|------|---------------------|---------------|
| **Standard** | 5 steps + Step E/A (hors appli) | Expertise complète assistée par IA : ordonnance → TRE → PREA → PRE → archivage |
| **Simple** | 2 steps | L'expert dispose déjà d'un **PRE** rédigé : mise en forme linguistique → archivage |

---

### Workflow standard (5 étapes + E/A)

L'expert judiciaire utilise le workflow standard pour produire un rapport d'expertise en **5 étapes séquentielles**, plus une **étape intermédiaire E/A** (Entretien ou Analyse) réalisée par l'expert **hors application, après le Step 3**. Chaque étape gérée par l'application doit être validée avant de passer à la suivante. Une étape validée est verrouillée et ne peut plus être modifiée.

Le **TRE** (Template de Rapport d'Expertise, fichier `tre.docx`) est le **document central** du workflow standard. Il contient deux types de méta-instructions :
- **Placeholders** : `<<nom>>` — champs substitués par des valeurs extraites ou saisies
- **Annotations** : `@type contenu@` — instructions de génération interprétées par le moteur

> **Note importante — TRE, PREA et PRE**
>
> À l'issue du **Step 2**, le fichier `prea.docx` est une **copie du `tre.docx` validée syntaxiquement** (placeholders et annotations conformes). Ce n'est pas encore le rapport final : c'est le document de travail de l'expert.
>
> Le **PREA** est ensuite **enrichi progressivement** par les notes de l'expert au **Step E/A** (après le Step 3). Ce `prea.docx` complété est **injecté au Step 4** pour permettre la production du **`pre.docx`** (Pré-Rapport d'Expertise en texte lisible).

<table border="2" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%; margin: 1em 0;">
<tr style="background-color: #e3f2fd;">
  <td colspan="6" style="text-align: center; font-weight: bold; padding: 12px;">
    SITE CENTRAL (AWS)<br/>
    <span style="font-weight: normal; font-size: 0.9em;">Inscription → Achat ticket (Stripe) → Envoi ticket par email</span>
  </td>
</tr>
<tr><td colspan="6" style="text-align: center; padding: 4px;">↓ ticket</td></tr>
<tr style="background-color: #f5f5f5;">
  <td colspan="6" style="text-align: center; font-weight: bold; padding: 8px;">APPLICATION LOCALE (PC Expert)</td>
</tr>
<tr>
  <th style="width: 16%; background-color: #e8f5e9; text-align: center;">Step 1<br/><small>Création dossier</small></th>
  <th style="width: 16%; background-color: #e8f5e9; text-align: center;">Step 2<br/><small>Validation TRE → PREA</small></th>
  <th style="width: 16%; background-color: #e8f5e9; text-align: center;">Step 3<br/><small>Consolidation doc.</small></th>
  <th style="width: 16%; background-color: #fff8e1; text-align: center;">Step E/A<br/><small>Entretien ou Analyse</small></th>
  <th style="width: 16%; background-color: #e8f5e9; text-align: center;">Step 4<br/><small>Production PRE</small></th>
  <th style="width: 16%; background-color: #e8f5e9; text-align: center;">Step 5<br/><small>Révision &amp; Archivage</small></th>
</tr>
<tr style="font-size: 0.85em;">
  <td style="vertical-align: top;">
    <strong>Entrée :</strong><br/>
    <code>demande.pdf</code><br/>
    <code>piece-xxx.*</code><br/><br/>
    <strong>Sortie :</strong><br/>
    <code>demande.md</code><br/>
    <code>piece-xxx.md</code><br/>
    <code>placeholders.csv</code><br/>
    <code>questions.md</code>
  </td>
  <td style="vertical-align: top;">
    <strong>Entrée :</strong><br/>
    <code>tre.docx</code><br/>
    <code>placeholders.csv</code><br/><br/>
    <strong>Sortie :</strong><br/>
    <code>prea.docx</code><br/>
    <em>(copie TRE validée)</em>
  </td>
  <td style="vertical-align: top;">
    <strong>Entrée :</strong><br/>
    <code>diligence-xxx-piece-yyy.*</code><br/><br/>
    <strong>Sortie :</strong><br/>
    <code>diligence-xxx-piece-yyy.md</code>
  </td>
  <td style="vertical-align: top; background-color: #fff8e1;">
    <strong>Entrée :</strong><br/>
    <code>prea.docx</code><br/>
    pièces Step 3 (si existantes)<br/><br/>
    <strong>Sortie :</strong><br/>
    <code>prea.docx</code><br/>
    <em>(annotations complétées)</em><br/><br/>
    <em>(hors application)</em>
  </td>
  <td style="vertical-align: top;">
    <strong>Entrée :</strong><br/>
    <code>prea.docx</code><br/>
    <code>placeholders.csv</code><br/>
    docs Step 3 (si existants)<br/><br/>
    <strong>Sortie :</strong><br/>
    <code>pre.docx</code><br/>
    <code>dac.docx</code> (optionnel)
  </td>
  <td style="vertical-align: top;">
    <strong>Entrée :</strong><br/>
    <code>ref.docx</code><br/><br/>
    <strong>Sortie :</strong><br/>
    <code>&lt;dossier&gt;.zip</code><br/>
    <code>&lt;dossier&gt;-timbre.txt</code>
  </td>
</tr>
<tr style="font-size: 0.85em; background-color: #fafafa;">
  <td style="text-align: center;"><em>judi-ocr<br/>judi-llm</em></td>
  <td style="text-align: center;"><em>vérification syntaxique<br/>placeholders + annotations</em></td>
  <td style="text-align: center;"><em>judi-ocr</em></td>
  <td style="text-align: center; background-color: #fff8e1;"><em>—</em></td>
  <td style="text-align: center;"><em>judi-rag<br/>judi-llm</em></td>
  <td style="text-align: center;"><em>judi-llm<br/>S3</em></td>
</tr>
</table>

### Workflow simple (2 étapes)

Pour les expertises où l'expert a **déjà rédigé son Pré-Rapport** (`pre.docx`) en dehors de Judi-Expert, le workflow **simple** accélère la finalisation :

| Step | Nom | Entrée | Opération | Sortie |
|------|-----|--------|-----------|--------|
| **1** | Mise en forme linguistique | `pre.docx` | Révision linguistique LLM (préservation verbatim) | `pref.docx` (+ `dac.docx` optionnel) |
| **2** | Archivage | `pref.docx` (Step 1 ou version ajustée) | Archive ZIP + timbre SHA-256 (+ stockage S3) | `<dossier>.zip`, `<dossier>-timbre.txt` |

**Cycle itératif Step 1** : l'expert peut relancer la mise en forme après avoir modifié le PRE ou le PREF, tant que le Step 1 n'est pas validé.

**Acronymes workflow simple** :
- **PRE** — Pré-Rapport d'Expertise (`pre.docx`) — document rédigé par l'expert en amont
- **PREF** — Projet de Rapport d'Expertise Final (`pref.docx`) — PRE après révision linguistique

> Le workflow simple **ne remplace pas** le workflow standard pour une expertise guidée de bout en bout (ordonnance → TRE → investigations → PRE). Les deux coexistent ; le choix est **figé à la création du dossier**.

### Prérequis avant le workflow

1. L'expert s'inscrit sur le **Site Central** et achète un **ticket** via Stripe
2. L'expert installe l'**Application Locale** sur son PC et configure :
   - Son **identifiant** (le mot de passe est celui du Site Central — une connexion Internet est nécessaire pour l'authentification)
   - Son **domaine d'expertise** (psychologie, psychiatrie, etc.)
3. L'expert peut personnaliser :
   - Son **corpus d'expertise** (documents de référence indexés dans la base RAG)
   - Son **TRE** — Template de Rapport d'Expertise (`tre.docx`), document central contenant placeholders `<<...>>` et annotations `@type contenu@`

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
  <td><code>demande.pdf</code>, <code>piece-xxx.*</code></td>
  <td>OCR + structuration LLM</td>
  <td><code>demande.md</code>, <code>piece-xxx.md</code>, <code>placeholders.csv</code>, <code>questions.md</code></td>
</tr>
<tr>
  <td><strong>2</strong></td>
  <td>Validation du TRE → PREA</td>
  <td><code>tre.docx</code>, <code>placeholders.csv</code></td>
  <td>Vérifier la syntaxe du TRE (placeholders, annotations) et produire le PREA</td>
  <td><code>prea.docx</code></td>
</tr>
<tr>
  <td><strong>3</strong></td>
  <td>Consolidation documentaire</td>
  <td><code>diligence-xxx-piece-yyy.*</code></td>
  <td>Extraire les documents complémentaires (OCR)</td>
  <td><code>diligence-xxx-piece-yyy.md</code></td>
</tr>
<tr style="background-color: #fff8e1;">
  <td><strong>E/A</strong></td>
  <td>Entretien ou Analyse sur pièces</td>
  <td><code>prea.docx</code> (issu du Step 2), pièces Step 3 (si existantes)</td>
  <td><em>(action expert hors application)</em> — remplissage des annotations en style télégraphique</td>
  <td><code>prea.docx</code> (annotations complétées)</td>
</tr>
<tr>
  <td><strong>4</strong></td>
  <td>Production pré-rapport</td>
  <td><code>prea.docx</code>, <code>placeholders.csv</code>, docs Step 3 (si existants)</td>
  <td>Substituer les placeholders, reformuler les annotations via LLM, générer éventuellement un DAC</td>
  <td><code>pre.docx</code>, <code>dac.docx</code> (optionnel)</td>
</tr>
<tr>
  <td><strong>5</strong></td>
  <td>Finalisation, révision et archivage</td>
  <td><code>ref.docx</code> (rapport final ajusté)</td>
  <td>Révision, archivage, génération timbre</td>
  <td><code>&lt;nom-dossier&gt;.zip</code>, <code>&lt;nom-dossier&gt;-timbre.txt</code></td>
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
<tr><td><code>demande.pdf</code></td><td>—</td><td>PDF-scan de la demande d'expertise (ordonnance ou réquisition du tribunal)</td></tr>
<tr><td><code>demande.md</code></td><td>—</td><td>Texte de la demande extrait par OCR, structuré en Markdown</td></tr>
<tr><td><code>questions.md</code></td><td>—</td><td>Questions soumises à l'expert, extraites et structurées au Step 1</td></tr>
<tr><td><code>piece-xxx.*</code></td><td>—</td><td>Pièce complémentaire (PDF, DOCX ou image)</td></tr>
<tr><td><code>piece-xxx.md</code></td><td>—</td><td>Texte extrait par OCR d'une pièce complémentaire</td></tr>
<tr><td><code>placeholders.csv</code></td><td>—</td><td>Ensemble clé/valeur des placeholders extraits de la demande (Step 1) : questions numérotées <code>question_1</code>…<code>question_n</code> + métadonnées. Utilisé pour les substitutions au Step 4</td></tr>
<tr><td><code>tre.docx</code></td><td>TRE</td><td>Template de Rapport d'Expertise — document type contenant placeholders <code>&lt;&lt;...&gt;&gt;</code> et annotations <code>@type contenu@</code>. Peut provenir de la configuration, du corpus domaine ou être ad hoc pour l'expertise. Validé au Step 2, il devient le PREA.</td></tr>
<tr><td><code>prea.docx</code></td><td>PREA</td><td>Projet de Rapport d'Expertise Annoté — copie du TRE validé (Step 2), complétée par l'expert (Step E/A) avec les informations collectées en entretien ou en analyse</td></tr>
<tr><td><code>diligence-xxx-piece-yyy.*</code></td><td>—</td><td>Pièce reçue en réponse à une diligence</td></tr>
<tr><td><code>diligence-xxx-piece-yyy.md</code></td><td>—</td><td>Texte extrait par OCR d'une pièce de diligence</td></tr>
<tr><td><code>pre.docx</code></td><td>PRE</td><td>Pré-Rapport d'Expertise généré au Step 4 — rapport en texte lisible après reformulation des annotations et substitution des placeholders</td></tr>
<tr><td><code>dac.docx</code></td><td>DAC</td><td>Document d'Analyse Contradictoire (optionnel) — suggestions pour renforcer et challenger les analyses</td></tr>
<tr><td><code>ref.docx</code></td><td>REF</td><td>Rapport d'Expertise Final — pré-rapport ajusté et validé par l'expert (édition hors application)</td></tr>
<tr><td><code>&lt;nom-dossier&gt;.zip</code></td><td>—</td><td>Archive immuable contenant tous les fichiers du dossier</td></tr>
<tr><td><code>&lt;nom-dossier&gt;-timbre.txt</code></td><td>—</td><td>Fichier timbre : métadonnées (date de création, hash SHA-256 du .zip, nom expert, référence dossier). Stocké sur S3 pour horodatage technique (non juridiquement horlogé). L'archivage longue durée est à la charge de l'expert.</td></tr>
</tbody>
</table>


### Détail par étape

### Step 1 — Création dossier

<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<tr><td style="width:150px;"><strong>Objectif</strong></td><td>Importer la réquisition originale, extraire le texte par OCR, identifier les questions et les valeurs de placeholders</td></tr>
<tr><td><strong>Entrée</strong></td><td><code>demande.pdf</code> + zéro ou plusieurs <code>piece-xxx.pdf/.docx/.img</code></td></tr>
<tr><td><strong>Traitement</strong></td><td>OCR (judi-ocr) → conversion PDF/scan en Markdown. Extraction LLM des questions numérotées (stockées comme <code>question_1</code>…<code>question_n</code> dans <code>placeholders.csv</code> et <code>questions.md</code>) et des valeurs de placeholders depuis la demande.</td></tr>
<tr><td><strong>Sortie</strong></td><td><code>demande.md</code>, <code>piece-xxx.md</code>, <code>placeholders.csv</code>, <code>questions.md</code></td></tr>
<tr><td><strong>Stockage</strong></td><td>Entrées dans <code>C:\judi-expert\&lt;nom-dossier&gt;\step1\in</code> · Sorties dans <code>step1\out</code></td></tr>
<tr><td><strong>Rôle expert</strong></td><td>Vérifier le texte extrait, corriger les erreurs OCR, valider les placeholders et questions extraites</td></tr>
<tr><td><strong>Verrouillage</strong></td><td>Validation → passage au Step 2, Step 1 non modifiable</td></tr>
</table>

### Step 2 — Validation du TRE → PREA

<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<tr><td style="width:150px;"><strong>Objectif</strong></td><td>Sélectionner le TRE et produire le PREA (projet de rapport avec annotations)</td></tr>
<tr><td><strong>Entrée</strong></td><td><code>tre.docx</code> (configuration, corpus domaine ou ad hoc) + <code>placeholders.csv</code></td></tr>
<tr><td><strong>Traitement</strong></td><td>Vérification syntaxique du TRE : placeholders en snake_case, annotations bien formées. Vérification des placeholders du TRE contre <code>placeholders.csv</code>. Copie du TRE validé en <code>prea.docx</code>. Aucune génération LLM.</td></tr>
<tr><td><strong>Sortie</strong></td><td><code>prea.docx</code> — Projet de Rapport d'Expertise Annoté (structure du rapport avec emplacements d'annotations prêts à être remplis)</td></tr>
<tr><td><strong>Stockage</strong></td><td>Entrées dans <code>C:\judi-expert\&lt;nom-dossier&gt;\step2\in</code> · Sorties dans <code>step2\out</code></td></tr>
<tr><td><strong>Rôle expert</strong></td><td>Choisir ou uploader son template, lancer la validation, télécharger le PREA</td></tr>
<tr><td><strong>Verrouillage</strong></td><td>Validation → passage au Step 3, Step 2 non modifiable</td></tr>
</table>

### Step 3 — Consolidation documentaire

<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<tr><td style="width:150px;"><strong>Objectif</strong></td><td>Importer les pièces complémentaires issues des diligences et les convertir en Markdown</td></tr>
<tr><td><strong>Entrée</strong></td><td><code>diligence-xxx-piece-yyy.pdf/.docx/.img</code> (fichiers de réponse aux diligences)</td></tr>
<tr><td><strong>Traitement</strong></td><td>OCR (judi-ocr) → extraction texte en format .md pour les pièces PDF/scan</td></tr>
<tr><td><strong>Sortie</strong></td><td><code>diligence-xxx-piece-yyy.md</code> pour chaque fichier nécessitant extraction</td></tr>
<tr><td><strong>Stockage</strong></td><td>Entrées dans <code>C:\judi-expert\&lt;nom-dossier&gt;\step3\in</code> · Sorties dans <code>step3\out</code></td></tr>
<tr><td><strong>Rôle expert</strong></td><td>Téléverser les pièces reçues, vérifier les extractions, valider</td></tr>
<tr><td><strong>Verrouillage</strong></td><td>Validation → passage au Step E/A (action expert hors application), Step 3 non modifiable</td></tr>
</table>

### Step E/A — Entretien ou Analyse sur pièces (action expert)

<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<tr><td style="width:150px;"><strong>Objectif</strong></td><td>L'expert mène ses entretiens ou ses analyses sur pièces et remplit les annotations du PREA</td></tr>
<tr><td><strong>Entrée</strong></td><td><code>prea.docx</code> produit au Step 2, éventuellement les pièces consolidées au Step 3</td></tr>
<tr><td><strong>Traitement</strong></td><td>Aucun traitement IA — travail de l'expert hors application. L'expert remplit les champs annotation en style télégraphique, de deux façons possibles :
<ul>
<li>Édition directe dans Word sur le <code>prea.docx</code></li>
<li>Utilisation de l'outil d'édition PREA (formulaire avec les annotations comme champs à saisir)</li>
</ul>
L'expert ajoute aussi la conclusion à l'aide d'annotations pour faciliter le rappel des questions et les copies textuelles de sections dans le corps du rapport.</td></tr>
<tr><td><strong>Sortie</strong></td><td><code>prea.docx</code> complété (même fichier, annotations remplies)</td></tr>
<tr><td><strong>Rôle expert</strong></td><td>Mener les entretiens ou analyses, remplir les annotations avec les conventions de balisage (@dires, @analyse, @verbatim, @conclusion, @question, @reference, @cite, etc.)</td></tr>
<tr><td><strong>Note</strong></td><td>Cette étape se déroule <strong>après le Step 3</strong>, avant le Step 4. Elle n'est pas gérée par l'application (pas de bouton d'action). L'expert travaille sur le document hors ligne puis importe le PREA complété au Step 4.</td></tr>
</table>

### Step 4 — Production pré-rapport

<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<tr><td style="width:150px;"><strong>Objectif</strong></td><td>Générer le Pré-Rapport d'Expertise (PRE) à partir du PREA complété</td></tr>
<tr><td><strong>Entrée</strong></td><td><code>prea.docx</code> (complété au Step E/A) + <code>placeholders.csv</code> + documents complémentaires Step 3 (si existants)</td></tr>
<tr><td><strong>Traitement</strong></td><td>
1. Substitution des placeholders <code>&lt;&lt;...&gt;&gt;</code> depuis <code>placeholders.csv</code><br/>
2. Interprétation des annotations <code>@type contenu@</code> : reformulation LLM pour <code>@dires</code> et <code>@analyse</code>, préservation pour <code>@verbatim</code>, résolution des <code>@question</code>, <code>@reference</code>, <code>@cite</code> et <code>@resume</code><br/>
3. Mise en forme en langage compréhensible des contenus en style télégraphique<br/>
4. Génération du PRE et, optionnellement, du DAC</td></tr>
<tr><td><strong>Sortie</strong></td><td><code>pre.docx</code> (Pré-Rapport d'Expertise), <code>dac.docx</code> (Document d'Analyse Contradictoire, optionnel)</td></tr>
<tr><td><strong>Stockage</strong></td><td>Entrées dans <code>C:\judi-expert\&lt;nom-dossier&gt;\step4\in</code> · Sorties dans <code>step4\out</code></td></tr>
<tr><td><strong>Rôle expert</strong></td><td>Importer le PREA complété, relire PRE et DAC, affiner les conclusions. Éditer le PRE hors application pour produire le REF.</td></tr>
<tr><td><strong>Verrouillage</strong></td><td>Validation → passage au Step 5, Step 4 non modifiable</td></tr>
</table>

### Step 5 — Finalisation, révision et archivage sécurisé

<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<tr><td style="width:150px;"><strong>Objectif</strong></td><td>Importer le rapport final ajusté, proposer un service de révision, archiver l'ensemble du dossier avec horodatage et générer le fichier timbre</td></tr>
<tr><td><strong>Entrée</strong></td><td><code>ref.docx</code> — rapport d'expertise final (pré-rapport ajusté et validé par l'expert)</td></tr>
<tr><td><strong>Traitement</strong></td><td>
1. Service de révision (optionnel) : relecture LLM du rapport final (cohérence, orthographe, style)<br/>
2. Création d'une archive ZIP contenant tous les fichiers du dossier<br/>
3. Génération du fichier timbre <code>&lt;nom-dossier&gt;-timbre.txt</code> contenant les métadonnées : date de création, hash SHA-256 du .zip, nom de l'expert, référence dossier, domaine<br/>
4. Stockage du timbre sur S3 (horodatage technique, non juridiquement horlogé)</td></tr>
<tr><td><strong>Sortie</strong></td><td><code>&lt;nom-dossier&gt;.zip</code> (archive immuable), <code>&lt;nom-dossier&gt;-timbre.txt</code> (horodatage technique + métadonnées)</td></tr>
<tr><td><strong>Stockage</strong></td><td>Entrées dans <code>C:\judi-expert\&lt;nom-dossier&gt;\step5\in</code> · Sorties dans <code>step5\out</code></td></tr>
<tr><td><strong>Rôle expert</strong></td><td>Importer le rapport final ajusté, utiliser le service de révision si souhaité, valider pour archivage définitif. L'archivage longue durée est à la charge de l'expert.</td></tr>
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
  Step 2 (Validation TRE → PREA):      initial ──► en_cours ──► valide
    │
    ▼
  Step 3 (Consolidation documentaire): initial ──► en_cours ──► valide
    │
    ▼
  Step E/A (Entretien ou Analyse):     action expert hors application
    │                                  (remplissage des annotations du PREA)
    ▼
  Step 4 (Production PRE):             initial ──► en_cours ──► valide
    │
    ▼
  Step 5 (Révision et archivage):      initial ──► en_cours ──► valide
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
<tr><td>Dossier</td><td>Dossier d'expertise</td><td>Unité de travail. Workflow <strong>standard</strong> : 5 étapes + Step E/A. Workflow <strong>simple</strong> : 2 étapes. Le type est choisi à la création.</td></tr>
<tr><td>PEX</td><td>Personne Expertisée</td><td>Personne évaluée en expertise (plaignant ou mis en cause). Sujet de l'expertise désigné par la juridiction. Remplace l'ancien terme MEC (Mis en Cause).</td></tr>
<tr><td>QT</td><td>Questions du Tribunal</td><td>Questions posées par la juridiction auxquelles l'expert doit répondre, extraites de la demande et stockées comme <code>question_1</code>…<code>question_n</code> dans <code>placeholders.csv</code> et <code>questions.md</code></td></tr>
<tr><td>TRE</td><td>Template de Rapport d'Expertise</td><td>Fichier <code>tre.docx</code> — document type contenant placeholders <code>&lt;&lt;...&gt;&gt;</code> et annotations <code>@type contenu@</code>. Validé au Step 2 pour produire le PREA.</td></tr>
<tr><td>PREA</td><td>Projet de Rapport d'Expertise Annoté</td><td>Fichier <code>prea.docx</code> — copie du TRE validé au Step 2, complétée par l'expert au Step E/A. Fichier d'entrée du Step 4.</td></tr>
<tr><td>PRE</td><td>Pré-Rapport d'Expertise</td><td>Document <code>pre.docx</code> — en workflow <strong>standard</strong>, généré au Step 4 ; en workflow <strong>simple</strong>, importé au Step 1 (rédigé par l'expert en amont)</td></tr>
<tr><td>PREF</td><td>Projet de Rapport d'Expertise Final</td><td>Document <code>pref.docx</code> — PRE après révision linguistique (workflow simple, Step 1)</td></tr>
<tr><td>DAC</td><td>Document d'Analyse Contradictoire</td><td>Document <code>dac.docx</code> généré optionnellement au Step 4 (standard) ou Step 1 (simple)</td></tr>
<tr><td>REF</td><td>Rapport d'Expertise Final</td><td>Document <code>ref.docx</code> — pré-rapport ajusté par l'expert hors application, importé au Step 5</td></tr>
<tr><td>Réquisition</td><td>Demande d'expertise</td><td>Document officiel (<code>demande.pdf</code>) — ordonnance ou réquisition du tribunal</td></tr>
<tr><td>Ticket</td><td>Code d'accès</td><td>Code unique acheté via Stripe</td></tr>
<tr><td>Domaine</td><td>Spécialité d'expertise</td><td>Psychologie, psychiatrie, médecine légale, bâtiment ou comptabilité</td></tr>
<tr><td>Corpus</td><td>Base documentaire</td><td>Documents de référence par domaine utilisés par le RAG</td></tr>
<tr><td>Step E/A</td><td>Entretien ou Analyse</td><td>Étape hors application <strong>après le Step 3</strong>, avant le Step 4 : l'expert remplit les annotations du PREA lors de ses entretiens ou analyses sur pièces</td></tr>
</tbody>
</table>

> **Termes obsolètes** (ne plus utiliser) : PE, PA, **TPE**, TPA, PEA, PAA, `@debut_tpe@`, Mode Entretien / Mode Analyse comme flux parallèles.

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

## 7. Méta-instructions du TRE et conventions d'annotation

Le TRE (Template de Rapport d'Expertise) est le document central du workflow. Il contient deux types de méta-instructions qui pilotent la génération du rapport :

### 7.1 Placeholders `<<nom>>`

Les placeholders sont des champs de substitution directe. Ils sont remplacés par des valeurs issues de `placeholders.csv` (Step 1) ou saisies manuellement par l'expert.

**Syntaxe** : `<<nom_placeholder>>`

**Exemples** : `<<nom_tribunal>>`, `<<nom_magistrat>>`, `<<question_1>>`, `<<nom_pex>>`

### 7.2 Annotations `@type contenu@`

Les annotations sont des instructions de génération interprétées par le moteur au Step 4. Elles indiquent comment traiter le contenu lors de la production du pré-rapport.

### Types d'annotations

<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<thead>
<tr style="background-color: #f0f0f0;">
  <th>Annotation</th><th>Syntaxe</th><th>Rendu dans le PRE</th><th>Traitement</th>
</tr>
</thead>
<tbody>
<tr><td><code>@dires</code></td><td><code>@dires contenu@</code></td><td><strong>Dires :</strong> contenu reformulé</td><td>Reformulation LLM (style professionnel)</td></tr>
<tr><td><code>@analyse</code></td><td><code>@analyse contenu@</code></td><td><strong>Analyse :</strong> contenu reformulé</td><td>Reformulation LLM (style professionnel)</td></tr>
<tr><td><code>@verbatim</code></td><td><code>@verbatim contenu@</code></td><td>« contenu » (entre guillemets)</td><td>Préservé tel quel — aucune modification</td></tr>
<tr><td><code>@question</code></td><td><code>@question n@</code></td><td>Texte de la question n</td><td>Substitution du placeholder <code>question_n</code> depuis <code>placeholders.csv</code></td></tr>
<tr><td><code>@reference</code></td><td><code>@reference @dires_x.y.z@</code></td><td>cf section X.Y.Z — titre</td><td>Génère une référence croisée vers la section indiquée</td></tr>
<tr><td><code>@cite</code></td><td><code>@cite @dires_x.y.z@</code></td><td>citation section X.Y.Z — titre … texte</td><td>Insère une citation du contenu de la section référencée</td></tr>
<tr><td><code>@/custom</code></td><td><code>@/custom contenu@</code></td><td><strong>Custom :</strong> contenu reformulé</td><td>Annotation personnalisée — reformulation LLM avec le préfixe choisi par l'expert</td></tr>
<tr><td><code>@remplir</code></td><td><code>@remplir_champ texte@</code> (inline)<br/><code>@remplir_bloc : texte@</code> (bloc)</td><td>texte</td><td><strong>Champ</strong> : insertion inline — le texte pré-remplit le champ (si absent, champ vide).<br/><strong>Bloc</strong> : insertion multi-lignes — le texte après <code>:</code> pré-remplit le bloc (si absent, bloc vide). Seul le contenu est conservé dans le PRE.</td></tr>
<tr><td><code>@resume</code></td><td><code>@resume @reference annotation_xxx, @reference annotation_yyy, ...@</code></td><td>Résumé des sections citées</td><td>Concatène les contenus des annotations référencées et génère un résumé via LLM. Résolu au Step 4 <strong>après</strong> la reformulation des annotations citées.</td></tr>
<tr><td><code>@conclusion</code></td><td><code>@conclusion</code> … <code>@</code></td><td>Contenu de la zone conclusion (annotations imbriquées résolues comme ailleurs)</td><td>Pas de paramètres, pas de rendu spécifique propre à cette balise au Step 4 — voir section dédiée ci-dessous</td></tr>
</tbody>
</table>

> **Note** : Toutes les annotations peuvent contenir des placeholders `<<placeholder>>`. La résolution des placeholders se fait **après** toutes les substitutions d'annotations (reformulation, @resume, etc.).

### Principe de fonctionnement

Le TRE est un document unique contenant la structure complète du rapport d'expertise : en-tête administratif, corps du rapport et conclusion. Les placeholders et annotations sont répartis dans l'ensemble du document selon la structure choisie par l'expert.

```
┌─────────────────────────────────────────────────┐
│  TRE (tre.docx)                                  │
│                                                  │
│  Structure complète du rapport d'expertise :     │
│  - placeholders <<...>> pour les métadonnées     │
│  - annotations @type contenu@ pour recevoir      │
│    les informations collectées en entretien      │
│    ou en analyse, et les conclusions             │
│                                                  │
│  Step 2 : validation TRE → prea.docx (PREA)     │
│  Step 3 : consolidation des pièces               │
│  Step E/A : remplissage des annotations          │
│  Step 4 : génération → pre.docx (PRE)            │
└─────────────────────────────────────────────────┘
```

### Flux de traitement au Step 4

```
PREA (prea.docx complété)
    │
    ├─ Passe 1 : validation syntaxique des annotations
    │            et vérification des <<placeholders>> contre placeholders.csv
    │
    ├─ Passe 2 : reformulation LLM des annotations
    │            @dires → "Dires : ..." (reformulé en français professionnel)
    │            @analyse → "Analyse : ..." (reformulé en français professionnel)
    │            @verbatim → "«...»" (préservé tel quel)
    │            @/custom → "Custom : ..." (reformulé)
    │
    ├─ Passe 3 : résolution @resume (après reformulation des annotations citées)
    │            concaténation des sections référencées → résumé LLM
    │
    ├─ Passe 4 : résolution @question n@ et @reference / @cite
    │            (depuis placeholders.csv + contenus déjà reformulés)
    │
    ├─ Passe 5 : substitution des <<placeholders>>
    │            (valeurs depuis placeholders.csv du Step 1)
    │
    ▼
pre.docx (Pré-Rapport d'Expertise)
```

### Conventions d'annotation dans le PREA

L'expert remplit le PREA avec les balises `@type contenu@` en style télégraphique (Step E/A). Le LLM reformule les annotations `@dires` et `@analyse` en style professionnel lors de la génération du pré-rapport (Step 4).

### Exemple d'annotation dans le PREA

```
## Section 4.1.3 : Relations à la fratrie

@dires Le sujet rapporte avoir une sœur aînée avec laquelle
les relations sont distantes depuis l'adolescence. Il évoque des
conflits récurrents liés à l'héritage familial.@

@analyse L'expert note un schéma d'évitement relationnel
avec la fratrie, possiblement lié à un sentiment d'injustice
perçu dans la dynamique familiale.@

@verbatim Ma sœur et moi, on ne se parle plus depuis
que mon père est décédé@
```

### Résultat après traitement (PRE)

```
## 4.1.3 Relations à la fratrie

Dires : Le sujet indique entretenir des relations distantes avec sa sœur
aînée depuis l'adolescence, marquées par des conflits récurrents en lien
avec la succession familiale.

Analyse : L'examen clinique met en évidence un schéma d'évitement
relationnel au sein de la fratrie, vraisemblablement associé à un
sentiment d'injustice perçu dans la dynamique familiale.

« Ma sœur et moi, on ne se parle plus depuis que mon père est décédé »
```

### Annotation `@conclusion`

L'annotation **`@conclusion`** n'a **pas de paramètres** et ne produit **en elle-même rien de spécial** en résolution finale au Step 4 : elle ne déclenche ni reformulation LLM ni substitution dédiée. Son rôle est surtout **structurel** et lié au **mode remplissage assisté** (outil **Éditer PREA** / formulaire) :

- Dans l'éditeur formulaire, `@conclusion` ouvre une **zone de texte multiligne** pour rédiger la conclusion.
- L'outil propose d'**injecter** d'autres annotations — notamment `@reference` et `@cite` — à l'intérieur de cette zone.
- Ces annotations imbriquées (`@question`, `@reference`, `@cite`, etc.) **apparaissent à l'intérieur de `@conclusion`** et sont traitées **normalement** au Step 4 comme si elles étaient placées ailleurs dans le PREA.

**Édition manuelle (Word)** : si l'expert rédige la conclusion directement dans le `prea.docx`, il est **conseillé d'inclure explicitement** les annotations `@reference` et `@cite` (ainsi que `@question` le cas échéant) **à l'intérieur de `@conclusion`**, afin de pouvoir **passer sans friction** du mode édition manuelle au mode assistant d'édition en formulaire (les références et citations restent alors détectables et réutilisables par l'outil d'insertion).

**Syntaxe** : balise ouvrante `@conclusion` (éventuellement suivie de `:` puis d'un contenu initial) et balise fermante `@` sur une ligne dédiée, comme les autres annotations multi-lignes.

### Balises spéciales : @question, @reference et @cite

Ces annotations sont couramment regroupées dans la section conclusion du rapport. Elles peuvent être placées **à l'intérieur de `@conclusion`** ou directement dans le corps du PREA.

```
## 9. CONCLUSION

@conclusion
@question 1@
@reference @dires_4.1.3@
@cite @dires_4.2.1@

@question 2@
@reference @dires_5.1.2@
@
```

- `@question n@` → substitue le texte de la question N° n (depuis `question_n` dans `placeholders.csv`)
- `@reference @dires_x.y.z@` → génère « cf section X.Y.Z — titre de la section »
- `@cite @dires_x.y.z@` → insère « citation section X.Y.Z — titre … texte de la section »

### Annotations personnalisées : @/custom

L'expert peut définir ses propres types d'annotations avec le préfixe `@/` :

```
@/observation Le PEX présente une agitation psychomotrice notable@
@/recommandation Suivi psychothérapeutique hebdomadaire recommandé@
```

Rendu dans le PRE :
```
Observation : Le PEX présente une agitation psychomotrice notable.
Recommandation : Un suivi psychothérapeutique hebdomadaire est recommandé.
```

### Règles d'utilisation

- Les annotations sont ouvrantes (`@type`) et fermantes (`@`)
- Le contenu entre balises est en style télégraphique (l'expert écrit vite, le LLM reformule pour `@dires` et `@analyse`)
- `@verbatim` est préservé mot pour mot entre guillemets — aucune reformulation
- Plusieurs annotations peuvent se succéder dans une même section
- Si une même annotation apparaît plusieurs fois dans une section, les contenus sont concaténés
- L'expert est libre d'ajouter du texte non balisé entre les annotations (il sera ignoré par le parseur)

---

## 8. Placeholders du Template de Rapport (`tre.docx`)

Le fichier TRE contient des champs `<<nom_placeholder>>` qui sont automatiquement substitués lors de la génération du pré-rapport au Step 4.

### Deux sources de placeholders

| Source | Moment d'extraction | Stockage | Type |
|--------|---------------------|----------|------|
| **Demande** (Step 1) | Extraction LLM au Step 1 | `placeholders.csv` | Placeholders de réquisition (standards) + questions (`question_1`…`question_n`) |
| **PREA** (Step 4) | Parsing des annotations `@type contenu@` | En mémoire au Step 4 | Contenu des annotations (reformulé ou préservé selon le type) |

- Les **placeholders de réquisition** sont **standards** (communs à tous les domaines).
- Les **questions** sont numérotées `question_1` à `question_n` dans `placeholders.csv` et listées dans `questions.md`.
- Les **annotations** sont interprétées au Step 4 selon leur type (voir section 7).

### 8.1 Placeholders de réquisition (standards)

#### Fichier `placeholders.csv`

- **Format** : CSV séparateur `;` — `nom_placeholder;valeur`
- **Génération** : extrait au Step 1 depuis la demande (LLM)
- **Questions** : stockées comme `question_1;Texte de la question 1`, `question_2;Texte de la question 2`, etc.
- **Validation** : l'expert vérifie et corrige les valeurs
- **Modification** : l'expert peut éditer directement le CSV
- **Utilisation au Step 4** : lu automatiquement pour substitution dans le PREA
- **Archivage** : fichier extrait et modifié conservés dans l'archive ZIP

#### Exemple

```csv
nom_placeholder;valeur
nom_expert;Dr. Martin Dupont
prenom_expert;Martin
titre_expert;Expert judiciaire en psychologie
date_mission;15/03/2025
nom_tribunal;Tribunal judiciaire de Paris
reference_dossier;RG 24/12345
titre_expertise;Expertise psychologique
nom_pex;Jean Durand
prenom_pex;Jean
requerant_nom;Marie Lambert
requerant_prenom;Marie
objet_mission;Évaluation du préjudice psychologique
nom_magistrat;Mme la Juge Lefèvre
question_1;Décrire l'état psychologique actuel du PEX
question_2;Évaluer le retentissement psychologique des faits
question_3;Déterminer si un suivi thérapeutique est nécessaire
```

#### Liste des placeholders du TRE

<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<thead>
<tr style="background-color: #f0f0f0;">
  <th>Placeholder</th><th>Description</th><th>Source d'extraction</th>
</tr>
</thead>
<tbody>
<tr><td colspan="3" style="background-color: #e8f5e9; font-weight: bold;">Expertise</td></tr>
<tr><td><code>&lt;&lt;titre_expertise&gt;&gt;</code></td><td>Intitulé de l'expertise (ex: « Expertise psychologique »)</td><td>Demande</td></tr>
<tr><td><code>&lt;&lt;objet_mission&gt;&gt;</code></td><td>Objet de la mission d'expertise</td><td>Demande</td></tr>
<tr><td><code>&lt;&lt;date_mission&gt;&gt;</code></td><td>Date de la mission d'expertise</td><td>Demande</td></tr>
<tr><td><code>&lt;&lt;pieces_auxiliaires&gt;&gt;</code></td><td>Liste des pièces consultées par l'expert</td><td>Demande / Expert</td></tr>
<tr><td><code>&lt;&lt;reference_dossier&gt;&gt;</code></td><td>Numéro de référence du dossier (RG)</td><td>Demande</td></tr>
<tr><td colspan="3" style="background-color: #e8f5e9; font-weight: bold;">Requérant / Magistrat</td></tr>
<tr><td><code>&lt;&lt;requerant_prenom&gt;&gt;</code></td><td>Prénom du requérant</td><td>Demande</td></tr>
<tr><td><code>&lt;&lt;requerant_nom&gt;&gt;</code></td><td>Nom du requérant</td><td>Demande</td></tr>
<tr><td><code>&lt;&lt;requerant_titre&gt;&gt;</code></td><td>Titre/qualité du requérant (ex: Substitut du procureur)</td><td>Demande</td></tr>
<tr><td><code>&lt;&lt;requerant_ville&gt;&gt;</code></td><td>Ville du requérant</td><td>Demande</td></tr>
<tr><td><code>&lt;&lt;nom_tribunal&gt;&gt;</code></td><td>Nom complet du tribunal</td><td>Demande</td></tr>
<tr><td><code>&lt;&lt;ville_tribunal&gt;&gt;</code></td><td>Ville du tribunal</td><td>Demande</td></tr>
<tr><td><code>&lt;&lt;nom_magistrat&gt;&gt;</code></td><td>Nom du magistrat ayant ordonné l'expertise</td><td>Demande</td></tr>
<tr><td colspan="3" style="background-color: #e8f5e9; font-weight: bold;">Questions du tribunal</td></tr>
<tr><td><code>&lt;&lt;question_1&gt;&gt;</code> … <code>&lt;&lt;question_n&gt;&gt;</code></td><td>Questions du tribunal (numérotées)</td><td>Demande (extraction LLM)</td></tr>
<tr><td colspan="3" style="background-color: #e8f5e9; font-weight: bold;">Personne expertisée (PEX)</td></tr>
<tr><td><code>&lt;&lt;genre_pex&gt;&gt;</code></td><td>Genre de la personne expertisée (Monsieur ou Madame)</td><td>Demande</td></tr>
<tr><td><code>&lt;&lt;nom_pex&gt;&gt;</code></td><td>Nom de la personne expertisée</td><td>Demande</td></tr>
<tr><td><code>&lt;&lt;prenom_pex&gt;&gt;</code></td><td>Prénom de la personne expertisée</td><td>Demande</td></tr>
<tr><td><code>&lt;&lt;age_pex&gt;&gt;</code></td><td>Âge de la personne expertisée</td><td>Demande (calculé)</td></tr>
<tr><td><code>&lt;&lt;date_naissance_pex&gt;&gt;</code></td><td>Date de naissance de la personne expertisée</td><td>Demande</td></tr>
<tr><td><code>&lt;&lt;ville_naissance_pex&gt;&gt;</code></td><td>Ville de naissance de la personne expertisée</td><td>Demande</td></tr>
<tr><td><code>&lt;&lt;CP_ville_naissance_pex&gt;&gt;</code></td><td>Code postal de la ville de naissance</td><td>Demande</td></tr>
<tr><td colspan="3" style="background-color: #e8f5e9; font-weight: bold;">Expert</td></tr>
<tr><td><code>&lt;&lt;genre_expert&gt;&gt;</code></td><td>Genre de l'expert (Monsieur ou Madame)</td><td>Configuration locale</td></tr>
<tr><td><code>&lt;&lt;nom_expert&gt;&gt;</code></td><td>Nom de famille de l'expert</td><td>Configuration locale</td></tr>
<tr><td><code>&lt;&lt;prenom_expert&gt;&gt;</code></td><td>Prénom de l'expert</td><td>Configuration locale</td></tr>
<tr><td><code>&lt;&lt;titre_expert&gt;&gt;</code></td><td>Titre professionnel de l'expert</td><td>Configuration locale</td></tr>
<tr><td><code>&lt;&lt;date_rapport&gt;&gt;</code></td><td>Date de rédaction du rapport</td><td>Automatique (date du Step 4)</td></tr>
</tbody>
</table>

> **Note** : Le terme **PEX** (Personne Expertisée) remplace l'ancien terme MEC (Mis en Cause) pour couvrir les cas où la personne expertisée est le plaignant et non le mis en cause.

> **Note** : cette liste est extensible. L'expert peut ajouter des placeholders personnalisés dans son TRE et renseigner les valeurs correspondantes dans le CSV.
