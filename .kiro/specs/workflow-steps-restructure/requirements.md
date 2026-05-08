# Requirements Document

## Introduction

Restructuration de l'interface utilisateur des pages d'étapes (Steps) dans l'Application Locale Judi-Expert. Chaque page d'étape doit être réorganisée en 3 sections claires (Fichiers d'entrée, Opération, Fichiers de sortie) avec un bandeau descriptif "Action" en haut. La terminologie doit être alignée avec celle du workflow présenté sur la page d'accueil du Site Central.

## Glossary

- **Application_Locale**: Application de bureau Judi-Expert installée sur le poste de l'expert, composée de 4 conteneurs Docker (backend FastAPI, frontend Next.js, OCR, LLM)
- **Step_Page**: Page de l'interface frontend affichant le détail d'une étape du workflow pour un dossier donné
- **Action_Banner**: Bandeau descriptif affiché en haut de chaque Step_Page expliquant ce que l'étape réalise
- **Input_Section**: Section "Fichiers d'entrée" affichant les fichiers nécessaires à l'exécution de l'étape
- **Operation_Section**: Section "Opération" contenant le bouton déclencheur de l'action de l'étape
- **Output_Section**: Section "Fichiers de sortie" affichant les fichiers produits par l'exécution de l'étape
- **File_Tree**: Arborescence de fichiers sur le disque local structurée en `C:\judi-expert\<nom-dossier>\step<N>\in` et `step<N>\out`
- **OCR_Extraction**: Processus de conversion de fichiers PDF/scan en texte au format Markdown
- **TPE**: Template de Plan d'Entretien — trame standard ou personnalisée utilisée pour préparer les entretiens
- **TPA**: Template de Plan d'Analyse — trame standard ou personnalisée utilisée pour préparer l'analyse sur pièces
- **PE**: Plan d'Entretien — document généré contenant les questions et la structure de l'entretien
- **PA**: Plan d'Analyse — document généré contenant les analyses et diligences à mener
- **PEA**: Plan d'Entretien Annoté — document `pea.docx`, PE annoté par l'expert en style télégraphique avec les conventions d'annotation (@dires, @analyse, @verbatim, @question, @reference). Fichier d'entrée du Step 4 en Mode_Entretien.
- **PAA**: Plan d'Analyse Annoté — document `paa.docx`, PA annoté par l'expert en style télégraphique avec les conventions d'annotation (@dires, @analyse, @verbatim, @question, @reference). Fichier d'entrée du Step 4 en Mode_Analyse.
- **PRE**: Pré-Rapport d'Expertise — document de rapport généré avant finalisation par l'expert
- **DAC**: Document d'Analyse Contradictoire — ensemble de remarques et suggestions pour challenger les conclusions de l'expert
- **TRE**: Template de Rapport d'Expertise — modèle standard ou personnalisé pour le rapport final
- **Mode_Entretien**: Mode d'expertise basé sur des entretiens avec les parties
- **Mode_Analyse**: Mode d'expertise basé sur l'analyse documentaire des pièces

## Requirements

### Requirement 1 : Structure tripartite des pages d'étape

**User Story :** En tant qu'expert judiciaire, je veux que chaque page d'étape soit clairement divisée en sections Entrée, Opération et Sortie, afin de comprendre immédiatement quels fichiers entrent, quelle action est réalisée, et quels fichiers sont produits.

#### Acceptance Criteria

1. LA Step_Page DOIT afficher exactement trois sections visuelles distinctes dans l'ordre suivant : Input_Section, Operation_Section, Output_Section
2. L'Input_Section DOIT afficher le titre "Fichiers d'entrée" et lister tous les fichiers d'entrée associés à l'étape courante
3. L'Operation_Section DOIT afficher le titre "Opération" et contenir le bouton déclencheur de l'action de l'étape courante
4. L'Output_Section DOIT afficher le titre "Fichiers de sortie" et lister tous les fichiers produits par l'étape courante
5. QUAND aucun fichier de sortie n'existe pour une étape, L'Output_Section DOIT afficher un message indicatif précisant qu'aucune sortie n'a encore été générée
6. QUAND aucun fichier d'entrée n'a été téléversé pour une étape, L'Input_Section DOIT afficher un message indicatif précisant que des fichiers d'entrée sont requis

### Requirement 2 : Bandeau Action descriptif

**User Story :** En tant qu'expert judiciaire, je veux voir une description claire de ce que chaque étape réalise en haut de la page, afin de comprendre l'objectif et le fonctionnement de l'étape avant d'interagir avec elle.

#### Acceptance Criteria

1. LA Step_Page DOIT afficher un Action_Banner en haut de la page, sous le titre de l'étape et au-dessus des trois sections
2. L'Action_Banner de l'étape 1 DOIT afficher le texte : "Entrée de tous les fichiers du dossier. Ceux-ci sont stockés dans C:\judi-expert\<nom-dossier>\step1\in. Les fichiers .pdf sont transformés en texte au format .md dans \step1\out. On extrait de l'ordonnance la liste des questions à résoudre numérotées Q1 à Qn"
3. L'Action_Banner de l'étape 2 DOIT afficher le texte : "Extrait de ordonnance.md la liste des questions à résoudre dans l'expertise et les numérote : Q1, ..., Qn. Utilise le template d'entretien (TPE) ou d'analyse (TPA) pour préparer la Trame d'entretien ou d'analyse des pièces. Produit le plan d'entretien PE ou le Plan d'Analyse PA en injectant dans le TPE ou le TPA selon le cas, des questions particulières à poser en entretien ou des analyses pertinentes et diligences à initier pour l'analyse sur pièces, et dans le cas de PA des projets de courriers pour les diligences complémentaires à initier"
4. L'Action_Banner de l'étape 3 DOIT afficher le texte : "Introduction des pièces complémentaires issues de diligences et extraction OCR en format .md pour les pièces PDF/scan de texte."
5. L'Action_Banner de l'étape 4 DOIT afficher le texte : "Produire un Pré-Rapport final à partir du PEA ou du PAA annoté par l'expert avec les notes d'entretien, les notes d'analyses et les conclusions aux questions numérotées, le tout en style télégraphique compact. La conclusion présente les questions et construit les réponses sur la base des sections du document complété. Le DAC (Document d'Analyse Contradictoire) est un ensemble de remarques et suggestions proposées par l'outil pour renforcer et challenger les analyses et conclusions de l'expert."
6. L'Action_Banner DOIT être visuellement distinct du reste du contenu de la page en utilisant un fond mis en évidence et une icône ou un libellé "Action"

### Requirement 3 : Fichiers d'entrée pour Step 1 (Création dossier)

**User Story :** En tant qu'expert judiciaire, je veux téléverser l'ordonnance et les documents complémentaires dans la section Entrée de l'étape 1, afin que le système puisse extraire le texte et identifier les questions.

#### Acceptance Criteria

1. L'Input_Section de l'étape 1 DOIT accepter le téléversement d'un fichier ordonnance au format PDF (ordonnance.pdf)
2. L'Input_Section de l'étape 1 DOIT accepter le téléversement de zéro ou plusieurs fichiers complémentaires (piece-xxx.<format>) aux formats PDF, DOCX ou image
3. QUAND des fichiers sont téléversés à l'étape 1, L'Application_Locale DOIT stocker les fichiers d'entrée dans le répertoire `C:\judi-expert\<nom-dossier>\step1\in`
4. L'Input_Section de l'étape 1 DOIT afficher la liste des fichiers d'entrée téléversés avec leurs noms et tailles

### Requirement 4 : Fichiers de sortie pour Step 1 (Création dossier)

**User Story :** En tant qu'expert judiciaire, je veux voir les fichiers texte extraits dans la section Sortie après l'exécution de l'étape 1, afin de vérifier l'extraction OCR et les questions identifiées.

#### Acceptance Criteria

1. QUAND l'exécution de l'étape 1 est terminée, L'Output_Section DOIT afficher ordonnance.md comme fichier de sortie
2. QUAND l'exécution de l'étape 1 est terminée et que des fichiers PDF complémentaires ont été fournis, L'Output_Section DOIT afficher les fichiers piece-xxx.md correspondants
3. QUAND l'exécution de l'étape 1 est terminée, L'Output_Section DOIT afficher questions.md contenant la liste numérotée des questions (Q1 à Qn) extraites de l'ordonnance
4. L'Application_Locale DOIT stocker les fichiers de sortie de l'étape 1 dans le répertoire `C:\judi-expert\<nom-dossier>\step1\out`

### Requirement 5 : Fichiers d'entrée pour Step 2 (Préparation investigations)

**User Story :** En tant qu'expert judiciaire, je veux que la section Entrée de l'étape 2 affiche les fichiers sources et templates requis, afin de vérifier que toutes les entrées sont disponibles avant de générer le plan d'investigation.

#### Acceptance Criteria

1. L'Input_Section de l'étape 2 DOIT afficher ordonnance.md comme fichier d'entrée requis (provenant de la sortie de l'étape 1)
2. L'Input_Section de l'étape 2 DOIT afficher le fichier template applicable : TPE (tpe.md ou tpe.docx) en Mode_Entretien, ou TPA (tpa.md ou tpa.docx) en Mode_Analyse
3. L'Input_Section de l'étape 2 DOIT afficher la liste des fichiers piece-xxx disponibles depuis l'étape 1
4. QUAND des fichiers sont fournis pour l'étape 2, L'Application_Locale DOIT stocker les fichiers d'entrée dans le répertoire `C:\judi-expert\<nom-dossier>\step2\in`

