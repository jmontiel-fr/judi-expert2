# Document d'Exigences — Gestion des Fichiers par Étape

## Introduction

Cette fonctionnalité enrichit la page de détail d'un dossier et les pages d'étapes dans l'Application Locale de Judi-Expert. L'objectif est d'afficher les fichiers produits par chaque étape directement dans la section correspondante, de permettre leur ouverture (prévisualisation inline ou nouvel onglet) et leur téléchargement, et d'offrir à l'expert la possibilité d'uploader une version modifiée d'un fichier. Les versions modifiées remplacent les originaux pour les étapes suivantes du workflow. Un système de versionnage léger permet de distinguer visuellement les fichiers originaux des fichiers modifiés par l'expert.

## Glossaire

- **Application_Locale** : Application web locale (Next.js + FastAPI) installée sur le PC de l'expert
- **Page_Dossier** : Page de détail d'un dossier affichant les 4 étapes du workflow (`/dossier/{id}`)
- **Page_Étape** : Page de détail d'une étape spécifique (`/dossier/{id}/step/{n}`)
- **Section_Étape** : Zone de la Page_Dossier dédiée à une étape donnée (Step 0–3)
- **Fichier_Étape** : Fichier produit ou associé à une étape, enregistré dans le modèle StepFile
- **Fichier_Original** : Fichier généré automatiquement par le système (OCR, LLM) ou uploadé initialement
- **Fichier_Modifié** : Version d'un Fichier_Original re-uploadée manuellement par l'expert
- **Expert** : Utilisateur authentifié de l'Application_Locale
- **Prévisualisation_Inline** : Affichage du contenu d'un fichier directement dans la page sans téléchargement
- **Workflow_Engine** : Service backend gérant la progression séquentielle des étapes (Step 0 → 3)
- **Liste_Fichiers** : Composant UI affichant les fichiers d'une étape avec leurs actions

## Exigences

### Exigence 1 : Affichage des fichiers par étape

**User Story :** En tant qu'expert, je veux voir les fichiers produits par chaque étape directement dans la page du dossier, afin de consulter rapidement les résultats sans naviguer vers chaque étape individuellement.

#### Critères d'acceptation

1. WHEN une étape possède des Fichier_Étape associés, THE Page_Dossier SHALL afficher une Liste_Fichiers dans la Section_Étape correspondante
2. THE Liste_Fichiers SHALL afficher pour chaque Fichier_Étape le nom du fichier, le type de fichier, la taille formatée en unités lisibles (Ko, Mo) et la date de création
3. WHEN une étape ne possède aucun Fichier_Étape, THE Section_Étape SHALL afficher le message « Aucun fichier produit »
4. THE Page_Étape SHALL également afficher la Liste_Fichiers complète de l'étape courante

### Exigence 2 : Ouverture et prévisualisation des fichiers

**User Story :** En tant qu'expert, je veux pouvoir ouvrir un fichier directement depuis la page pour le consulter sans le télécharger, afin de gagner du temps lors de la revue des résultats.

#### Critères d'acceptation

1. THE Liste_Fichiers SHALL afficher un bouton « Ouvrir » pour chaque Fichier_Étape
2. WHEN l'Expert clique sur « Ouvrir » pour un fichier de type Markdown, THE Application_Locale SHALL afficher une Prévisualisation_Inline du contenu Markdown dans la page courante
3. WHEN l'Expert clique sur « Ouvrir » pour un fichier de type PDF, THE Application_Locale SHALL ouvrir le fichier dans un nouvel onglet du navigateur
4. WHEN l'Expert clique sur « Ouvrir » pour un fichier de type Word (.docx), THE Application_Locale SHALL ouvrir le fichier dans un nouvel onglet du navigateur via une URL de téléchargement
5. IF le fichier demandé est introuvable sur le disque, THEN THE Application_Locale SHALL afficher un message d'erreur « Fichier introuvable »

### Exigence 3 : Téléchargement des fichiers

**User Story :** En tant qu'expert, je veux pouvoir télécharger un fichier produit par une étape pour l'étudier dans un outil externe, afin de travailler sur le document en dehors de l'application.

#### Critères d'acceptation

1. THE Liste_Fichiers SHALL afficher un bouton « Télécharger » pour chaque Fichier_Étape
2. WHEN l'Expert clique sur « Télécharger », THE Application_Locale SHALL déclencher le téléchargement du fichier avec son nom original comme nom de fichier
3. THE Application_Locale SHALL servir le fichier avec le Content-Type approprié (text/markdown, application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document)
4. IF le fichier demandé est introuvable sur le disque, THEN THE Application_Locale SHALL retourner une erreur HTTP 404 avec le message « Fichier introuvable sur le disque »

