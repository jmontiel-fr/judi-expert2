# Guide de l'Expert — Judi-Expert

## Sommaire

1. Processus méthodologique
2. Installation et démarrage
3. Configuration avant utilisation
4. Utilisation de l'application
5. Le TRE (Template de Rapport d'Expertise)
6. Structure des fichiers sur votre PC
7. Bonnes pratiques
8. Sécurité et confidentialité

---

## 1. Processus méthodologique

### Ce que l'outil apporte

Judi-Expert assiste l'expert judiciaire à travers **deux workflows** complémentaires :

**Workflow Standard (5 étapes)** — Pour une expertise complète assistée de bout en bout :
- Extraction automatique du contenu de l'ordonnance (OCR + structuration)
- Identification des questions du tribunal et des informations de contexte (placeholders)
- Production d'un document de travail annoté (PREA) à partir de votre template de rapport (TRE)
- Reformulation professionnelle de vos notes d'entretien (style télégraphique → style rapport)
- Analyse contradictoire optionnelle (DAC) pour anticiper les contestations
- Archivage sécurisé avec horodatage technique

**Workflow Simple (2 étapes)** — Pour un rapport déjà rédigé :
- L'outil sert à remettre en forme textuelle le rapport d'expertise final (correction linguistique : orthographe, grammaire, syntaxe)
- Les outils de mise en forme ou de résumé (menu Outils) peuvent être utilisés en amont pour préparer le rapport soumis pour ajustement final

### Opérations préliminaires

**Pour le workflow standard**, avant de créer un dossier, l'expert doit :

1. **Configurer l'application** (section 3 ci-dessous) : domaine, corpus RAG, profil matériel
2. **Préparer son TRE** à partir du fichier `TRE_template.docx` :
   - Mise en forme Word (titres, styles, structure du rapport)
   - Organisation des sections dans l'ordre souhaité
   - Insertion des annotations (`@dires`, `@analyse`, `@verbatim`, etc.) aux emplacements prévus pour l'entretien
   - Insertion des placeholders `<<...>>` aux emplacements d'informations factuelles
   - Voir la section 5 (Le TRE) pour le mode d'emploi complet des annotations

**Pour le workflow simple** : aucune préparation spécifique — il suffit de disposer d'un PRE (`pre.docx`) déjà rédigé.

### Vue d'ensemble du workflow standard

Le processus d'expertise assisté couvre l'intégralité du parcours, depuis la réception de la demande (ordonnance ou réquisition) jusqu'à la remise du rapport final et de son annexe méthodologique au greffe.

```
Réception ordonnance/réquisition
        │
        ▼
┌─── STEP 1 ─── Extraction & structuration ──────────────────────┐
│  • OCR du PDF scanné                                            │
│  • Structuration en Markdown                                    │
│  • Extraction des questions du tribunal (Q1…Qn)                 │
│  • Extraction des placeholders (noms, dates, références)        │
│  → Vérification et validation par l'expert                      │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─── STEP 2 ─── Validation TRE → PREA ───────────────────────────┐
│  • Vérification syntaxique du TRE (template de rapport)         │
│  • Cohérence placeholders TRE ↔ placeholders.csv                │
│  • Production du PREA (copie validée du TRE)                    │
│  → Validation par l'expert                                      │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─── STEP 3 ─── Consolidation documentaire ───────────────────────┐
│  • Import des pièces de diligence reçues                        │
│  • OCR et extraction en Markdown                                │
│  → Vérification par l'expert                                    │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─── STEP E/A ─── Entretien ou Analyse (HORS APPLICATION) ───────┐
│  • L'expert mène ses entretiens / analyses sur pièces           │
│  • Remplissage des annotations du PREA :                        │
│    @dires, @analyse, @verbatim, @question, @reference           │
│  • En style télégraphique (Word ou outil d'édition PREA)        │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─── STEP 4 ─── Production du pré-rapport ────────────────────────┐
│  • Reformulation LLM des @dires et @analyse                     │
│  • Préservation intacte des @verbatim                           │
│  • Substitution des placeholders <<...>>                        │
│  • Génération du PRE (pre.docx)                                 │
│  • Optionnel : DAC (Document d'Analyse Contradictoire)          │
│  → Relecture et ajustement par l'expert                         │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
   L'expert ajuste le PRE hors application → REF (rapport final)
        │
        ▼
┌─── STEP 5 ─── Finalisation et archivage ────────────────────────┐
│  • Import du REF (ref.docx)                                     │
│  • Révision linguistique (optionnel)                            │
│  • Archive ZIP + timbre SHA-256                                 │
│  → Clôture du dossier                                           │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
  Remise du rapport (REF) + annexe méthodologique au greffe
```

### Annexe méthodologique

L'expert remet au tribunal le rapport final (REF) accompagné de l'annexe méthodologique justifiant :
- L'utilisation de Judi-Expert comme outil d'assistance (pas de substitution)
- Le respect de la supervision humaine à chaque étape
- La conformité RGPD et AI Act
- L'exécution 100% locale de l'IA (aucune fuite de données)

### Workflow simple (alternative)

Si l'expert a déjà rédigé son PRE en dehors de l'application :

| Étape | Nom | Description |
|-------|-----|-------------|
| Step 1 | Mise en forme linguistique | Import PRE → révision IA → PREF + DAC optionnel |
| Step 2 | Archivage | Archive ZIP + timbre SHA-256, clôture |

---

## 2. Installation et démarrage

### Prérequis matériels

| Composant | Minimum | Recommandé |
|-----------|---------|-----------|
| CPU | Intel i5 (10e gén) ou AMD Ryzen 5 | Intel i7/i9 (12e gén+) ou Ryzen 7/9 |
| RAM | 16 Go | 32 Go |
| Disque | SSD 256 Go (50 Go libres) | SSD NVMe 512 Go+ |
| GPU | Non requis | NVIDIA RTX 3060+ (12 Go VRAM) |
| OS | Windows 11 Pro | Windows 11 Pro |
| Chiffrement | BitLocker activé (obligatoire) | — |

### Ce que fait l'installateur

L'installateur (`judi-expert-client-x.y.z.exe`) effectue automatiquement :

1. Vérifie les prérequis (RAM, disque, chiffrement, Docker)
2. Installe Docker Desktop si absent
3. Crée le répertoire `C:\judi-expert\`
4. Déploie les images Docker (backend, frontend, OCR, LLM, RAG)
5. Télécharge le modèle LLM adapté à votre matériel
6. Configure l'environnement (ports, volumes, paramètres)
7. Crée un **raccourci bureau** Judi-Expert

### Démarrage de l'application

1. Double-cliquez sur le raccourci **Judi-Expert** sur votre bureau
2. L'Amorce démarre Docker Desktop si nécessaire
3. Les 5 conteneurs démarrent (frontend, backend, OCR, LLM, RAG)
4. Votre navigateur s'ouvre automatiquement
5. Connectez-vous avec vos identifiants du Site Central

### Arrêt de l'application

Double-cliquez à nouveau sur l'Amorce, ou fermez Docker Desktop. Vos données sont persistées.

---

## 3. Configuration avant utilisation

Avant de créer votre premier dossier, configurez l'application depuis le menu **Configuration**.

### 3.1 Domaine d'expertise

Sélectionnez votre domaine (psychologie, psychiatrie, médecine légale, bâtiment, comptabilité). Le domaine détermine :
- Le corpus RAG utilisé par l'IA
- Le TRE par défaut proposé
- Les prompts adaptés au domaine

### 3.2 Module RAG (base de connaissances)

Le module RAG contient la base de connaissances spécialisée de votre domaine. Son installation est **obligatoire**.

1. Dans **Configuration**, section **Corpus RAG**
2. Consultez les versions disponibles
3. Cliquez sur **Installer** (téléchargement depuis le Site Central)
4. Attendez la fin de l'indexation

Le corpus contient des documents de référence publics : guides méthodologiques, textes réglementaires, référentiels de bonnes pratiques.

Vous pouvez ajouter vos propres documents au corpus (bouton **Ajouter un document**) ou supprimer des documents personnalisés.

### 3.3 Options matérielles (profil de performance)

L'application détecte automatiquement votre matériel et sélectionne le profil adapté :

| Profil | RAM | Modèle LLM | Vitesse estimée |
|--------|-----|------------|-----------------|
| Haute performance | ≥ 32 Go | Mistral 7B (q4_0) | 2-5 min/étape |
| Standard | 16-32 Go | Mistral 7B (q3_K_M) | 3-7 min/étape |
| Économique | 8-16 Go | Qwen 2.5 3B (q4_0) | 5-10 min/étape |
| Minimal | < 8 Go | Qwen 2.5 1.5B (q4_0) | 8-15 min/étape |

Vous pouvez forcer un profil différent dans **Configuration > Performance**, mais un profil supérieur à votre RAM peut provoquer des ralentissements.

Si une carte GPU NVIDIA est détectée, l'accélération GPU est activée automatiquement (temps divisé par 10 à 20).

### 3.4 Personnalisation du TRE (Template de Rapport)

Le TRE (`tre.docx`) est le squelette de votre rapport d'expertise. Pour importer le vôtre :

1. Dans **Configuration**, section **TRE / Template rapport**
2. Cliquez sur **Importer**
3. Sélectionnez votre fichier `.docx`

Si vous n'importez pas de TRE personnalisé, le TRE par défaut de votre domaine est utilisé.

Voir la section 5 ci-dessous pour le détail du format TRE.

### 3.5 Limites mémoire Docker (avancé)

Pour les PC avec moins de 32 Go de RAM, vous pouvez ajuster les limites mémoire dans **Configuration > Mémoire** :
- LLM : 8 Go par défaut
- RAG : 1 Go
- Backend/Frontend/OCR : 512 Mo chacun

---

## 4. Utilisation de l'application

### 4.1 Créer un dossier

**Prérequis** : un ticket d'expertise valide (acheté sur judi-expert.fr) et le module RAG installé.

1. Page d'accueil → **Nouveau dossier**
2. Saisissez le **nom du dossier** (ex : « Expertise Dupont — TGI Paris »)
3. Collez le **token du ticket** (reçu par email)
4. Choisissez le workflow : **Standard** ou **Simple**
5. **Créer** — le ticket est vérifié en ligne

### 4.2 Workflow standard — détail des étapes

**Step 1 — Création dossier (OCR + extraction)**

1. Importez le PDF de l'ordonnance (≥ 300 dpi recommandé)
2. Optionnel : ajoutez des pièces complémentaires
3. Cliquez sur **Extraire et structurer**
4. Vérifiez : `demande.md`, `placeholders.csv`, `questions.md`
5. **Validez**

**Step 2 — Validation TRE → PREA**

1. Le TRE est résolu (config ou upload dans le dossier)
2. Cliquez sur **Valider le TRE**
3. Vérifiez le `prea.docx` en sortie
4. **Validez**

**Step 3 — Consolidation documentaire**

1. Importez les pièces de diligence reçues
2. Cliquez sur **Extraire les documents**
3. Vérifiez les extractions OCR
4. **Validez** (ou **Sans objet**)

**Step E/A — Entretien ou Analyse (hors application)**

Après le Step 3, travaillez hors application :
- Menez vos entretiens ou analyses sur pièces
- Remplissez les annotations du PREA (`@dires`, `@analyse`, `@verbatim`)
- Style télégraphique autorisé (le LLM reformulera au Step 4)

**Step 4 — Production du pré-rapport**

1. Importez le PREA complété (`pea.docx`)
2. Cliquez sur **Générer le PRE**
3. Relisez le `pre.docx`
4. Optionnel : **Générer le DAC**
5. **Validez**

**Step 5 — Finalisation et archivage**

1. Ajustez le PRE hors application → REF
2. Importez le REF (`ref.docx`)
3. Archive ZIP + timbre SHA-256
4. **Validez** puis **Clore le dossier**

### 4.3 Workflow simple

**Step 1 — Mise en forme linguistique**

1. Importez votre `pre.docx`
2. Cliquez sur **Mettre en forme linguistique**
3. Consultez le `pref.docx` généré
4. Optionnel : **Générer le DAC**
5. Relance possible — **Validez**

**Step 2 — Archivage**

1. Le PREF est utilisé par défaut
2. **Archiver le dossier** → ZIP + timbre
3. **Validez** puis **Clore le dossier**

### 4.4 Gestion des dossiers

- **Progression** : pastilles de statut par étape (initial, en cours, fait, validé)
- **Reset** d'une étape ou reset complet (dossier actif uniquement)
- **Clore le dossier** quand toutes les étapes sont validées
- **Télécharger l'archive** une fois le dossier clos

### 4.5 ChatBot

L'assistant conversationnel est accessible depuis le menu :
- Réponses basées sur le corpus de votre domaine
- Questions sur l'utilisation de l'application
- LLM local — aucune donnée transmise à l'extérieur

---

## 5. Le TRE (Template de Rapport d'Expertise)

### Qu'est-ce que le TRE ?

Le TRE est un fichier **Word (.docx)** qui constitue votre trame de rapport d'expertise. C'est un document Word classique enrichi d'**annotations** (balises `@type ... @`) et de **placeholders** (`<<nom>>`) aux endroits où l'IA doit intervenir.

Le TRE conserve intégralement sa mise en forme Word : titres, styles, numérotation, table des matières, en-têtes/pieds de page.

### Cycle de vie du TRE

```
TRE (votre template)
  ↓ Step 2 : validation syntaxique
PREA (copie de travail)
  ↓ Step E/A : annotation par l'expert
PREA annoté
  ↓ Step 4 : traitement IA
PRE (Pré-Rapport d'Expertise)
  ↓ Relecture et ajustements
REF (Rapport d'Expertise Final)
```

### Types d'annotations

| Annotation | Format | Rôle |
|-----------|--------|------|
| `@dires section_x.x_suffixe ... @` | Bloc | Propos rapportés. Reformulés en style professionnel. |
| `@analyse section_x.x_suffixe ... @` | Bloc | Observations cliniques. Reformulées en style rapport. |
| `@verbatim "citation" @` | Inline | Citation textuelle exacte. Jamais modifiée. |
| `@remplir_champ nom : contenu @` | Inline | Champ court (date, lieu). |
| `@remplir_bloc contenu @` | Bloc | Zone de texte libre multiligne. |
| `@conclusion ... @` | Bloc | Bloc de conclusion avec injection de références. |
| `@question N @` | Inline | Insère la réponse à la question N. |
| `@reference section_x.x @` | Inline | Référence aux dires/analyse d'une section. |
| `@cite section_x.x @` | Inline | Citation des dires d'une section. |
| `@resume section_x.x, section_y.y @` | Bloc | Résumé IA de plusieurs sections. |
| `@date_naissance_pex JJ/MM/AAAA @` | Inline | Date de naissance (calcul @age@). |
| `@age@` | Inline | Calcul automatique de l'âge. |

### Placeholders `<<nom>>`

| Placeholder | Signification |
|------------|---------------|
| `<<nom_pex>>` | Nom de la personne expertisée |
| `<<prenom_pex>>` | Prénom |
| `<<genre_pex>>` | Monsieur / Madame |
| `<<date_naissance_pex>>` | Date de naissance |
| `<<nom_expert>>` | Nom de l'expert |
| `<<prenom_expert>>` | Prénom de l'expert |
| `<<titre_expert>>` | Titre professionnel |
| `<<nom_tribunal>>` | Juridiction émettrice |
| `<<ville_tribunal>>` | Ville du tribunal |
| `<<date_mission>>` | Date de la réquisition |
| `<<reference_dossier>>` | Numéro de dossier |
| `<<requerant_nom>>` | Nom du requérant |
| `<<objet_mission>>` | Chapeau introductif de la mission |

### Construction du TRE

**Méthode 1 — Éditeur PEA (assistant visuel)**

Menu Outils > Éditer PEA. Permet de charger un .docx, visualiser la structure, insérer des annotations via une palette visuelle sans taper la syntaxe.

**Méthode 2 — Édition manuelle dans Word**

Créez votre structure, tapez les balises `@type ... @` et les `<<placeholders>>` directement. Règles :
- Annotations bloc : une par paragraphe
- Le `@` ouvrant en début de paragraphe, le `@` fermant en fin
- Annotations inline (`@remplir_champ`, `@verbatim`) : au milieu du texte

### Structure type d'un TRE

```
1. Identification et cadre de mission
   <<genre_pex>> <<prenom_pex>> <<nom_pex>>, né(e) le
   <<date_naissance_pex>> à <<ville_naissance_pex>>
   @remplir_champ date_entretien : JJ/MM/AAAA@

2. Anamnèse
   2.1 Famille d'origine
       @dires section_2.1_famille@
       @analyse section_2.1_famille@
   2.2 Parcours scolaire
       @dires section_2.2_scolarite@
       @analyse section_2.2_scolarite@

3. Examen clinique
   3.1.1 Relation au père
       @dires section_3.1.1_pere@
       @analyse section_3.1.1_pere@

4. Conclusions
   @conclusion@
```

---

## 6. Structure des fichiers sur votre PC

Tous vos fichiers sont dans `C:\judi-expert\` :

```
C:\judi-expert\
│
├── judi-expert.db                      ← base de données (métadonnées)
│
├── config\                             ← configuration
│   ├── .env                            ← paramètres
│   ├── docker-compose.yml              ← orchestration conteneurs
│   ├── TPE_psychologie.docx            ← Trame Plan d'Entretien
│   ├── template_psychologie.docx       ← TRE par défaut
│   └── corpus_cache\                   ← documents RAG
│
├── Expertise Dupont 2026\              ← un dossier d'expertise
│   ├── step1\
│   │   ├── in\       ← PDF ordonnance
│   │   └── out\      ← demande.md, placeholders.csv, questions.md
│   ├── step2\
│   │   ├── in\       ← TRE sélectionné
│   │   └── out\      ← prea.docx
│   ├── step3\
│   │   ├── in\       ← pièces de diligence
│   │   └── out\      ← extractions Markdown
│   ├── step4\
│   │   ├── in\       ← PREA complété (pea.docx)
│   │   └── out\      ← pre.docx, dac.docx
│   ├── step5\
│   │   ├── in\       ← REF (ref.docx)
│   │   └── out\      ← archive ZIP + timbre
│   └── archive\
│
├── docker-images\                      ← images Docker
├── scripts\                            ← scripts (amorce)
└── uninstall.exe                       ← désinstalleur
```

Ce répertoire est protégé par le chiffrement de votre disque (BitLocker). Ne supprimez pas manuellement les fichiers.

---

## 7. Bonnes pratiques

1. **Scanner en haute résolution** (≥ 300 dpi) pour une meilleure OCR
2. **Toujours vérifier** les extractions OCR et les questions identifiées
3. **Encadrer les citations** entre guillemets dans le PREA (protection verbatim)
4. **Compléter toutes les annotations** avant de lancer le Step 4
5. **Relire le PRE** systématiquement — l'IA assiste mais l'expert reste maître
6. **Utiliser le DAC** pour anticiper les contestations possibles
7. **Tester son TRE** avec l'éditeur PEA pour détecter les erreurs de syntaxe
8. **Nommer les sections** de façon parlante (ex: `section_3.1.1_pere`)

---

## 8. Sécurité et confidentialité

- **Données locales** : toutes les données d'expertise restent sur votre PC
- **IA locale** : le LLM tourne en local, aucune donnée transmise à l'extérieur
- **Chiffrement** : BitLocker / FileVault obligatoire
- **Transit minimal** : seuls les tokens de tickets transitent vers le Site Central
- **Archivage** : ZIP immuable + timbre SHA-256 pour garantir l'intégrité
