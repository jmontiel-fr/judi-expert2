# Méthodologie — Judi-Expert

## Introduction

Ce document présente la solution Judi-Expert, son usage de l'intelligence artificielle comme assistant à l'expert judiciaire, et sa conformité aux exigences réglementaires en vigueur. Il est destiné à accompagner l'expert dans la justification de l'usage de l'IA auprès des instances judiciaires.

> Pour la définition des termes et acronymes utilisés dans ce document, consultez le [Glossaire & Workflow](glossaire-workflow.md).

---

## 1. Autorisations des experts judiciaires en matière de rédaction de rapports

### Cadre juridique applicable

L'expert judiciaire exerce sa mission dans un cadre légal précis, défini par les textes suivants :

**En matière pénale — Code de procédure pénale (articles 156 à 169) :**

- **Article 156** : Le juge d'instruction ou la juridiction de jugement peut ordonner une expertise. L'expert est choisi parmi les personnes inscrites sur les listes d'experts judiciaires.
- **Article 157** : Les experts sont choisis parmi les personnes physiques ou morales figurant sur la liste nationale ou sur une liste dressée par chaque cour d'appel.
- **Article 158** : La décision qui ordonne l'expertise précise la mission confiée à l'expert et fixe le délai dans lequel le rapport doit être déposé.
- **Article 160** : L'expert doit remplir sa mission personnellement. Toutefois, il peut se faire assister par des personnes qualifiées sous sa responsabilité.
- **Article 166** : L'expert rédige un rapport qui contient la description des opérations pratiquées, les conclusions motivées et les réponses aux questions posées.
- **Article 169** : L'expert dépose son rapport au greffe de la juridiction qui l'a commis.

**En matière civile — Code de procédure civile (articles 232 à 284) :**

- **Article 232** : Le juge peut commettre toute personne de son choix pour l'éclairer par des constatations, une consultation ou une expertise sur une question de fait qui requiert les lumières d'un technicien.
- **Article 233** : Le technicien commis doit accomplir sa mission avec conscience, objectivité et impartialité.
- **Article 237** : Le technicien commis doit donner son avis sur les points pour l'examen desquels il a été commis. Il ne peut répondre à d'autres questions.
- **Article 238** : Le technicien doit donner son avis sur les points pour l'examen desquels il a été commis. Son rapport doit être clair, précis et motivé.
- **Article 276** : L'expert doit prendre en considération les observations des parties et, lorsqu'elles sont écrites, les joindre à son avis.
- **Article 282** : Le rapport de l'expert est déposé au greffe de la juridiction.

### Liberté méthodologique de l'expert

Les textes précités confèrent à l'expert judiciaire une **liberté méthodologique** dans la conduite de ses opérations d'expertise, sous réserve de respecter les principes fondamentaux suivants :

1. **Mission personnelle** : l'expert accomplit sa mission personnellement (art. 160 CPP)
2. **Conscience et objectivité** : l'expert agit avec conscience, objectivité et impartialité (art. 233 CPC)
3. **Rapport motivé** : le rapport doit être clair, précis et motivé (art. 238 CPC)
4. **Réponse aux questions** : l'expert répond aux questions posées par la juridiction (art. 237 CPC)

L'expert est libre de choisir les outils et méthodes qu'il juge appropriés pour accomplir sa mission, y compris des outils informatiques d'assistance, dès lors que :
- Il conserve la maîtrise intellectuelle de ses conclusions
- Il assume la responsabilité de l'intégralité de son rapport
- Les outils utilisés ne se substituent pas à son jugement professionnel

---

## 2. Présentation de Judi-Expert

### Description de la solution

Judi-Expert est un système d'assistance aux experts judiciaires qui automatise les tâches répétitives du processus d'expertise tout en laissant à l'expert le contrôle total de ses conclusions.

Le système se compose de deux parties :

- **Application Locale** : installée sur le PC de l'expert, elle gère le workflow d'expertise en 5 étapes (extraction OCR, préparation investigations, consolidation documentaire, production pré-rapport, finalisation et archivage). Toutes les données d'expertise restent exclusivement sur le PC de l'expert. L'authentification utilise les identifiants du Site Central (connexion Internet requise).