### Exigence 4 : Upload d'un fichier modifié par l'expert

**User Story :** En tant qu'expert, je veux pouvoir uploader une version modifiée d'un fichier produit par une étape, afin que mes corrections soient prises en compte dans les étapes suivantes du workflow.

#### Critères d'acceptation

1. WHILE une étape a le statut « réalisé » ou « initial » (non validée), THE Page_Étape SHALL afficher un bouton « Remplacer » à côté de chaque Fichier_Étape
2. WHEN l'Expert clique sur « Remplacer » et sélectionne un fichier, THE Application_Locale SHALL uploader le nouveau fichier et le stocker dans le répertoire de l'étape
3. WHEN un Fichier_Modifié est uploadé, THE Application_Locale SHALL conserver le Fichier_Original en le renommant avec le suffixe « _original » (ex : requisition_original.md) et stocker le Fichier_Modifié sous le nom original
4. WHEN un Fichier_Modifié est uploadé, THE Application_Locale SHALL mettre à jour l'entrée StepFile en base avec la nouvelle taille, le nouveau chemin et marquer le fichier comme modifié
5. WHILE une étape a le statut « valide » (verrouillée), THE Page_Étape SHALL masquer le bouton « Remplacer »
6. IF le fichier uploadé a une extension différente de celle du Fichier_Original, THEN THE Application_Locale SHALL rejeter l'upload avec le message « Le fichier doit avoir la même extension que l'original »

### Exigence 5 : Utilisation des fichiers modifiés dans les étapes suivantes

**User Story :** En tant qu'expert, je veux que les étapes suivantes utilisent automatiquement mes fichiers modifiés plutôt que les originaux, afin que mes corrections soient intégrées dans la suite du workflow.

#### Critères d'acceptation

1. WHEN le Step 1 lit le fichier Markdown du Step 0, THE Workflow_Engine SHALL utiliser le Fichier_Modifié si un Fichier_Modifié existe, sinon le Fichier_Original
2. WHEN le Step 3 lit les fichiers du Step 0 et du Step 2, THE Workflow_Engine SHALL utiliser le Fichier_Modifié si un Fichier_Modifié existe pour chaque fichier requis, sinon le Fichier_Original
3. THE Workflow_Engine SHALL résoudre le chemin du fichier actif (modifié ou original) via le champ file_path du StepFile en base de données

### Exigence 6 : Versionnage et traçabilité des modifications

**User Story :** En tant qu'expert, je veux savoir si un fichier a été modifié par rapport à la version originale, afin de garder une traçabilité de mes interventions sur les documents.

#### Critères d'acceptation

1. THE modèle StepFile SHALL inclure un champ booléen « is_modified » indiquant si le fichier a été remplacé par l'expert (valeur par défaut : false)
2. THE modèle StepFile SHALL inclure un champ optionnel « original_file_path » contenant le chemin vers le Fichier_Original lorsque le fichier a été modifié
3. WHEN un Fichier_Étape a le champ is_modified à true, THE Liste_Fichiers SHALL afficher un indicateur visuel « Modifié par l'expert » à côté du nom du fichier
4. WHEN un Fichier_Étape a le champ is_modified à true, THE Liste_Fichiers SHALL afficher la date de la dernière modification

### Exigence 7 : Endpoint API de téléchargement et de service des fichiers

**User Story :** En tant que développeur frontend, je veux un endpoint API unifié pour télécharger ou servir les fichiers d'une étape, afin de simplifier l'intégration côté client.

#### Critères d'acceptation

1. THE Application_Locale SHALL exposer un endpoint GET `/api/dossiers/{id}/steps/{step}/files/{file_id}/download` qui retourne le fichier en téléchargement (Content-Disposition: attachment)
2. THE Application_Locale SHALL exposer un endpoint GET `/api/dossiers/{id}/steps/{step}/files/{file_id}/view` qui retourne le fichier pour affichage inline (Content-Disposition: inline)
3. THE Application_Locale SHALL exposer un endpoint POST `/api/dossiers/{id}/steps/{step}/files/{file_id}/replace` qui accepte un fichier uploadé et remplace le Fichier_Étape existant
4. WHEN l'endpoint replace est appelé, THE Application_Locale SHALL vérifier que l'étape a le statut « réalisé » ou « initial » avant d'accepter le remplacement
5. IF l'étape a le statut « valide », THEN THE Application_Locale SHALL retourner une erreur HTTP 403 avec le message « Étape verrouillée — modification impossible »
