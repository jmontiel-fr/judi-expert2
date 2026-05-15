# Glossaire & Workflow — Judi-Expert

Ce document centralise les termes, acronymes et concepts du projet, ainsi que le workflow fonctionnel complet de l'expertise judiciaire assistée par IA.

> Voir aussi : [Architecture](architecture.md) · [Guide utilisateur](user-guide.md) · [Méthodologie](methodologie.md) · [Développement](developpement.md)

---

## 1. Workflow fonctionnel

### Vue d'ensemble

L'expert judiciaire utilise Judi-Expert pour produire un rapport d'expertise en 5 étapes séquentielles (plus une étape intermédiaire E/A réalisée par l'expert hors application). Chaque étape doit être validée avant de passer à la suivante. Une étape validée est verrouillée et ne peut plus être modifiée.

Le **TRE** (Template de Rapport d'Expertise) est le **document central** du workflow. Il contient deux types de méta-instructions :
- **Placeholders** : `<<nom>>` — champs substitués par des valeurs extraites ou saisies
- **Annotations** : `@type contenu@` — instructions de génération interprétées par le moteur

Le workflow supporte deux modes d'expertise :
- **Mode Entretien** : expertise basée sur des entretiens avec les parties (TPE → PE → PEA)
- **Mode Analyse** : expertise basée sur l'analyse documentaire des pièces (TPA → PA → PAA)

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
  <th style="width: 16%; background-color: #e8f5e9; text-align: center;">Step 2<br/><small>Extraction PE depuis TRE</small></th>
  <th style="width: 16%; background-color: #fff8e1; text-align: center;">Step E/A<br/><small>Entretien ou Analyse</small></th>
  <th style="width: 16%; background-color: #e8f5e9; text-align: center;">Step 3<br/><small>Consolidation doc.</small></th>
  <th style="width: 16%; background-color: #e8f5e9; text-align: center;">Step 4<br/><small>Production pré-rapport</small></th>
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
    <code>placeholders.csv</code>
  </td>
  <td style="vertical-align: top;">
    <strong>Entrée :</strong><br/>
    <code>tre.docx</code><br/>
    <code>placeholders.csv</code><br/><br/>
    <strong>Sortie :</strong><br/>
    <code>pe.docx</code><br/>
    <code>pa.docx</code>
  </td>
  <td style="vertical-align: top; background-color: #fff8e1;">
    <strong>Entrée :</strong><br/>
    <code>pe.docx</code> ou <code>pa.docx</code><br/><br/>
    <strong>Sortie :</strong><br/>
    <code>pea.docx</code> ou <code>paa.docx</code><br/><br/>
    <em>(hors application)</em>
  </td>
  <td style="vertical-align: top;">
    <strong>Entrée :</strong><br/>
    <code>diligence-xxx-piece-yyy.*</code><br/><br/>
    <strong>Sortie :</strong><br/>
    <code>diligence-xxx-piece-yyy.md</code>
  </td>
  <td style="vertical-align: top;">
    <strong>Entrée :</strong><br/>
    <code>pea.docx</code><br/>
    <code>tre.docx</code><br/>
    <code>placeholders.csv</code><br/><br/>
    <strong>Sortie :</strong><br/>
    <code>pre.docx</code><br/>
    <code>dac.docx</code>
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
  <td style="text-align: center;"><em>extraction<br/>mécanique</em></td>
  <td style="text-align: center; background-color: #fff8e1;"><em>—</em></td>
  <td style="text-align: center;"><em>judi-ocr</em></td>
  <td style="text-align: center;"><em>judi-rag<br/>judi-llm</em></td>
  <td style="text-align: center;"><em>judi-llm<br/>S3</em></td>
</tr>
</table>

### Prérequis avant le workflow

1. L'expert s'inscrit sur le **Site Central** et achète un **ticket** via Stripe
2. L'expert installe l'**Application Locale** sur son PC et configure :
   - Son **identifiant** (le mot de passe est celui du Site Central — une connexion Internet est nécessaire pour l'authentification)
   - Son **domaine d'expertise** (psychologie, psychiatrie, etc.)
3. L'expert peut personnaliser :
   - Son **corpus d'expertise** (documents de référence indexés dans la base RAG)
   - Son **TRE** — Template de Rapport d'Expertise (`tre.docx`), document central contenant placeholders `<<...>>` et annotations `@type contenu@`. Le PE/PA est extrait du TRE (section délimitée par `@debut_tpe@`).

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
  <td>Extraire et structurer</td>
  <td><code>demande.md</code>, <code>piece-xxx.md</code>, <code>placeholders.csv</code></td>
</tr>
<tr>
  <td><strong>2</strong></td>
  <td>Extraction PE/PA depuis TRE</td>
  <td><code>tre.docx</code>, <code>demande.md</code>, <code>piece-xxx.md</code></td>
  <td>Extraire le plan depuis le TRE</td>
  <td><strong>Entretien</strong> : <code>pe.md</code>, <code>pe.docx</code><br/><strong>Analyse</strong> : <code>pa.md</code>, <code>pa.docx</code>, <code>diligence-xxx.docx</code></td>
</tr>
<tr style="background-color: #fff8e1;">
  <td><strong>E/A</strong></td>
  <td>Entretien ou Analyse sur pièces</td>
  <td>PE ou PA extrait au Step 2</td>
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
  <td><code>pea.docx</code> ou <code>paa.docx</code>, <code>tre.docx</code>, <code>placeholders.csv</code>, docs Step 3</td>
  <td>Reconstituer le rapport (TRE header + PEA), reformuler les annotations via LLM</td>
  <td><code>pre.docx</code>, <code>dac.docx</code></td>
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
<tr><td><code>piece-xxx.*</code></td><td>—</td><td>Pièce complémentaire (PDF, DOCX ou image)</td></tr>
<tr><td><code>piece-xxx.md</code></td><td>—</td><td>Texte extrait par OCR d'une pièce complémentaire</td></tr>
<tr><td><code>placeholders.csv</code></td><td>—</td><td>Valeurs des placeholders extraites de la demande (Step 1) : questions numérotées <code>question_1</code>…<code>question_n</code> + métadonnées. Utilisé pour les substitutions dans <code>tre.docx</code> (Step 4)</td></tr>
<tr><td><code>tre.docx</code></td><td>TRE</td><td>Template de Rapport d'Expertise — document central contenant placeholders <code>&lt;&lt;...&gt;&gt;</code> et annotations <code>@type contenu@</code>. Inclut le PE/PA après le marqueur <code>@debut_tpe@</code>.</td></tr>
<tr><td><code>pe.md</code></td><td>PE</td><td>Plan d'Entretien extrait du TRE (Mode Entretien)</td></tr>
<tr><td><code>pe.docx</code></td><td>PE</td><td>Plan d'Entretien au format .docx (Mode Entretien)</td></tr>
<tr><td><code>pa.md</code></td><td>PA</td><td>Plan d'Analyse extrait du TRE (Mode Analyse)</td></tr>
<tr><td><code>pa.docx</code></td><td>PA</td><td>Plan d'Analyse au format .docx</td></tr>
<tr><td><code>diligence-xxx.docx</code></td><td>—</td><td>Projet de courrier pour diligences complémentaires</td></tr>
<tr><td><code>diligence-xxx-piece-yyy.*</code></td><td>—</td><td>Pièce reçue en réponse à une diligence</td></tr>
<tr><td><code>diligence-xxx-piece-yyy.md</code></td><td>—</td><td>Texte extrait par OCR d'une pièce de diligence</td></tr>
<tr><td><code>pea.docx</code></td><td>PEA</td><td>Plan d'Entretien Annoté par l'expert (voir section 7)</td></tr>
<tr><td><code>paa.docx</code></td><td>PAA</td><td>Plan d'Analyse Annoté par l'expert (voir section 7)</td></tr>
<tr><td><code>placeholders.csv</code></td><td>—</td><td>Valeurs des placeholders (questions <code>question_1</code>…<code>question_n</code> + métadonnées) extraites au Step 1</td></tr>
<tr><td><code>pre.docx</code></td><td>PRE</td><td>Pré-Rapport d'Expertise généré au Step 4</td></tr>
<tr><td><code>dac.docx</code></td><td>DAC</td><td>Document d'Analyse Contradictoire</td></tr>
<tr><td><code>ref.docx</code></td><td>REF</td><td>Rapport d'Expertise Final — pré-rapport ajusté et validé par l'expert</td></tr>
<tr><td><code>&lt;nom-dossier&gt;.zip</code></td><td>—</td><td>Archive immuable contenant tous les fichiers du dossier</td></tr>
<tr><td><code>&lt;nom-dossier&gt;-timbre.txt</code></td><td>—</td><td>Fichier timbre : métadonnées (date de création, hash SHA-256 du .zip, nom expert, référence dossier). Stocké sur S3 pour horodatage technique.</td></tr>
</tbody>
</table>


### Détail par étape

### Step 1 — Création dossier

<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<tr><td style="width:150px;"><strong>Objectif</strong></td><td>Importer les fichiers du dossier, extraire le texte par OCR, identifier les questions et les valeurs de placeholders</td></tr>
<tr><td><strong>Entrée</strong></td><td><code>demande.pdf</code> + zéro ou plusieurs <code>piece-xxx.pdf/.docx/.img</code></td></tr>
<tr><td><strong>Traitement</strong></td><td>OCR (judi-ocr) → conversion PDF/scan en Markdown. Extraction LLM des questions numérotées (stockées comme <code>question_1</code>…<code>question_n</code>) et des valeurs de placeholders depuis la demande.</td></tr>
<tr><td><strong>Sortie</strong></td><td><code>demande.md</code>, <code>piece-xxx.md</code>, <code>placeholders.csv</code></td></tr>
<tr><td><strong>Stockage</strong></td><td>Entrées dans <code>C:\judi-expert\&lt;nom-dossier&gt;\step1\in</code> · Sorties dans <code>step1\out</code></td></tr>
<tr><td><strong>Rôle expert</strong></td><td>Vérifier le texte extrait, corriger les erreurs OCR, valider les placeholders et questions extraites</td></tr>
<tr><td><strong>Verrouillage</strong></td><td>Validation → passage au Step 2, Step 1 non modifiable</td></tr>
</table>

### Step 2 — Extraction PE/PA depuis le TRE

<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<tr><td style="width:150px;"><strong>Objectif</strong></td><td>Extraire le plan d'entretien (PE) ou le plan d'analyse (PA) depuis le TRE</td></tr>
<tr><td><strong>Entrée</strong></td><td><code>tre.docx</code> + <code>demande.md</code> + <code>piece-xxx.md</code></td></tr>
<tr><td><strong>Traitement</strong></td><td>Extraction mécanique du contenu du TRE depuis le marqueur <code>@debut_tpe@</code> jusqu'à la fin du document. Aucune génération LLM — le PE/PA est directement extrait du TRE. En Mode Analyse, génération de courriers de diligence.</td></tr>
<tr><td><strong>Sortie (Mode Entretien)</strong></td><td><code>pe.md</code>, <code>pe.docx</code></td></tr>
<tr><td><strong>Sortie (Mode Analyse)</strong></td><td><code>pa.md</code>, <code>pa.docx</code>, <code>diligence-xxx.docx</code></td></tr>
<tr><td><strong>Stockage</strong></td><td>Entrées dans <code>C:\judi-expert\&lt;nom-dossier&gt;\step2\in</code> · Sorties dans <code>step2\out</code></td></tr>
<tr><td><strong>Rôle expert</strong></td><td>Télécharger le PE/PA, l'adapter si nécessaire, valider</td></tr>
<tr><td><strong>Verrouillage</strong></td><td>Validation → passage au Step E/A (action expert), Step 2 non modifiable</td></tr>
</table>

### Step E/A — Entretien ou Analyse sur pièces (action expert)

<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
<tr><td style="width:150px;"><strong>Objectif</strong></td><td>L'expert mène ses entretiens (Mode Entretien) ou ses analyses sur pièces (Mode Analyse) et annote le plan extrait</td></tr>
<tr><td><strong>Entrée</strong></td><td>PE (<code>pe.md</code> / <code>pe.docx</code>) en Mode Entretien, ou PA (<code>pa.md</code> / <code>pa.docx</code>) en Mode Analyse</td></tr>
<tr><td><strong>Traitement</strong></td><td>Aucun traitement IA — travail de l'expert hors application</td></tr>
<tr><td><strong>Sortie</strong></td><td><code>pea.docx</code> (Plan d'Entretien Annoté) ou <code>paa.docx</code> (Plan d'Analyse Annoté) avec annotations balisées</td></tr>
<tr><td><strong>Rôle expert</strong></td><td>Mener les entretiens ou analyses, annoter le plan avec les conventions de balisage (@dires, @analyse, @verbatim, @question, @reference, @cite)</td></tr>
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
<tr><td style="width:150px;"><strong>Objectif</strong></td><td>Reconstituer le rapport complet à partir de l'en-tête du TRE et du PEA, puis reformuler les annotations via LLM</td></tr>
<tr><td><strong>Entrée</strong></td><td><code>pea.docx</code> (Mode Entretien) ou <code>paa.docx</code> (Mode Analyse) + <code>tre.docx</code> + <code>placeholders.csv</code> + documents complémentaires Step 3 (si existants)</td></tr>
<tr><td><strong>Traitement</strong></td><td>
1. Reconstitution du rapport complet : en-tête du TRE (avant <code>@debut_tpe@</code>) + contenu du PEA/PAA<br/>
2. Substitution des placeholders <code>&lt;&lt;...&gt;&gt;</code> depuis <code>placeholders.csv</code><br/>
3. Interprétation des annotations <code>@type contenu@</code> : reformulation LLM pour <code>@dires</code> et <code>@analyse</code>, préservation pour <code>@verbatim</code>, résolution des <code>@question</code>, <code>@reference</code> et <code>@cite</code><br/>
4. Génération du PRE et du DAC</td></tr>
<tr><td><strong>Sortie</strong></td><td><code>pre.docx</code> (Pré-Rapport d'Expertise), <code>dac.docx</code> (Document d'Analyse Contradictoire)</td></tr>
<tr><td><strong>Stockage</strong></td><td>Entrées dans <code>C:\judi-expert\&lt;nom-dossier&gt;\step4\in</code> · Sorties dans <code>step4\out</code></td></tr>
<tr><td><strong>Rôle expert</strong></td><td>Relire PRE et DAC, affiner les conclusions, valider</td></tr>
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
4. Stockage du timbre sur S3</td></tr>
<tr><td><strong>Sortie</strong></td><td><code>&lt;nom-dossier&gt;.zip</code> (archive immuable), <code>&lt;nom-dossier&gt;-timbre.txt</code> (horodatage technique + métadonnées)</td></tr>
<tr><td><strong>Stockage</strong></td><td>Entrées dans <code>C:\judi-expert\&lt;nom-dossier&gt;\step5\in</code> · Sorties dans <code>step5\out</code></td></tr>
<tr><td><strong>Rôle expert</strong></td><td>Importer le rapport final ajusté, utiliser le service de révision si souhaité, valider pour archivage définitif. L'expert peut compléter par un horodatage juridiquement certifié (solutions externes proposées dans le manuel utilisateur).</td></tr>
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
  Step 2 (Extraction PE/PA depuis TRE): initial ──► en_cours ──► valide
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
<tr><td>Dossier</td><td>Dossier d'expertise</td><td>Unité de travail regroupant les 5 étapes d'une expertise judiciaire</td></tr>
<tr><td>PEX</td><td>Personne Expertisée</td><td>Personne évaluée en expertise (plaignant ou mis en cause). Sujet de l'expertise désigné par la juridiction. Remplace l'ancien terme MEC (Mis en Cause).</td></tr>
<tr><td>QT</td><td>Questions du Tribunal</td><td>Questions posées par la juridiction auxquelles l'expert doit répondre, extraites de la demande et stockées comme <code>question_1</code>…<code>question_n</code> dans <code>placeholders.csv</code></td></tr>
<tr><td>TPE</td><td>Template de Plan d'Entretien</td><td>Partie du TRE (après <code>@debut_tpe@</code>) définissant la structure des entretiens</td></tr>
<tr><td>TPA</td><td>Template de Plan d'Analyse</td><td>Partie du TRE (après <code>@debut_tpe@</code>) définissant la structure des analyses sur pièces</td></tr>
<tr><td>PE</td><td>Plan d'Entretien</td><td>Document <code>pe.md</code> / <code>pe.docx</code> extrait du TRE au Step 2 (Mode Entretien)</td></tr>
<tr><td>PA</td><td>Plan d'Analyse</td><td>Document <code>pa.md</code> / <code>pa.docx</code> extrait du TRE au Step 2 (Mode Analyse)</td></tr>
<tr><td>PEA</td><td>Plan d'Entretien Annoté</td><td>Document <code>pea.docx</code> — PE annoté par l'expert (voir section 7). Fichier d'entrée du Step 4 en Mode Entretien.</td></tr>
<tr><td>PAA</td><td>Plan d'Analyse Annoté</td><td>Document <code>paa.docx</code> — PA annoté par l'expert (voir section 7). Fichier d'entrée du Step 4 en Mode Analyse.</td></tr>
<tr><td>TRE</td><td>Template de Rapport d'Expertise</td><td>Fichier <code>tre.docx</code> — document central du workflow. Contient des placeholders <code>&lt;&lt;...&gt;&gt;</code> et des annotations <code>@type contenu@</code>. Inclut le TPE/TPA après le marqueur <code>@debut_tpe@</code>.</td></tr>
<tr><td>PRE</td><td>Pré-Rapport d'Expertise</td><td>Document <code>pre.docx</code> généré au Step 4 par reconstitution TRE header + PEA et reformulation des annotations</td></tr>
<tr><td>DAC</td><td>Document d'Analyse Contradictoire</td><td>Document <code>dac.docx</code> généré au Step 4</td></tr>
<tr><td>REF</td><td>Rapport d'Expertise Final</td><td>Document <code>ref.docx</code> — pré-rapport ajusté, importé au Step 5</td></tr>
<tr><td>Réquisition</td><td>Demande d'expertise</td><td>Document officiel (<code>demande.pdf</code>) — ordonnance ou réquisition du tribunal</td></tr>
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

## 7. Méta-instructions du TRE et conventions d'annotation

Le TRE (Template de Rapport d'Expertise) est le document central du workflow. Il contient deux types de méta-instructions qui pilotent la génération du rapport :

### 7.1 Placeholders `<<nom>>`

Les placeholders sont des champs de substitution directe. Ils sont remplacés par des valeurs issues de `placeholders.csv` (Step 1) ou saisies manuellement par l'expert.

**Syntaxe** : `<<nom_placeholder>>`

**Exemples** : `<<tribunal>>`, `<<magistrat>>`, `<<question_1>>`, `<<nom_mec>>`

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
<tr><td><code>@debut_tpe</code></td><td><code>@debut_tpe@</code></td><td>—</td><td>Marqueur structurel : début de la zone PE/PA (extraction au Step 2)</td></tr>
<tr><td><code>@/custom</code></td><td><code>@/custom contenu@</code></td><td><strong>Custom :</strong> contenu reformulé</td><td>Annotation personnalisée — reformulation LLM avec le préfixe choisi par l'expert</td></tr>
<tr><td><code>@remplir</code></td><td><code>@remplir description : texte@</code></td><td>texte (partie après le <code>:</code>)</td><td>Texte à substituer au Step 4. Seule la partie après le <code>:</code> est conservée dans le PRE — la description avant le <code>:</code> sert d'indication à l'expert.</td></tr>
<tr><td><code>@resume</code></td><td><code>@resume @reference annotation_xxx, @reference annotation_yyy, ...@</code></td><td>Résumé des sections citées</td><td>Concatène les contenus des annotations référencées et génère un résumé via LLM. Résolu au Step 4 <strong>après</strong> la reformulation des annotations citées.</td></tr>
</tbody>
</table>

> **Note** : Toutes les annotations peuvent contenir des placeholders `<<placeholder>>`. La résolution des placeholders se fait **après** toutes les substitutions d'annotations (reformulation, @resume, etc.).

### Principe de fonctionnement

Le TRE se divise en deux zones séparées par le marqueur `@debut_tpe@` :

```
┌─────────────────────────────────────────────────┐
│  EN-TÊTE DU TRE (avant @debut_tpe@)            │
│                                                  │
│  Contient : placeholders <<...>> + annotations   │
│  @type contenu@ pour la partie administrative    │
│  et structurelle du rapport                      │
├──────────────────────────────────────────────────┤
│  @debut_tpe@                                     │
├──────────────────────────────────────────────────┤
│  CORPS TPE/TPA (après @debut_tpe@)              │
│                                                  │
│  Contient : la trame d'entretien ou d'analyse    │
│  avec annotations @type contenu@ pour guider     │
│  l'expert dans ses observations                  │
│  → Extrait au Step 2 pour produire le PE/PA      │
└─────────────────────────────────────────────────┘
```

### Flux de traitement au Step 4

```
TRE (en-tête, avant @debut_tpe@)
    │
    ├─ Reconstitution : en-tête TRE + contenu PEA/PAA
    │
    ▼
Document reconstitué complet
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
    │            Note : les placeholders dans les annotations sont résolus ici
    │
    ▼
pre.docx (Pré-Rapport d'Expertise)
```

### Conventions d'annotation dans le PEA/PAA

L'expert annote le PE/PA avec les balises `@type contenu@` en style télégraphique. Le LLM reformule les annotations `@dires` et `@analyse` en style professionnel lors de la génération du pré-rapport.

### Exemple d'annotation dans le PEA

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

### Balises spéciales : @question, @reference et @cite

```
## 9. CONCLUSION

@question 1@
@reference @dires_4.1.3@
@cite @dires_4.2.1@

@question 2@
@reference @dires_5.1.2@
```

- `@question n@` → substitue le texte de la question N° n (depuis `question_n` dans `placeholders.csv`)
- `@reference @dires_x.y.z@` → génère « cf section X.Y.Z — titre de la section »
- `@cite @dires_x.y.z@` → insère « citation section X.Y.Z — titre … texte de la section »

### Annotations personnalisées : @/custom

L'expert peut définir ses propres types d'annotations avec le préfixe `@/` :

```
@/observation Le MEC présente une agitation psychomotrice notable@
@/recommandation Suivi psychothérapeutique hebdomadaire recommandé@
```

Rendu dans le PRE :
```
Observation : Le MEC présente une agitation psychomotrice notable.
Recommandation : Un suivi psychothérapeutique hebdomadaire est recommandé.
```

### Règles d'utilisation

- Les annotations sont ouvrantes (`@type`) et fermantes (`@`)
- Le contenu entre balises est en style télégraphique (l'expert écrit vite, le LLM reformule pour `@dires` et `@analyse`)
- `@verbatim` est préservé mot pour mot entre guillemets — aucune reformulation
- Plusieurs annotations peuvent se succéder dans une même section
- Si une même annotation apparaît plusieurs fois dans une section, les contenus sont concaténés
- L'expert est libre d'ajouter du texte non balisé entre les annotations (il sera ignoré par le parseur)
- Le marqueur `@debut_tpe@` ne doit apparaître qu'une seule fois dans le TRE

---

## 8. Placeholders du Template de Rapport (`tre.docx`)

Le fichier `tre.docx` (Template de Rapport d'Expertise) contient des champs `<<nom_placeholder>>` qui sont automatiquement substitués lors de la génération du pré-rapport au Step 4.

### Deux sources de placeholders

| Source | Moment d'extraction | Stockage | Type |
|--------|---------------------|----------|------|
| **Demande** (Step 1) | Extraction LLM au Step 1 | `placeholders.csv` | Placeholders de réquisition (standards) + questions (`question_1`…`question_n`) |
| **PEA/PAA** (Step 4) | Parsing des annotations `@type contenu@` | En mémoire au Step 4 | Contenu des annotations (reformulé ou préservé selon le type) |

- Les **placeholders de réquisition** sont **standards** (communs à tous les domaines).
- Les **questions** sont numérotées `question_1` à `question_n` dans `placeholders.csv`.
- Les **annotations** sont interprétées au Step 4 selon leur type (voir section 7).

### 8.1 Placeholders de réquisition (standards)

#### Fichier `placeholders.csv`

- **Format** : CSV séparateur `;` — `nom_placeholder;valeur`
- **Génération** : extrait au Step 1 depuis la demande (LLM)
- **Questions** : stockées comme `question_1;Texte de la question 1`, `question_2;Texte de la question 2`, etc.
- **Validation** : l'expert vérifie et corrige les valeurs
- **Modification** : l'expert peut éditer directement le CSV
- **Utilisation au Step 4** : lu automatiquement pour substitution dans le TRE
- **Archivage** : fichier extrait et modifié conservés dans l'archive ZIP

#### Exemple

```csv
nom_placeholder;valeur
nom_expert;Dr. Martin Dupont
prenom_expert;Martin
titre_expert;Expert judiciaire en psychologie
date_mission;15/03/2025
tribunal;Tribunal judiciaire de Paris
reference_dossier;RG 24/12345
nom_expertise;Expertise psychologique
nom_mec;Jean Durand
prenom_mec;Jean
nom_requerant;Marie Lambert
prenom_requerant;Marie
objet_mission;Évaluation du préjudice psychologique
date_ordonnance;10/02/2025
juridiction;Tribunal judiciaire
ville_juridiction;Paris
magistrat;Mme la Juge Lefèvre
question_1;Décrire l'état psychologique actuel du MEC
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

> **Note** : cette liste est extensible. L'expert peut ajouter des placeholders personnalisés dans son `tre.docx` et renseigner les valeurs correspondantes dans le CSV.
