# Guide de l'Expert — Judi-Expert

## Vue d'ensemble

Judi-Expert est un assistant IA pour la production de rapports d'expertise judiciaire. L'application gère le workflow complet, de la réception de l'ordonnance à l'archivage du rapport final.

---

## Les deux types de workflow

### Workflow Standard (5 étapes)

Le workflow standard couvre l'intégralité du processus d'expertise avec entretien :

| Étape | Nom | Description |
|-------|-----|-------------|
| 0 | Création de dossier | Choix du workflow, saisie du token ticket |
| 1 | Initialisation dossier | Import ordonnance, OCR, extraction questions et placeholders |
| 2 | Validation TRE → PREA | Validation syntaxique du template, production du PREA |
| E/A | Entretien ou Analyse | Hors application : l'expert annote le PREA |
| 3 | Consolidation documentaire | Import et OCR des pièces de diligence |
| 4 | Production pré-rapport | Reformulation IA, résolution annotations → PRE + DAC |
| 5 | Finalisation et archivage | Import REF, archive ZIP + timbre SHA-256 |

**Cas d'usage** : expertise complète nécessitant un entretien avec la personne expertisée (psychologie, psychiatrie, etc.).

### Workflow Simple (2 étapes)

Le workflow simple est destiné aux experts qui ont déjà rédigé leur rapport et souhaitent uniquement une mise en forme linguistique :

| Étape | Nom | Description |
|-------|-----|-------------|
| 1 | Mise en forme linguistique | Import PRE → révision IA → PREF |
| 2 | Archivage | Archive ZIP + timbre SHA-256 |

**Cas d'usage** : rapport déjà rédigé manuellement, l'expert souhaite une correction linguistique professionnelle avant soumission.

---

## Le TRE (Template de Rapport d'Expertise)

### Qu'est-ce que le TRE ?

Le TRE est un fichier **Word (.docx)** qui constitue votre trame de rapport d'expertise. C'est un document Word classique enrichi d'**annotations** (balises `@type ... @`) et de **placeholders** (`<<nom>>`) aux endroits où l'IA doit intervenir.

Le TRE conserve intégralement sa mise en forme Word : titres, styles, numérotation, table des matières, en-têtes/pieds de page. Seules les annotations sont traitées par l'IA.

### Cycle de vie du TRE

```
TRE (votre template)
  ↓ Step 2 : validation syntaxique
PREA (copie de travail)
  ↓ Step E/A : annotation par l'expert pendant l'entretien
PREA annoté
  ↓ Step 4 : traitement IA
PRE (Pré-Rapport d'Expertise)
  ↓ Relecture et ajustements par l'expert
REF (Rapport d'Expertise Final)
```

---

## Format du TRE — Annotations

### Types d'annotations

| Annotation | Format | Rôle |
|-----------|--------|------|
| `@dires section_x.x_suffixe ... @` | Bloc | Propos rapportés par la personne expertisée. Reformulés par l'IA en style professionnel (3ème personne). |
| `@analyse section_x.x_suffixe ... @` | Bloc | Observations et interprétations cliniques. Reformulées en style rapport. |
| `@verbatim "citation" @` | Inline | Citation textuelle exacte. Jamais modifiée par l'IA. |
| `@remplir_champ nom : contenu @` | Inline | Champ court à remplir (ex: date, lieu). S'intègre dans le flux du texte. |
| `@remplir_bloc contenu multiligne @` | Bloc | Zone de texte libre multiligne à remplir par l'expert. |
| `@conclusion ... @` | Bloc | Bloc de conclusion. Accepte l'injection de références via la palette. |
| `@question N @` | Inline | Insère la réponse à la question N du tribunal. |
| `@reference section_x.x @` | Inline | Insère une référence aux dires/analyse d'une section. |
| `@cite section_x.x @` | Inline | Citation des dires d'une section. |
| `@resume section_x.x, section_y.y @` | Bloc | Résumé automatique IA de plusieurs sections. |
| `@date_naissance_pex JJ/MM/AAAA @` | Inline | Champ date de naissance (sert au calcul de @age@). |
| `@age@` | Inline | Calcul automatique de l'âge à la date de l'entretien. |

### Distinction `@remplir_champ` vs `@remplir_bloc`

- **`@remplir_champ`** : s'insère dans le flux du texte (inline). Exemple : "L'entretien a eu lieu le `@remplir_champ date_entretien : JJ/MM/AAAA@` à mon cabinet."
- **`@remplir_bloc`** : crée un bloc multiligne séparé. Exemple :