### Requirement 6 : Fichiers de sortie pour Step 2 (Préparation investigations)

**User Story :** En tant qu'expert judiciaire, je veux voir le plan d'investigation généré et les documents associés dans la section Sortie de l'étape 2, afin de les examiner et les valider avant de poursuivre.

#### Acceptance Criteria

1. QUAND l'exécution de l'étape 2 est terminée en Mode_Entretien, L'Output_Section DOIT afficher pe.md et qmec.docx comme fichiers de sortie
2. QUAND l'exécution de l'étape 2 est terminée en Mode_Analyse, L'Output_Section DOIT afficher pa.md et pa.docx comme fichiers de sortie
3. QUAND l'exécution de l'étape 2 est terminée en Mode_Analyse et que des courriers de diligence sont générés, L'Output_Section DOIT afficher les fichiers diligence-xxx.docx
4. L'Application_Locale DOIT stocker les fichiers de sortie de l'étape 2 dans le répertoire `C:\judi-expert\<nom-dossier>\step2\out`

### Requirement 7 : Fichiers d'entrée pour Step 3 (Consolidation documentaire)

**User Story :** En tant qu'expert judiciaire, je veux téléverser les documents complémentaires reçus suite aux diligences dans la section Entrée de l'étape 3, afin qu'ils soient traités et ajoutés au dossier.