- **Site Central** : plateforme web de gestion des inscriptions, des tickets d'expertise et de la distribution des modules de connaissances par domaine.

### Workflow d'expertise assisté par l'IA

| Étape | Nom | Rôle de l'IA | Rôle de l'expert |
|-------|-----|-------------|------------------|
| Step 1 | Création dossier | Extraction OCR + structuration Markdown + extraction placeholders et questions | Vérification du texte extrait, validation des placeholders et questions |
| Step 2 | Extraction PE/PA depuis TRE | Extraction mécanique du PE/PA depuis le TRE (à partir de `@debut_tpe@`), intégration des questions en conclusion | Validation, adaptation du plan |
| Step E/A | Entretien ou Analyse | Aucun | Mener les entretiens/analyses, annoter le PE/PA → produire PEA/PAA |
| Step 3 | Consolidation documentaire | Extraction OCR des pièces de diligence | Vérification des extractions |
| Step 4 | Production pré-rapport | Reconstitution du rapport (TRE header + PEA), reformulation LLM des annotations `@dires` et `@analyse`, substitution placeholders, génération PRE et DAC | Relecture, ajustement des conclusions |
| Step 5 | Révision et archivage | Révision linguistique LLM (préservation verbatim), création archive ZIP + timbre.txt (métadonnées + hash SHA-256) | Import du rapport final ajusté, validation des corrections, archivage |

À chaque étape, l'expert conserve la possibilité de modifier, corriger et valider les productions de l'IA avant de passer à l'étape suivante.

---

## 3. Usage de l'IA comme assistant à l'expert

### Principe fondamental

L'intelligence artificielle intégrée à Judi-Expert est utilisée exclusivement comme **outil d'assistance** à l'expert judiciaire. Elle ne se substitue en aucun cas au jugement professionnel de l'expert.

### Rôle de l'IA

L'IA intervient dans les tâches suivantes :

1. **Extraction et structuration de texte** (Step 1) : conversion des documents scannés en texte exploitable via OCR, structuration automatique en Markdown, extraction des questions du tribunal (Q1…Qn) et des valeurs de placeholders pour le template de rapport. L'expert vérifie et corrige le résultat.

2. **Extraction du plan d'entretien ou d'analyse depuis le TRE** (Step 2) : extraction mécanique du PE (Mode Entretien) ou PA (Mode Analyse) depuis le TRE à partir du marqueur `@debut_tpe@`. Aucune génération LLM — le plan est directement extrait du template de l'expert. Les questions du tribunal sont intégrées en section conclusion. L'expert adapte le plan à son contexte.

3. **Extraction OCR des pièces de diligence** (Step 3) : conversion des documents reçus en réponse aux diligences en format Markdown. L'expert vérifie les extractions.

4. **Production du pré-rapport** (Step 4) : reconstitution du rapport complet à partir de l'en-tête du TRE (avant `@debut_tpe@`) et du PEA/PAA annoté. Reformulation LLM des annotations `@dires` et `@analyse` (texte abrégé → texte rédigé professionnel). Préservation des `@verbatim` entre guillemets sans modification. Résolution des `@reference` et `@cite`. Substitution des placeholders `<<...>>` depuis `placeholders.csv`. Production du pré-rapport (`pre.docx`). L'expert valide le rapport.

5. **Analyse contradictoire** (Step 4 — DAC) : génération d'un Document d'Analyse Contradictoire (`dac.docx`) identifiant les points de contestation possibles et proposant des pistes de renforcement. L'expert décide des modifications à retenir.

6. **Révision linguistique** (Step 5) : correction automatique du rapport final par le LLM (orthographe, grammaire, syntaxe) avec préservation intacte des textes entre guillemets (verbatim). Les corrections sont présentées à l'expert pour validation.

7. **Archivage sécurisé** (Step 5) : création d'une archive ZIP immuable contenant tous les fichiers du dossier, avec génération d'un fichier timbre (`<nom-dossier>-timbre.txt`) contenant les métadonnées d'expertise et le hash SHA-256 du ZIP. L'expert peut compléter par un horodatage juridiquement certifié.