```
@remplir_bloc
<<genre_pex>> <<prenom_pex>> <<nom_pex>> a été attentif/attentive
à l'énoncé du cadre de l'expertise et des missions qui m'ont été
confiées. Son niveau de compréhension semblait permettre la
réalisation de l'expertise.
@
```

### Placeholders `<<nom>>`

Les placeholders sont des champs de substitution automatique. Extraits de l'ordonnance au Step 1, ils sont remplacés dans le rapport final au Step 4.

| Placeholder | Signification |
|------------|---------------|
| `<<nom_pex>>` | Nom de la personne expertisée |
| `<<prenom_pex>>` | Prénom de la personne expertisée |
| `<<genre_pex>>` | Monsieur / Madame |
| `<<date_naissance_pex>>` | Date de naissance |
| `<<nom_expert>>` | Nom de l'expert |
| `<<prenom_expert>>` | Prénom de l'expert |
| `<<titre_expert>>` | Titre professionnel (ex: expert psychologue) |
| `<<nom_tribunal>>` | Juridiction émettrice |
| `<<ville_tribunal>>` | Ville du tribunal |
| `<<date_mission>>` | Date de la réquisition |
| `<<reference_dossier>>` | Numéro de dossier |
| `<<requerant_nom>>` | Nom du requérant (OPJ, magistrat) |
| `<<objet_mission>>` | Chapeau introductif de la mission |

### Nommage des sections dans les annotations

Les annotations `@dires` et `@analyse` utilisent un suffixe de section pour identifier à quel passage du rapport elles se rapportent :

```
@dires section_3.1.1_pere ... @
@analyse section_3.1.1_pere ... @
```

Le format est : `section_NUMERO_SUFFIXE` où :
- `NUMERO` correspond à la numérotation du plan (3.1.1)
- `SUFFIXE` est un identifiant court et parlant (pere, mere, scolarite, etc.)

---

## Construction du TRE — Deux méthodes

### Méthode 1 : Avec l'éditeur PEA (assistant d'édition)

L'application propose un **éditeur visuel** (menu Outils > Éditer PEA) qui permet de :

1. **Charger un fichier .docx existant** (votre trame de rapport)
2. **Visualiser la structure** : headings, texte, annotations détectées
3. **Éditer les annotations** : modifier le contenu des blocs `@dires`, `@analyse`, `@remplir_bloc`
4. **Insérer des annotations** via la palette visuelle (sans taper la syntaxe manuellement)
5. **Insérer des placeholders** `<<nom>>` depuis une liste déroulante
6. **Utiliser la palette de conclusion** : injection de `@question`, `@reference`, `@cite`, `@resume`
7. **Sauvegarder** le document modifié en .docx

**Avantages** :
- Pas besoin de connaître la syntaxe exacte
- Détection automatique des erreurs de syntaxe
- Visualisation immédiate de la structure
- Palette d'insertion pour les annotations complexes

**Accès** : Menu Outils > Éditer PEA

### Méthode 2 : Édition manuelle dans Word

Vous pouvez construire votre TRE directement dans Microsoft Word :

1. **Créer votre structure de rapport** avec les sections et titres habituels
2. **Insérer les annotations** en tapant les balises `@type ... @` dans le texte
3. **Insérer les placeholders** en tapant `<<nom_placeholder>>`
4. **Enregistrer en .docx**