#### Acceptance Criteria

1. L'Input_Section de l'étape 3 DOIT accepter le téléversement d'un ou plusieurs fichiers de réponse aux diligences (diligence-xxx-piece-yyy.<format>)
2. QUAND des fichiers sont téléversés à l'étape 3, L'Application_Locale DOIT stocker les fichiers d'entrée dans le répertoire `C:\judi-expert\<nom-dossier>\step3\in`
3. L'Input_Section de l'étape 3 DOIT afficher la liste des fichiers de réponse aux diligences téléversés avec leurs noms

### Requirement 8 : Fichiers de sortie pour Step 3 (Consolidation documentaire)

**User Story :** En tant qu'expert judiciaire, je veux voir les fichiers markdown extraits par OCR dans la section Sortie de l'étape 3, afin de vérifier l'extraction textuelle des documents de diligence.

#### Acceptance Criteria

1. QUAND l'exécution de l'étape 3 est terminée, L'Output_Section DOIT afficher les fichiers diligence-xxx-piece-yyy.md pour chaque fichier d'entrée ayant nécessité une extraction textuelle
2. L'Application_Locale DOIT stocker les fichiers de sortie de l'étape 3 dans le répertoire `C:\judi-expert\<nom-dossier>\step3\out`
3. QUAND un fichier d'entrée ne nécessite pas d'extraction OCR (déjà au format texte), L'Output_Section DOIT indiquer qu'aucune extraction n'était nécessaire pour ce fichier

### Requirement 9 : Fichiers d'entrée pour Step 4 (Production pré-rapport)

**User Story :** En tant qu'expert judiciaire, je veux que la section Entrée de l'étape 4 affiche tous les documents sources requis, afin de confirmer que le système dispose de tout le nécessaire pour générer le pré-rapport.

#### Acceptance Criteria

1. L'Input_Section de l'étape 4 DOIT afficher le fichier pea.docx (Plan d'Entretien Annoté, en Mode_Entretien) ou paa.docx (Plan d'Analyse Annoté, en Mode_Analyse) contenant les annotations télégraphiques de l'expert avec les conventions de balisage (@dires, @analyse, @verbatim, @question, @reference)
2. L'Input_Section de l'étape 4 DOIT afficher le fichier template TRE (standard ou personnalisé)
3. QUAND des documents complémentaires ont été introduits à l'étape 3, L'Input_Section de l'étape 4 DOIT afficher ces documents comme entrées supplémentaires
4. QUAND des fichiers sont fournis pour l'étape 4, L'Application_Locale DOIT stocker les fichiers d'entrée dans le répertoire `C:\judi-expert\<nom-dossier>\step4\in`