8. **Assistant conversationnel** (ChatBot) : réponses aux questions de l'expert sur le domaine d'expertise et l'utilisation du système.

### Documents annotés par l'expert (PEA / PAA)

Après la génération du plan d'entretien (PE) ou du plan d'analyse (PA) au Step 2, l'expert annote le document en style télégraphique pour produire :

- **PEA** (`pea.docx`) : Plan d'Entretien Annoté — en Mode Entretien
- **PAA** (`paa.docx`) : Plan d'Analyse Annoté — en Mode Analyse

L'expert utilise des balises d'annotation standardisées :

| Balise | Usage |
|--------|-------|
| `@dires ..... @` | Propos rapportés par l'interviewé |
| `@analyse ..... @` | Observations et interprétations de l'expert |
| `@verbatim ..... @` | Citation textuelle mot pour mot |
| `@question n @` | Référence à la question réquisition N° n |
| `@reference section xxx @` | Substitution des sections dires/analyses relatives à la section xxx |

Ces documents annotés constituent l'entrée principale du Step 4 pour la génération du pré-rapport. Le système interprète les balises pour structurer le rapport final.

### Garanties méthodologiques

- **L'expert reste maître de ses conclusions** : chaque production de l'IA est soumise à la validation de l'expert avant d'être intégrée au dossier
- **Traçabilité complète** : tous les fichiers intermédiaires sont conservés et archivés
- **Transparence** : l'expert peut consulter et modifier chaque document généré
- **Pas de boîte noire** : le LLM utilisé (Mistral 7B) est un modèle open-source dont le fonctionnement est documenté

### Modèle d'IA utilisé

