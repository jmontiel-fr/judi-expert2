# Document d'exigences — Gestion du Corpus Admin & Page Corpus Publique

## Introduction

Ce document décrit les exigences pour deux évolutions majeures du Site Central Judi-Expert :

1. **Page Corpus publique enrichie** : la page `/corpus` affiche actuellement les domaines et leurs versions de corpus (depuis la base de données), mais ne montre pas le contenu réel du corpus (documents PDF, URLs de référence). L'objectif est d'exposer le contenu détaillé de chaque domaine actif en lisant les fichiers `contenu.yaml` et `urls/urls.yaml` montés en volume.

2. **Refactoring de la page Admin** : remplacer la navigation par onglets actuelle par un menu horizontal avec quatre sections — Statistiques, Experts, News, Corpus — incluant une nouvelle section d'administration du corpus par domaine (consultation, upload de PDF, ajout d'URLs).

## Glossaire

- **Site_Central** : application web hébergée (FastAPI + Next.js) gérant l'inscription des experts, les paiements, la distribution du corpus et l'administration.
- **Page_Corpus** : page publique accessible à `/corpus` affichant les corpus par domaine d'expertise.
- **Page_Admin** : page protégée accessible à `/admin` réservée à l'administrateur du Site Central.
- **Menu_Admin** : barre de navigation horizontale de la Page_Admin contenant les sections Statistiques, Experts, News et Corpus.
- **Domaine** : spécialité d'expertise judiciaire (psychologie, psychiatrie, médecine légale, bâtiment, comptabilité) définie dans `domaines.yaml`.
- **Contenu_Corpus** : ensemble des ressources d'un domaine : documents PDF, URLs de référence et templates, décrits dans le fichier `contenu.yaml`.
- **URLs_Corpus** : liste des URLs publiques de référence d'un domaine, stockées dans `urls/urls.yaml`.
- **API_Corpus** : ensemble des endpoints FastAPI sous `/api/corpus` servant les données de corpus.
- **API_Admin_Corpus** : ensemble des endpoints FastAPI sous `/api/admin/corpus` permettant la gestion du corpus (upload, ajout d'URLs).
- **Administrateur** : expert authentifié dont l'email correspond à la variable d'environnement `ADMIN_EMAIL`.
- **Fichier_Contenu** : fichier `contenu.yaml` situé dans `corpus/{domaine}/` décrivant les ressources du corpus.
- **Fichier_URLs** : fichier `urls/urls.yaml` situé dans `corpus/{domaine}/urls/` listant les URLs de référence.

## Exigences

### Exigence 1 : Endpoint API de contenu du corpus par domaine

**User Story :** En tant que visiteur du Site Central, je veux consulter le contenu détaillé du corpus d'un domaine, afin de connaître les documents et URLs de référence disponibles.

#### Critères d'acceptation

1. WHEN un client appelle `GET /api/corpus/{domaine}/contenu`, THE API_Corpus SHALL lire le Fichier_Contenu du domaine demandé et retourner la liste des ressources au format JSON avec les champs `nom`, `description`, `type` et `date_ajout` pour chaque entrée.
2. WHEN un client appelle `GET /api/corpus/{domaine}/urls`, THE API_Corpus SHALL lire le Fichier_URLs du domaine demandé et retourner la liste des URLs au format JSON avec les champs `nom`, `url`, `description`, `type` et `date_ajout` pour chaque entrée.
3. IF le domaine demandé n'existe pas dans `domaines.yaml`, THEN THE API_Corpus SHALL retourner une erreur HTTP 404 avec le message « Domaine introuvable ».
4. IF le Fichier_Contenu ou le Fichier_URLs n'existe pas pour le domaine demandé, THEN THE API_Corpus SHALL retourner une liste vide.

### Exigence 2 : Page Corpus publique enrichie

**User Story :** En tant que visiteur du Site Central, je veux voir le contenu réel du corpus de chaque domaine actif (documents, URLs), afin de comprendre les ressources disponibles pour chaque spécialité.

#### Critères d'acceptation

1. WHEN un visiteur accède à la Page_Corpus, THE Page_Corpus SHALL afficher pour chaque domaine actif une section dépliable contenant la liste des documents et la liste des URLs de référence.
2. WHEN un domaine actif possède des documents dans son Contenu_Corpus, THE Page_Corpus SHALL afficher chaque document avec son nom, sa description et son type.
3. WHEN un domaine actif possède des URLs dans ses URLs_Corpus, THE Page_Corpus SHALL afficher chaque URL avec son nom, sa description et un lien cliquable vers l'URL.
4. WHILE un domaine est marqué comme inactif dans `domaines.yaml`, THE Page_Corpus SHALL afficher le domaine avec un badge « Inactif » et le message « Corpus en cours de préparation ».
5. WHILE les données du corpus sont en cours de chargement, THE Page_Corpus SHALL afficher un indicateur de chargement.

### Exigence 3 : Refactoring du menu de la Page Admin

**User Story :** En tant qu'administrateur, je veux naviguer entre les sections d'administration via un menu horizontal clair, afin d'accéder rapidement aux différentes fonctionnalités.

#### Critères d'acceptation

1. THE Menu_Admin SHALL afficher quatre éléments de navigation horizontaux dans l'ordre suivant : « Statistiques », « Experts », « News », « Corpus ».
2. WHEN l'Administrateur clique sur « Statistiques », THE Page_Admin SHALL afficher les statistiques de tickets par jour, mois courant et mois passés avec le filtre par domaine existant.
3. WHEN l'Administrateur clique sur « Experts », THE Page_Admin SHALL afficher la liste des experts avec un champ de recherche et le nombre total d'experts affiché à droite du champ de recherche.
4. WHEN l'Administrateur clique sur « News », THE Page_Admin SHALL naviguer vers la page `/admin/news` existante.
5. WHEN l'Administrateur clique sur « Corpus », THE Page_Admin SHALL afficher la section de gestion du corpus par domaine.
6. WHEN l'Administrateur saisit du texte dans le champ de recherche des experts, THE Page_Admin SHALL filtrer la liste des experts en temps réel par nom, prénom ou email.
7. THE Page_Admin SHALL afficher le nombre d'experts correspondant au filtre actif à droite du champ de recherche sous la forme « N expert(s) ».

### Exigence 4 : Section Admin Corpus — Consultation

**User Story :** En tant qu'administrateur, je veux consulter le contenu du corpus de chaque domaine depuis la Page Admin, afin de vérifier les ressources disponibles.

#### Critères d'acceptation

1. WHEN l'Administrateur accède à la section Corpus de la Page_Admin, THE Page_Admin SHALL afficher la liste des domaines avec leur statut (actif/inactif).
2. WHEN l'Administrateur sélectionne un domaine, THE Page_Admin SHALL afficher le contenu du corpus de ce domaine réparti en deux catégories : « Documents » et « URLs ».
3. WHEN un domaine possède des documents, THE Page_Admin SHALL afficher chaque document avec son nom, sa description, son type et sa date d'ajout.
4. WHEN un domaine possède des URLs, THE Page_Admin SHALL afficher chaque URL avec son nom, son URL cliquable, sa description, son type et sa date d'ajout.

### Exigence 5 : Section Admin Corpus — Upload de fichiers PDF

**User Story :** En tant qu'administrateur, je veux uploader des fichiers PDF dans le corpus d'un domaine, afin d'enrichir les ressources documentaires disponibles.

#### Critères d'acceptation

1. WHEN l'Administrateur sélectionne un domaine dans la section Corpus, THE Page_Admin SHALL afficher un bouton « Ajouter un document PDF ».
2. WHEN l'Administrateur clique sur « Ajouter un document PDF », THE Page_Admin SHALL ouvrir un sélecteur de fichier limité aux fichiers PDF.
3. WHEN l'Administrateur soumet un fichier PDF valide, THE API_Admin_Corpus SHALL enregistrer le fichier dans le répertoire `corpus/{domaine}/documents/` et mettre à jour le Fichier_Contenu avec les métadonnées du document.
4. IF le fichier soumis n'est pas un PDF valide, THEN THE API_Admin_Corpus SHALL retourner une erreur HTTP 400 avec le message « Seuls les fichiers PDF sont acceptés ».
5. IF un fichier portant le même nom existe déjà dans le répertoire du domaine, THEN THE API_Admin_Corpus SHALL retourner une erreur HTTP 409 avec le message « Un document portant ce nom existe déjà ».
6. WHEN l'upload est terminé avec succès, THE Page_Admin SHALL rafraîchir la liste des documents du domaine et afficher une notification de succès.

### Exigence 6 : Section Admin Corpus — Ajout d'URLs de PDF

**User Story :** En tant qu'administrateur, je veux ajouter des URLs pointant vers des PDF disponibles sur internet dans le corpus d'un domaine, afin de référencer des documents externes.

#### Critères d'acceptation

1. WHEN l'Administrateur sélectionne un domaine dans la section Corpus, THE Page_Admin SHALL afficher un bouton « Ajouter une URL de PDF ».
2. WHEN l'Administrateur clique sur « Ajouter une URL de PDF », THE Page_Admin SHALL afficher un formulaire avec les champs : nom (texte), URL (texte), description (texte).
3. WHEN l'Administrateur soumet le formulaire avec des données valides, THE API_Admin_Corpus SHALL ajouter l'entrée dans le Fichier_URLs du domaine avec le type « pdf_externe » et la date d'ajout courante.
4. IF le champ URL est vide ou ne commence pas par « http:// » ou « https:// », THEN THE Page_Admin SHALL afficher un message d'erreur de validation « L'URL doit commencer par http:// ou https:// ».
5. IF le champ nom est vide, THEN THE Page_Admin SHALL afficher un message d'erreur de validation « Le nom est obligatoire ».

### Exigence 7 : Section Admin Corpus — Ajout d'URLs de sites web à exploiter

**User Story :** En tant qu'administrateur, je veux ajouter des URLs de sites web à crawler/exploiter dans le corpus d'un domaine, afin d'enrichir les sources de données du RAG.

#### Critères d'acceptation

1. WHEN l'Administrateur sélectionne un domaine dans la section Corpus, THE Page_Admin SHALL afficher un bouton « Ajouter une URL de site web ».
2. WHEN l'Administrateur clique sur « Ajouter une URL de site web », THE Page_Admin SHALL afficher un formulaire avec les champs : nom (texte), URL (texte), description (texte).
3. WHEN l'Administrateur soumet le formulaire avec des données valides, THE API_Admin_Corpus SHALL ajouter l'entrée dans le Fichier_URLs du domaine avec le type « site_web » et la date d'ajout courante.
4. IF le champ URL est vide ou ne commence pas par « http:// » ou « https:// », THEN THE Page_Admin SHALL afficher un message d'erreur de validation « L'URL doit commencer par http:// ou https:// ».
5. IF le champ nom est vide, THEN THE Page_Admin SHALL afficher un message d'erreur de validation « Le nom est obligatoire ».

### Exigence 8 : Sécurité des endpoints Admin Corpus

**User Story :** En tant qu'administrateur, je veux que les opérations de gestion du corpus soient protégées, afin que seul l'administrateur puisse modifier le corpus.

#### Critères d'acceptation

1. THE API_Admin_Corpus SHALL exiger un token d'authentification valide pour tous les endpoints de gestion du corpus.
2. IF l'utilisateur authentifié n'est pas l'Administrateur, THEN THE API_Admin_Corpus SHALL retourner une erreur HTTP 403 avec le message « Accès réservé à l'administrateur ».
3. THE API_Corpus SHALL permettre l'accès en lecture aux endpoints `GET /api/corpus/{domaine}/contenu` et `GET /api/corpus/{domaine}/urls` sans authentification.

### Exigence 9 : Montage des volumes en écriture pour le corpus

**User Story :** En tant qu'administrateur, je veux que le backend puisse écrire dans les répertoires du corpus, afin de permettre l'upload de fichiers et la mise à jour des fichiers YAML.

#### Critères d'acceptation

1. WHEN le backend est déployé en mode développement, THE Site_Central SHALL monter le volume `corpus` en lecture-écriture (retirer le flag `:ro`) dans `docker-compose.dev.yml`.
2. THE Site_Central SHALL conserver le montage du volume `domaines` en lecture seule (`:ro`).