### Requirement 10 : Fichiers de sortie pour Step 4 (Production pré-rapport)

**User Story :** En tant qu'expert judiciaire, je veux voir le pré-rapport généré et le document d'analyse contradictoire dans la section Sortie de l'étape 4, afin de les examiner et les affiner.

#### Acceptance Criteria

1. QUAND l'exécution de l'étape 4 est terminée, L'Output_Section DOIT afficher pre.docx (Pré-Rapport d'Expertise) comme fichier de sortie
2. QUAND l'exécution de l'étape 4 est terminée, L'Output_Section DOIT afficher dac.docx (Document d'Analyse Contradictoire) comme fichier de sortie
3. L'Application_Locale DOIT stocker les fichiers de sortie de l'étape 4 dans le répertoire `C:\judi-expert\<nom-dossier>\step4\out`

### Requirement 11 : Alignement terminologique avec le Site Central

**User Story :** En tant qu'expert judiciaire, je veux que les noms et descriptions des étapes dans l'Application Locale correspondent à la terminologie utilisée dans la section workflow du Site Central, afin que l'expérience soit cohérente entre les deux plateformes.

#### Acceptance Criteria

1. L'Application_Locale DOIT utiliser le nom d'étape "Création dossier" pour l'étape 1, en cohérence avec la section workflow du Site Central
2. L'Application_Locale DOIT utiliser le nom d'étape "Préparation investigations" pour l'étape 2, en cohérence avec la section workflow du Site Central
3. L'Application_Locale DOIT utiliser le nom d'étape "Consolidation documentaire" pour l'étape 3, en cohérence avec la section workflow du Site Central
4. L'Application_Locale DOIT utiliser le nom d'étape "Production pré-rapport" pour l'étape 4, en cohérence avec la section workflow du Site Central
5. L'Application_Locale DOIT utiliser les libellés "Entrée" et "Sortie" dans les sections UI des étapes, en cohérence avec les libellés des cartes workflow du Site Central
6. L'Application_Locale DOIT utiliser une terminologie simplifiée et cohérente dans tous les éléments UI et la documentation liés aux étapes, en évitant le jargon technique lorsqu'un équivalent plus simple existe

### Requirement 12 : Structure de stockage fichiers sur disque

**User Story :** En tant qu'expert judiciaire, je veux que les fichiers soient organisés dans une structure de répertoires prévisible sur mon disque local, afin de pouvoir facilement localiser et gérer les fichiers du dossier en dehors de l'application si nécessaire.

#### Acceptance Criteria

1. L'Application_Locale DOIT créer la structure de répertoires `C:\judi-expert\<nom-dossier>\step<N>\in` pour les fichiers d'entrée de chaque étape N
2. L'Application_Locale DOIT créer la structure de répertoires `C:\judi-expert\<nom-dossier>\step<N>\out` pour les fichiers de sortie de chaque étape N
3. QUAND un nouveau dossier est créé, L'Application_Locale DOIT créer l'arborescence complète avec les sous-répertoires pour toutes les étapes (step1 à step4)
4. L'Application_Locale DOIT utiliser le nom du dossier comme nom de répertoire sous `C:\judi-expert\`

### Requirement 13 : Opération — Bouton d'action par étape

**User Story :** En tant qu'expert judiciaire, je veux un bouton d'action clairement libellé dans la section Opération de chaque étape, afin de pouvoir déclencher le traitement de l'étape en un seul clic.

#### Acceptance Criteria

1. L'Operation_Section de l'étape 1 DOIT afficher un bouton libellé "Extraire et structurer" pour déclencher l'extraction OCR et la structuration des fichiers
2. L'Operation_Section de l'étape 2 DOIT afficher un bouton libellé "Générer le plan" pour déclencher la génération du plan d'investigation
3. L'Operation_Section de l'étape 3 DOIT afficher un bouton libellé "Extraire les documents" pour déclencher l'extraction OCR des documents de diligence
4. L'Operation_Section de l'étape 4 DOIT afficher un bouton libellé "Générer le pré-rapport" pour déclencher la génération du pré-rapport
5. TANT QUE une étape est au statut "en_cours", L'Operation_Section DOIT désactiver le bouton d'action et afficher un indicateur de progression
6. QUAND l'étape est verrouillée ou le dossier est clôturé, L'Operation_Section DOIT désactiver le bouton d'action et afficher un indicateur de verrouillage