| Caractéristique | Détail |
|----------------|--------|
| Modèle | Mistral 7B Instruct v0.3 |
| Licence | Apache 2.0 (open-source) |
| Exécution | Locale (sur le PC de l'expert, via Ollama) |
| Paramètres | 7.25 milliards |
| Langue | Optimisé pour le français |
| Connexion internet | Non requise pour l'inférence |

### Base de connaissances (RAG)

Le système utilise une base de connaissances vectorielle (RAG — Retrieval-Augmented Generation) spécialisée par domaine d'expertise. Cette base contient :

- Des documents de référence publics (guides méthodologiques, textes réglementaires, référentiels de bonnes pratiques)
- Des URLs de ressources institutionnelles et académiques
- Le TPE ou TPA (trame d'entretien ou d'analyse) de l'expert
- Le template de rapport (`tre.docx`) avec ses placeholders `<<...>>`

La base RAG enrichit les réponses de l'IA avec des informations factuelles et à jour, réduisant les risques d'hallucination.

---

## 4. Conformité réglementaire

### RGPD (Règlement Général sur la Protection des Données)

Judi-Expert est conçu dans le respect du RGPD :

| Principe RGPD | Mise en œuvre |
|---------------|--------------|
| **Minimisation des données** | Seuls les tickets transitent entre l'Application Locale et le Site Central. Aucune donnée d'expertise n'est transmise. |
| **Localisation des données** | Toutes les données d'expertise sont stockées exclusivement sur le PC de l'expert. |
| **Chiffrement** | Le chiffrement du disque (BitLocker/FileVault) est exigé à l'installation. |
| **Droit à l'effacement** | L'expert peut supprimer ses dossiers localement. Sur le Site Central, la suppression de compte est possible. |
| **Consentement** | L'inscription sur le Site Central requiert l'acceptation explicite des CGU et des mentions légales. |
| **Sous-traitance** | Le LLM fonctionne localement. Aucun sous-traitant n'a accès aux données d'expertise. |

### AI Act (Règlement européen sur l'intelligence artificielle)

Le Règlement (UE) 2024/1689 du 13 juin 2024 (AI Act) établit un cadre réglementaire pour les systèmes d'intelligence artificielle dans l'Union européenne.

**Classification du système :**

Judi-Expert est un système d'IA utilisé comme outil d'assistance à la décision dans un contexte judiciaire. Selon l'AI Act, les systèmes d'IA utilisés dans l'administration de la justice peuvent être classés comme systèmes à **haut risque** (Annexe III, point 8).

**Mesures de conformité :**

| Exigence AI Act | Mise en œuvre |
|----------------|--------------|
| **Transparence** | L'expert est informé qu'il utilise un système d'IA. Les documents générés sont identifiés comme produits avec assistance IA. |
| **Supervision humaine** | L'expert valide chaque étape. L'IA ne produit aucun document final sans validation humaine. |
| **Exactitude et robustesse** | Le RAG enrichit les réponses avec des sources vérifiables. L'expert vérifie et corrige les productions. |
| **Documentation technique** | Le présent document et la documentation technique du projet sont disponibles. |
| **Gestion des risques** | Le workflow séquentiel avec validation à chaque étape limite les risques d'erreur. |
| **Qualité des données** | Le corpus RAG est constitué de documents publics de référence, vérifiés et à jour. |
| **Traçabilité** | Tous les fichiers intermédiaires sont conservés et archivés dans un ZIP immuable avec timbre d'horodatage (hash SHA-256). |

### Protection des données d'expertise

L'architecture de Judi-Expert garantit la protection des données d'expertise par conception :

1. **Exécution locale du LLM** : le modèle d'IA fonctionne sur le PC de l'expert, sans connexion à un service cloud
2. **Base RAG locale** : la base de connaissances vectorielle est stockée localement
3. **Aucune transmission de données** : les documents d'expertise ne quittent jamais le PC de l'expert
4. **Chiffrement obligatoire** : le chiffrement du disque est vérifié à l'installation
5. **Archivage immuable** : les dossiers finalisés sont archivés en ZIP avec un timbre d'horodatage (hash SHA-256 stocké sur S3) et ne peuvent plus être modifiés. L'expert peut compléter par un horodatage juridiquement certifié.

---

## 5. Responsabilité de l'expert

L'utilisation de Judi-Expert ne modifie en rien la responsabilité de l'expert judiciaire :

- L'expert **assume l'intégralité de la responsabilité** de son rapport d'expertise
- L'expert **valide personnellement** chaque étape du workflow et chaque document produit
- L'IA est un **outil d'assistance** qui ne se substitue pas au jugement professionnel
- L'expert peut à tout moment **modifier, corriger ou rejeter** les productions de l'IA
- Le rapport final déposé au greffe est celui **validé par l'expert**, qui en est l'auteur

---

## 6. Références juridiques

- Code de procédure pénale, articles 156 à 169 (expertise en matière pénale)
- Code de procédure civile, articles 232 à 284 (mesures d'instruction confiées à un technicien)
- Règlement (UE) 2016/679 du 27 avril 2016 (RGPD)
- Règlement (UE) 2024/1689 du 13 juin 2024 (AI Act)
- Loi n° 71-498 du 29 juin 1971 relative aux experts judiciaires
- Décret n° 2004-1463 du 23 décembre 2004 relatif aux experts judiciaires


---

## 8. Sécurité et protection des données

### Architecture sécurisée

L'application locale Judi-Expert est conçue avec une architecture de sécurité en profondeur :

- **Isolation réseau** : les conteneurs IA (LLM, OCR, RAG) fonctionnent dans un réseau Docker interne sans accès à Internet. Les données d'expertise ne peuvent physiquement pas fuiter vers l'extérieur.
- **Chiffrement** : le disque du PC expert doit être chiffré (BitLocker sous Windows 11 Pro). Les communications avec le Site Central utilisent HTTPS/TLS 1.3.
- **Intégrité** : chaque dossier finalisé est archivé avec un hash SHA-256 pour garantir la non-altération des documents.
- **Authentification** : JWT local avec vérification des credentials via le Site Central (AWS Cognito).

### Conformité RGPD

- Toutes les données d'expertise restent sur le PC de l'expert
- Seuls les tokens de tickets transitent vers le cloud
- Droit à l'effacement garanti (suppression complète des dossiers)
- Pas de transfert de données personnelles vers des services tiers

### Conformité AI Act

- L'IA est un outil d'assistance, pas un décideur
- L'expert valide chaque étape du workflow
- Modèle open-source (Mistral 7B, Apache 2.0), inférence 100% locale

Pour le détail complet des mesures de sécurité, voir [securite.md](securite.md).
