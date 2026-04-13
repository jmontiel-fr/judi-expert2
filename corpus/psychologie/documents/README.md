# Corpus Psychologie — Documents PDF de Référence

Ce répertoire est destiné à contenir des documents PDF publics de référence en expertise psychologique judiciaire. Ces documents seront indexés dans la base RAG (Qdrant) pour enrichir les réponses du LLM.

## Documents attendus

Les documents suivants doivent être téléchargés depuis leurs sources publiques respectives et placés dans ce répertoire :

### 1. Guide méthodologique — Expertise psychologique en matière pénale

- **Fichier attendu** : `guide_methodologique_expertise_psychologique_penale.pdf`
- **Source** : Ministère de la Justice — Direction des Affaires Criminelles et des Grâces
- **URL** : https://www.justice.gouv.fr
- **Description** : Guide de bonnes pratiques pour la conduite d'expertises psychologiques dans le cadre pénal. Couvre la méthodologie d'entretien, les outils d'évaluation et la rédaction du rapport.
- **Licence** : Document public institutionnel, librement accessible et redistribuable.

### 2. Code de déontologie des psychologues

- **Fichier attendu** : `code_deontologie_psychologues.pdf`
- **Source** : Commission Nationale Consultative de Déontologie des Psychologues (CNCDP)
- **URL** : http://www.cncdp.fr/index.php/code-de-deontologie/code-de-deontologie-2012
- **Description** : Code de déontologie des psychologues (version consolidée 2012). Définit les principes éthiques fondamentaux applicables à la pratique de l'expertise psychologique judiciaire.
- **Licence** : Document public, librement accessible.

### 3. Référentiel HAS — Évaluation psychologique dans le cadre judiciaire

- **Fichier attendu** : `referentiel_has_evaluation_psychologique.pdf`
- **Source** : Haute Autorité de Santé (HAS)
- **URL** : https://www.has-sante.fr
- **Description** : Recommandations de bonnes pratiques de la HAS relatives à l'évaluation psychologique, incluant les outils psychométriques validés et les protocoles d'évaluation standardisés.
- **Licence** : Document public institutionnel, librement accessible et redistribuable.

### 4. Textes réglementaires — Expertise judiciaire (Code de procédure pénale)

- **Fichier attendu** : `textes_reglementaires_expertise_judiciaire.pdf`
- **Source** : Légifrance — Service public de la diffusion du droit
- **URL** : https://www.legifrance.gouv.fr
- **Description** : Compilation des articles du Code de procédure pénale relatifs à l'expertise judiciaire (articles 156 à 169-1), incluant les conditions de désignation, les obligations de l'expert et le cadre procédural.
- **Licence** : Données juridiques publiques, licence ouverte Etalab.

### 5. Guide des bonnes pratiques — Expertise psychologique de la personnalité

- **Fichier attendu** : `guide_bonnes_pratiques_expertise_personnalite.pdf`
- **Source** : Société Française de Psychologie (SFP)
- **URL** : https://www.sfpsy.org
- **Description** : Référentiel de bonnes pratiques pour l'évaluation de la personnalité dans le cadre de l'expertise judiciaire. Couvre les tests psychométriques recommandés (MMPI-2, Rorschach, TAT) et les protocoles d'administration.
- **Licence** : Document public professionnel, librement accessible.

## Instructions d'ajout

1. Télécharger chaque document PDF depuis la source indiquée
2. Renommer le fichier selon le nom attendu ci-dessus
3. Placer le fichier dans ce répertoire (`corpus/psychologie/documents/`)
4. Mettre à jour `corpus/psychologie/contenu.yaml` si de nouveaux documents sont ajoutés

## Critères de sélection

Tous les documents inclus dans ce répertoire doivent respecter les critères suivants :
- **Public** : librement accessible sans authentification
- **Redistribuable** : licence compatible avec la redistribution
- **Pertinent** : en rapport direct avec l'expertise psychologique judiciaire
- **Fiable** : issu d'une source institutionnelle ou professionnelle reconnue