**Règles à respecter** :
- Les annotations doivent être **une par paragraphe** (un retour à la ligne avant et après pour les blocs)
- Le `@` ouvrant doit être en début de paragraphe (ou après un espace)
- Le `@` fermant doit être en fin de paragraphe (ou suivi d'un espace/ponctuation)
- Les annotations inline (`@remplir_champ`) peuvent s'insérer au milieu d'un paragraphe
- Ne pas couper une annotation sur plusieurs cellules de tableau

**Avantages** :
- Maîtrise totale de la mise en forme Word (styles, tableaux, images)
- Possibilité d'utiliser des fonctionnalités Word avancées
- Pas de dépendance à l'éditeur intégré

**Recommandation** : commencer par la méthode manuelle pour comprendre la syntaxe, puis utiliser l'éditeur PEA pour les modifications rapides et la vérification.

---

## Structure type d'un TRE

```
1. Identification et cadre de mission
   <<genre_pex>> <<prenom_pex>> <<nom_pex>>, né(e) le
   <<date_naissance_pex>> à <<ville_naissance_pex>>

   @remplir_champ date_entretien : JJ/MM/AAAA@

   @remplir_bloc
   <<genre_pex>> <<prenom_pex>> <<nom_pex>> a été attentif/attentive
   à l'énoncé du cadre de l'expertise. Son niveau de compréhension
   semblait permettre la réalisation de l'expertise.
   @

2. Anamnèse
   2.1 Famille d'origine
       @dires section_2.1_famille@
       @analyse section_2.1_famille@
   2.2 Parcours scolaire
       @dires section_2.2_scolarite@
       @analyse section_2.2_scolarite@

3. Examen clinique
   3.1 Entretien
       3.1.1 Relation au père
           @dires section_3.1.1_pere@
           @analyse section_3.1.1_pere@
       3.1.2 Relation à la mère
           @dires section_3.1.2_mere@
           @analyse section_3.1.2_mere@

4. Conclusions
   @conclusion@
   (palette : @question 1@, @reference section_3.1.1_pere@, etc.)
```

---

## Workflow Standard — Détail des étapes

### Step 0 — Création de dossier
**Préparation** : acheter un ticket sur le Site Central, récupérer le token par email.
**Action** : créer le dossier, choisir le workflow standard.

### Step 1 — Initialisation dossier
**Préparation** : scanner l'ordonnance en PDF (≥ 300 dpi), scanner les pièces complémentaires.
**Action** : importer, l'IA extrait le texte, identifie les questions et placeholders.
**Vérification** : relire le Markdown, corriger les erreurs OCR, valider questions et placeholders.

### Step 2 — Validation TRE → PREA
**Préparation** : s'assurer que le TRE est configuré (page Configuration) et que le Step 1 est validé.
**Action** : validation syntaxique du TRE, production du PREA.
**Résultat** : télécharger le PREA pour l'annoter lors de l'entretien.

### Step E/A — Entretien ou Analyse (hors application)
**Préparation** : imprimer ou ouvrir le PREA sur tablette/PC.
**Action** : mener l'entretien, remplir les `@dires` et `@analyse`, insérer les `@verbatim`.
**Résultat** : PREA complété, prêt pour import au Step 4.

### Step 3 — Consolidation documentaire
**Préparation** : rassembler et scanner les pièces de diligence reçues.
**Action** : importer les pièces, extraction OCR automatique.
**Vérification** : contrôler la qualité des extractions.

### Step 4 — Production pré-rapport
**Préparation** : finaliser le PREA (toutes annotations remplies), vérifier les verbatim entre guillemets.
**Action** : l'IA reformule, résout les références, substitue les placeholders → PRE.
**Options** : générer le DAC (analyse contradictoire).
**Vérification** : relire le PRE, ajuster les conclusions.

### Step 5 — Finalisation et archivage
**Préparation** : produire le REF (PRE ajusté et validé par l'expert).
**Action** : import du REF, création archive ZIP + timbre SHA-256.

---

## Workflow Simple — Détail des étapes

### Step 1 — Mise en forme linguistique
**Préparation** : rédiger le PRE dans Word, encadrer les citations entre guillemets (protégées).
**Action** : l'IA corrige orthographe/grammaire/syntaxe, préserve les verbatim.
**Résultat** : PREF (Projet de Rapport d'Expertise Final).

### Step 2 — Archivage
**Préparation** : vérifier le PREF, s'assurer de la version définitive.
**Action** : archive ZIP + timbre SHA-256.

---

## Bonnes pratiques

1. **Scanner en haute résolution** (≥ 300 dpi) pour une meilleure OCR
2. **Toujours vérifier** les extractions OCR et les questions identifiées
3. **Encadrer les citations** entre guillemets dans le PREA (protection verbatim)
4. **Compléter toutes les annotations** avant de lancer le Step 4
5. **Relire le PRE** systématiquement — l'IA assiste mais l'expert reste maître
6. **Utiliser le DAC** pour anticiper les contestations possibles
7. **Tester son TRE** avec l'éditeur PEA pour détecter les erreurs de syntaxe
8. **Nommer les sections** de façon parlante (ex: `section_3.1.1_pere` plutôt que `section_3.1.1`)

---

## Sécurité et confidentialité

- Toutes les données restent sur votre PC — rien ne transite par Internet
- Le LLM (Mistral 7B) tourne en local via Ollama
- Chiffrement disque obligatoire (BitLocker / FileVault)
- Seuls les tickets transitent entre l'application locale et le Site Central
