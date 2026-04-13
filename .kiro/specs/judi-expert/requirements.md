# Document d'Exigences — Judi-Expert

## Introduction

Judi-Expert est une solution d'assistance aux experts judiciaires multi-domaines (santé, bâtiment, comptabilité, informatique, cybersécurité, etc.). Le système se compose de deux parties principales : une application web locale installée sur le PC de l'expert et un site central déployé sur AWS. L'application locale gère le workflow d'expertise en 4 étapes (extraction, plan d'entretien, collecte de données, génération de rapport final) en s'appuyant sur un LLM et une base RAG spécifique au domaine. Le site central gère l'inscription des experts, la distribution des modules domaine, la vente de tickets d'expertise et la documentation légale. Toutes les données d'expertise restent exclusivement sur le PC de l'expert.

## Glossaire

- **Application_Locale** : Application web PWA (React/Next.js + Python) installée sur le PC de l'expert, fonctionnant via des conteneurs Docker
- **Site_Central** : Application web PWA (React/Next.js + Python) déployée sur AWS, gérant inscriptions, téléchargements et tickets
- **Expert** : Utilisateur principal du système, expert judiciaire inscrit et authentifié
- **Administrateur** : Compte unique d'administration du Site_Central (admin@judi-expert.fr)
- **Dossier** : Unité de travail représentant une mission d'expertise, contenant les étapes Step0 à Step3
- **Ticket** : Fichier électronique à usage unique acheté sur le Site_Central, nécessaire pour créer un Dossier
- **Step0_Extraction** : Étape de conversion d'un document PDF-scan de réquisition en fichier Markdown
- **Step1_PEMEC** : Étape de génération du plan d'entretien (QMEC) à partir de la réquisition tribunal (QT) et de la trame d'entretien configurée
- **Step2_Upload** : Étape de collecte des notes d'entretien (NE) et du rapport d'expertise brut (REB) produits par l'expert hors application
- **Step3_REF** : Étape de génération du rapport d'expertise final (REF) et du rapport auxiliaire (RAUX)
- **QT** : Questions du tribunal auxquelles l'expertise doit répondre, extraites de la réquisition
- **QMEC** : Plan d'entretien généré, comprenant la trame et des suggestions de questions
- **NE** : Notes d'entretien sous forme télégraphique rédigées par l'expert
- **REB** : Rapport d'expertise brut contenant les réponses argumentées aux QT sur la base des NE
- **REF** : Rapport d'expertise final généré par le système à partir du REB, des QT et des NE
- **RAUX** : Rapport auxiliaire comprenant une analyse de contestations possibles (Partie 1) et une version révisée du REF (Partie 2)
- **RAG** : Base de données vectorielle Qdrant contenant le corpus du domaine d'expertise
- **LLM** : Modèle de langage local utilisé pour le traitement et la génération de texte
- **Corpus_Domaine** : Ensemble de documents et URLs spécifiques à un domaine d'expertise, stockés dans la base RAG
- **TPE** : Template du plan d'entretien fourni par l'expert lors de la configuration
- **Template_Rapport** : Template Word du rapport final fourni par l'expert lors de la configuration
- **Domaine** : Spécialité d'expertise (psychologie, psychiatrie, médecine légale, bâtiment, comptabilité)
- **ChatBot** : Assistant conversationnel intégré à l'Application_Locale utilisant le LLM et la base RAG
- **Stripe** : Solution de paiement en ligne utilisée pour l'achat de Tickets
- **SQLAlchemy** : ORM Python utilisé pour la gestion de la base de données relationnelle
- **Alembic** : Outil de migration de schéma de base de données utilisé avec SQLAlchemy
- **Qdrant** : Base de données vectorielle open-source utilisée pour le stockage RAG
- **Programme_Installation** : Script d'installation de l'Application_Locale sur le PC de l'expert
- **Amorce** : Programme de lancement qui démarre le runtime Docker avant l'Application_Locale

## Exigences

### Exigence 1 : Installation de l'application locale

**User Story :** En tant qu'Expert, je veux installer l'application locale sur mon PC, afin de disposer de l'environnement d'expertise complet.

#### Critères d'acceptation

1. WHEN l'Expert lance le Programme_Installation, THE Programme_Installation SHALL vérifier que le PC satisfait les conditions requises minimales en CPU, RAM, espace disque et chiffrement du disque
2. IF le PC ne satisfait pas les conditions requises minimales, THEN THE Programme_Installation SHALL afficher un message d'erreur détaillant chaque condition non remplie et interrompre l'installation
3. WHEN les conditions requises sont satisfaites, THE Programme_Installation SHALL installer tous les composants système nécessaires, incluant le runtime Docker gratuit
4. WHEN l'installation est terminée, THE Application_Locale SHALL être lançable comme une application standard via l'Amorce
5. WHEN l'Expert lance l'Application_Locale, THE Amorce SHALL démarrer le runtime Docker avant de lancer les conteneurs de l'Application_Locale


### Exigence 2 : Architecture conteneurisée locale

**User Story :** En tant qu'Expert, je veux que l'application locale fonctionne avec des conteneurs Docker isolés, afin de garantir la portabilité et la simplicité de déploiement.

#### Critères d'acceptation

1. THE Application_Locale SHALL fonctionner avec au minimum 4 images Docker : le site web local avec la BD locale, le LLM, la base RAG avec le Corpus_Domaine, et un conteneur supplémentaire selon les besoins
2. WHEN l'Amorce démarre l'Application_Locale, THE Amorce SHALL orchestrer le démarrage de tous les conteneurs Docker dans l'ordre requis
3. THE Application_Locale SHALL utiliser exclusivement des composants sous licences gratuites et compatibles avec un usage commercial

### Exigence 3 : Configuration initiale de l'application locale

**User Story :** En tant qu'Expert, je veux configurer mon application locale au premier lancement, afin de personnaliser l'environnement pour mon domaine d'expertise.

#### Critères d'acceptation

1. WHEN l'Expert lance l'Application_Locale pour la première fois, THE Application_Locale SHALL exiger la définition d'un mot de passe local et la sélection d'un Domaine d'expertise
2. WHILE l'image RAG est absente, THE Application_Locale SHALL afficher la configuration comme obligatoire et bloquer l'accès aux fonctionnalités d'expertise
3. WHEN l'Expert accède au menu de configuration, THE Application_Locale SHALL afficher la liste des versions du module RAG disponibles sur le Site_Central pour le Domaine sélectionné
4. WHEN l'Expert sélectionne une version du module RAG, THE Application_Locale SHALL télécharger l'image RAG correspondante depuis le Site_Central et la démarrer
5. WHEN l'Expert soumet le fichier TPE et le Template_Rapport en format Word, THE Application_Locale SHALL enrichir la base RAG avec ces éléments
6. WHEN l'Expert consulte les documents chargés, THE Application_Locale SHALL afficher la liste des documents présents dans la base RAG
7. WHEN l'Expert remplace le TPE ou le Template_Rapport, THE Application_Locale SHALL mettre à jour la base RAG avec les nouveaux fichiers

### Exigence 4 : Remplacement de version du module RAG

**User Story :** En tant qu'Expert, je veux pouvoir changer la version du module RAG à tout moment, afin de bénéficier des mises à jour du corpus de mon domaine.

#### Critères d'acceptation

1. WHEN l'Expert sélectionne une nouvelle version du module RAG dans le menu de configuration, THE Application_Locale SHALL télécharger et remplacer l'image RAG existante par la nouvelle version
2. WHEN l'Expert consulte les versions disponibles, THE Application_Locale SHALL afficher le contenu détaillé de chaque version du module mis à disposition sur le Site_Central

### Exigence 5 : Gestion des dossiers d'expertise

**User Story :** En tant qu'Expert, je veux créer et gérer mes dossiers d'expertise, afin de suivre l'avancement de chaque mission.

#### Critères d'acceptation

1. WHEN l'Expert crée un nouveau Dossier, THE Application_Locale SHALL exiger un nom de dossier et un Ticket valide
2. WHEN l'Expert soumet un Ticket pour la création d'un Dossier, THE Application_Locale SHALL transmettre le Ticket au Site_Central pour vérification
3. WHEN le Site_Central valide le Ticket, THE Site_Central SHALL marquer le Ticket comme utilisé dans sa base de données
4. IF le Ticket est invalide ou déjà utilisé, THEN THE Application_Locale SHALL afficher un message d'erreur indiquant la raison du rejet (invalide ou déjà utilisé)
5. WHEN le Ticket est validé, THE Application_Locale SHALL créer le Dossier et l'ajouter à la liste des dossiers
6. THE Application_Locale SHALL afficher la liste des Dossiers dans l'ordre chronologique inverse, le plus récent en premier
7. WHEN l'Expert sélectionne un Dossier, THE Application_Locale SHALL afficher les étapes Step0_Extraction, Step1_PEMEC, Step2_Upload et Step3_REF avec leur état respectif (initial, réalisé, validé) et un lien pour accéder à chaque étape


### Exigence 6 : Step0 — Extraction de la réquisition

**User Story :** En tant qu'Expert, je veux convertir la réquisition PDF-scan en format Markdown, afin de disposer d'un texte exploitable et modifiable.

#### Critères d'acceptation

1. WHEN l'Expert introduit un fichier PDF-scan de réquisition, THE Application_Locale SHALL afficher un bouton "Extraction"
2. WHEN l'Expert clique sur le bouton "Extraction", THE Application_Locale SHALL lancer le processus de conversion du PDF-scan en fichier Markdown en utilisant un moteur OCR open-source (Tesseract OCR ou équivalent gratuit) pour l'extraction du texte depuis les images scannées
3. THE Application_Locale SHALL supporter les PDF-scan contenant des pages numérisées en image (JPEG, PNG, TIFF) et les PDF contenant déjà du texte extractible
4. THE Application_Locale SHALL utiliser le LLM local pour structurer le texte brut extrait par l'OCR en format Markdown propre, en identifiant les sections, les questions du tribunal (QT) et les informations du destinataire
5. WHEN la conversion est terminée, THE Application_Locale SHALL afficher un bouton "Visualiser" et indiquer l'emplacement du fichier Markdown généré
6. WHEN l'Expert clique sur le bouton "Visualiser", THE Application_Locale SHALL afficher le contenu du fichier Markdown généré
7. THE Application_Locale SHALL permettre à l'Expert de modifier manuellement le fichier Markdown généré à l'emplacement indiqué
8. THE moteur OCR utilisé SHALL être intégré dans l'un des conteneurs Docker de l'Application_Locale et fonctionner entièrement en local sans appel à un service cloud

### Exigence 7 : Step1 — Génération du plan d'entretien (PEMEC)

**User Story :** En tant qu'Expert, je veux obtenir un plan d'entretien structuré à partir de la réquisition tribunal, afin de préparer mes entretiens de manière méthodique.

#### Critères d'acceptation

1. WHEN l'Expert accède au Step1_PEMEC, THE Application_Locale SHALL afficher le statut "initial" et un bouton "Execute"
2. WHEN l'Expert clique sur le bouton "Execute", THE Application_Locale SHALL générer le QMEC en utilisant les QT extraites de la réquisition et la trame d'entretien TPE configurée par l'Expert
3. WHEN la génération du QMEC est terminée, THE Application_Locale SHALL actualiser le statut à "réalisé", afficher un bouton "Download" pour télécharger le QMEC et un bouton "Valider"
4. WHEN l'Expert clique sur le bouton "Valider" du Step1_PEMEC, THE Application_Locale SHALL verrouiller le Step1_PEMEC et autoriser l'accès au Step2_Upload

### Exigence 8 : Step2 — Collecte des notes et du rapport brut

**User Story :** En tant qu'Expert, je veux soumettre mes notes d'entretien et mon rapport brut, afin que le système puisse générer le rapport final.

#### Critères d'acceptation

1. WHEN l'Expert accède au Step2_Upload, THE Application_Locale SHALL afficher le statut "initial" et permettre le téléversement des fichiers NE et REB au format .docx
2. WHEN l'Expert téléverse les fichiers NE et REB, THE Application_Locale SHALL valider que les fichiers sont au format .docx et les stocker dans le Dossier correspondant
3. IF l'Expert téléverse un fichier dans un format autre que .docx, THEN THE Application_Locale SHALL afficher un message d'erreur indiquant que seul le format .docx est accepté
4. WHEN l'Expert clique sur le bouton "Valider" du Step2_Upload, THE Application_Locale SHALL verrouiller le Step2_Upload et autoriser l'accès au Step3_REF

### Exigence 9 : Step3 — Génération du rapport final et du rapport auxiliaire

**User Story :** En tant qu'Expert, je veux obtenir un rapport d'expertise final et une analyse auxiliaire, afin de produire un rapport de qualité professionnelle.

#### Critères d'acceptation

1. WHEN l'Expert accède au Step3_REF, THE Application_Locale SHALL afficher le statut "initial" et un bouton "Execute"
2. WHEN l'Expert clique sur le bouton "Execute", THE Application_Locale SHALL générer le REF en utilisant le REB, les QT, les NE et le Template_Rapport
3. WHEN l'Expert clique sur le bouton "Execute", THE Application_Locale SHALL générer le RAUX comprenant deux parties : la Partie 1 analysant les contestations possibles du REF sur la base du Corpus_Domaine, et la Partie 2 proposant une version révisée du REF tenant compte de la Partie 1
4. WHEN la génération est terminée, THE Application_Locale SHALL actualiser le statut à "réalisé", afficher les boutons "Download" pour le REF et le RAUX, et un bouton "Valider"
5. WHEN l'Expert clique sur le bouton "Valider" du Step3_REF, THE Application_Locale SHALL verrouiller définitivement le Dossier, empêchant toute exécution ou retour en arrière
6. WHEN le Step3_REF est validé, THE Application_Locale SHALL archiver le Dossier complet avec tous les fichiers intermédiaires finalisés dans un fichier ZIP

### Exigence 10 : Workflow séquentiel des étapes

**User Story :** En tant qu'Expert, je veux que les étapes du dossier suivent un ordre séquentiel strict, afin de garantir l'intégrité du processus d'expertise.

#### Critères d'acceptation

1. THE Application_Locale SHALL imposer l'ordre séquentiel Step0_Extraction, Step1_PEMEC, Step2_Upload, Step3_REF pour chaque Dossier
2. WHILE une étape a le statut "initial" ou "réalisé", THE Application_Locale SHALL interdire l'accès aux étapes suivantes
3. WHEN une étape passe au statut "validé", THE Application_Locale SHALL autoriser l'accès à l'étape suivante uniquement
4. WHILE une étape a le statut "validé", THE Application_Locale SHALL interdire toute modification de cette étape


### Exigence 11 : ChatBot intégré

**User Story :** En tant qu'Expert, je veux disposer d'un assistant conversationnel intégré, afin d'obtenir des réponses rapides sur l'utilisation du système et le contenu du domaine.

#### Critères d'acceptation

1. THE Application_Locale SHALL intégrer un ChatBot accessible depuis l'interface principale
2. THE ChatBot SHALL utiliser le LLM local avec la base RAG enrichie du contenu du site, des mentions légales, des CGU et du fichier user-guide.md
3. WHEN l'Expert pose une question au ChatBot, THE ChatBot SHALL fournir une réponse basée sur le Corpus_Domaine et la documentation du système

### Exigence 12 : Interface de l'application locale

**User Story :** En tant qu'Expert, je veux une interface professionnelle et intuitive, afin de travailler efficacement sur mes dossiers d'expertise.

#### Critères d'acceptation

1. THE Application_Locale SHALL présenter une charte graphique professionnelle, soignée et attractive en tant que PWA React/Next.js
2. THE Application_Locale SHALL afficher la page d'accueil directement sur la liste des Dossiers
3. THE Application_Locale SHALL afficher un header contenant un menu avec les entrées : Logo "Judi-expert Local" (texte), Dossiers, Configuration, Site_Central (lien externe), FAQ (lien externe)
4. THE Application_Locale SHALL afficher un footer contenant : "copyright ItechSource 2026", un lien externe CHU, un lien Mentions légales, un lien externe CGU, un lien externe Contact

### Exigence 13 : Inscription sur le site central

**User Story :** En tant qu'Expert, je veux m'inscrire sur le site central, afin de pouvoir télécharger l'application et acheter des tickets d'expertise.

#### Critères d'acceptation

1. WHEN l'Expert accède à la page /inscription, THE Site_Central SHALL afficher un formulaire contenant les champs : Nom, Prénom, adresse, Domaine d'expertise (menu déroulant)
2. THE Site_Central SHALL utiliser AWS Cognito pour la gestion de l'authentification des Experts
3. THE Site_Central SHALL afficher les cases à cocher obligatoires : acceptation des Mentions légales, acceptation des CGU, engagement de responsabilité de protection des données PC (BitLocker ou équivalent)
4. THE Site_Central SHALL afficher une case à cocher optionnelle : acceptation des emails et newsletter
5. WHEN l'Expert soumet le formulaire d'inscription avec tous les champs obligatoires remplis et les cases obligatoires cochées, THE Site_Central SHALL créer le compte Expert

### Exigence 14 : Connexion au site central

**User Story :** En tant qu'Expert, je veux me connecter au site central de manière sécurisée, afin d'accéder à mes services.

#### Critères d'acceptation

1. WHEN l'Expert accède à la page /connexion, THE Site_Central SHALL afficher un formulaire contenant les champs email et mot de passe, ainsi qu'un Captcha Google V2
2. WHEN l'Expert soumet des identifiants valides avec un Captcha résolu, THE Site_Central SHALL authentifier l'Expert et rediriger vers la page d'accueil
3. IF l'Expert soumet des identifiants invalides, THEN THE Site_Central SHALL afficher un message d'erreur sans révéler si l'email ou le mot de passe est incorrect

### Exigence 15 : Achat de tickets d'expertise

**User Story :** En tant qu'Expert, je veux acheter des tickets d'expertise en ligne, afin de pouvoir créer de nouveaux dossiers d'expertise.

#### Critères d'acceptation

1. WHILE l'Expert est connecté au Site_Central, THE Site_Central SHALL permettre l'achat de Tickets via la solution de paiement Stripe
2. WHEN le paiement Stripe est confirmé, THE Site_Central SHALL générer un Ticket à usage unique contenant le Domaine déclaré par l'Expert
3. WHEN le Ticket est généré, THE Site_Central SHALL transmettre le Ticket par email à l'Expert
4. WHEN l'Application_Locale soumet un Ticket pour vérification, THE Site_Central SHALL valider le Ticket et le marquer comme utilisé dans la base de données, ou retourner une erreur si le Ticket est invalide ou déjà utilisé

### Exigence 16 : Page d'accueil du site central

**User Story :** En tant que visiteur, je veux comprendre le service Judi-Expert dès la page d'accueil, afin de décider si la solution répond à mes besoins.

#### Critères d'acceptation

1. THE Site_Central SHALL afficher une section d'accueil contenant : une image libre de droits représentant un avocat ou un juge, le message principal "Réduisez de 50% votre temps de production des dossiers d'expertise avec l'IA", les messages complémentaires sur la qualité, le RGPD et l'AI Act, et une mention visible indiquant "Le site est ouvert pendant les horaires bureau de 8h à 20h"
2. THE Site_Central SHALL afficher la liste des domaines couverts : Santé (psychologie, psychiatrie, médecine légale), Bâtiment, Comptabilité
3. THE Site_Central SHALL afficher une section "Comment ça marche ?" décrivant le workflow d'inscription, téléchargement, configuration et achat de tickets, et précisant que toutes les données d'expertise restent sur le PC de l'Expert
4. THE Site_Central SHALL afficher une section présentant le workflow d'expertise avec un schéma illustrant les étapes Step0, Step1, Step3 pour un exemple de cas en psychologie
5. THE Site_Central SHALL afficher une section sur la conformité réglementaire AI Act


### Exigence 17 : Interface du site central

**User Story :** En tant que visiteur ou Expert, je veux naviguer facilement sur le site central, afin d'accéder rapidement aux fonctionnalités souhaitées.

#### Critères d'acceptation

1. THE Site_Central SHALL présenter une charte graphique professionnelle, soignée et attractive en tant que PWA React/Next.js
2. THE Site_Central SHALL afficher un header contenant : Logo "Judi-expert", Corpus, FAQ, Connexion/Inscription
3. WHILE l'Expert est connecté, THE Site_Central SHALL afficher l'entrée "Mon Espace" dans le header en remplacement de Connexion/Inscription
4. THE Site_Central SHALL afficher un footer contenant : "copyright ITechSource 2026", Mentions légales, CGU, FAQ, Contact

### Exigence 18 : Pages du site central

**User Story :** En tant qu'Expert connecté, je veux accéder à mes informations personnelles et à mes tickets, afin de gérer mon compte et mes achats.

#### Critères d'acceptation

1. WHEN l'Expert accède à la page /downloads, THE Site_Central SHALL mettre à disposition le package de l'Application_Locale souche à télécharger
2. WHEN l'Expert accède à la page /corpus, THE Site_Central SHALL afficher les divers corpus par Domaine avec leur version et le contenu détaillé de chaque version
3. WHEN l'Expert accède à la page /contact, THE Site_Central SHALL afficher un formulaire avec une sélection de Domaine (liste déroulante incluant les domaines et "général") et un objet (liste déroulante : Problème, Demande d'amélioration, Autre)
4. WHEN l'Expert accède à la page /monespace, THE Site_Central SHALL afficher une liste d'onglets pour naviguer dans les sous-pages
5. WHEN l'Expert accède à la page /monespace/profil, THE Site_Central SHALL afficher les paramètres d'inscription, permettre le changement de mot de passe et la suppression de compte
6. WHEN l'Expert accède à la page /monespace/tickets, THE Site_Central SHALL afficher la liste des Tickets achetés avec les dates et montants

### Exigence 19 : Administration du site central

**User Story :** En tant qu'Administrateur, je veux gérer les experts inscrits et consulter les statistiques de vente, afin de piloter l'activité du service.

#### Critères d'acceptation

1. THE Site_Central SHALL disposer d'un compte Administrateur prédéfini (admin@judi-expert.fr) avec le mot de passe "change-me" au déploiement initial sur AWS
2. WHILE l'Administrateur est connecté, THE Site_Central SHALL afficher une entrée "Administration" dans le header
3. WHEN l'Administrateur accède à l'onglet "Experts" de la page d'administration, THE Site_Central SHALL afficher la liste des Experts inscrits avec leur Domaine d'expertise et leur date d'inscription
4. WHEN l'Administrateur accède à l'onglet "Statistiques tickets", THE Site_Central SHALL afficher un filtre par Domaine (liste déroulante incluant "Tous") et la liste des achats de Tickets pour la sélection sur le jour actuel, le mois courant et les mois passés depuis la création

### Exigence 20 : Documentation légale

**User Story :** En tant que visiteur ou Expert, je veux consulter les documents légaux, afin de connaître les conditions d'utilisation et les obligations légales.

#### Critères d'acceptation

1. THE Site_Central SHALL fournir les pages Mentions légales, CGU, FAQ et Politique de confidentialité accessibles depuis le footer
2. THE Application_Locale SHALL contenir des liens vers les pages Mentions légales, CGU et FAQ du Site_Central
3. THE Site_Central SHALL mettre à disposition le document methodologie.md en format PDF téléchargeable sur la page /downloads

### Exigence 21 : Document de méthodologie

**User Story :** En tant qu'Expert, je veux disposer d'un document de méthodologie, afin de justifier l'usage de l'IA dans mes rapports d'expertise auprès des instances judiciaires.

#### Critères d'acceptation

1. THE Site_Central SHALL fournir un document methodologie.md présentant la solution, son usage et sa conformité aux exigences réglementaires
2. THE Document methodologie.md SHALL mentionner explicitement l'usage de l'IA comme assistant à l'Expert selon la méthodologie définie
3. THE Document methodologie.md SHALL rappeler en introduction les autorisations des experts judiciaires en matière de rédaction de rapports en citant les sources juridiques applicables


### Exigence 22 : Gestion des domaines

**User Story :** En tant qu'Administrateur, je veux gérer les domaines d'expertise disponibles, afin de contrôler les spécialités proposées par le service.

#### Critères d'acceptation

1. THE Site_Central SHALL lire la configuration des domaines depuis un fichier domaines.yaml situé dans le répertoire domaines/ du dépôt
2. THE fichier domaines.yaml SHALL contenir pour chaque domaine : nom, répertoire, corpus/documents, corpus/urls et un indicateur actif (booléen True/False)
3. THE Site_Central SHALL proposer au départ 5 domaines : psychologie, psychiatrie, médecine_légale, bâtiment, comptabilité
4. THE Domaine psychologie SHALL être le seul domaine complété avec des fichiers dans corpus/documents/ et corpus/urls/

### Exigence 23 : Création du corpus du domaine psychologie

**User Story :** En tant que développeur, je veux que le corpus du domaine psychologie soit créé avec des documents PDF publics et des URLs publiques de référence, afin que le RAG dispose d'une base de connaissances opérationnelle dès le premier déploiement.

#### Critères d'acceptation

1. THE répertoire corpus/psychologie/documents/ SHALL contenir des documents PDF publics de référence en expertise psychologique judiciaire, incluant au minimum : des guides méthodologiques d'expertise psychologique, des textes réglementaires encadrant l'expertise judiciaire en psychologie, et des référentiels de bonnes pratiques
2. THE répertoire corpus/psychologie/urls/ SHALL contenir un fichier urls.yaml listant des URLs publiques de référence en expertise psychologique judiciaire, incluant au minimum : des sites institutionnels (ministère de la Justice, HAS, ordres professionnels), des bases documentaires juridiques publiques et des ressources académiques en psychologie légale
3. THE fichier corpus/psychologie/contenu.yaml SHALL décrire le contenu du corpus avec pour chaque entrée : le nom du document ou de l'URL, une description, le type (document ou url), et la date d'ajout
4. FOR ALL documents PDF inclus dans corpus/psychologie/documents/, THE document SHALL être un document public librement accessible et redistribuable
5. FOR ALL URLs listées dans corpus/psychologie/urls/, THE URL SHALL pointer vers une ressource publique accessible sans authentification

### Exigence 24 : Fichiers exemples du domaine psychologie

**User Story :** En tant qu'Expert psychologue, je veux disposer d'un TPE (trame d'entretien) et d'un template de rapport d'expertise par défaut pour le domaine psychologie, afin de pouvoir démarrer immédiatement sans créer ces fichiers de zéro.

#### Critères d'acceptation

1. THE répertoire corpus/psychologie/ SHALL contenir un fichier TPE par défaut (TPE_psychologie.tpl) structuré selon les bonnes pratiques de l'expertise psychologique judiciaire, incluant les sections : identification, motif de l'expertise, anamnèse, examen clinique, tests psychométriques, analyse et conclusions
2. THE répertoire corpus/psychologie/ SHALL contenir un fichier template de rapport d'expertise par défaut (template_rapport_psychologie.docx) au format Word, structuré selon les normes de rédaction des rapports d'expertise judiciaire
3. THE template_rapport_psychologie.docx SHALL contenir des champs de fusion (placeholders) pour : les informations du destinataire extraites du document QT, les questions du tribunal (QT), les réponses argumentées, l'analyse et les conclusions
4. THE template_rapport_psychologie.docx SHALL ne pas contenir l'identité du destinataire en dur ; cette identité SHALL être extraite automatiquement du document QT lors de la génération du rapport final (REF)
5. THE TPE_psychologie.tpl SHALL proposer pour chaque section une liste de questions types adaptables au contexte de chaque expertise
6. THE Application_Locale SHALL proposer les fichiers exemples du domaine psychologie comme valeurs par défaut lors de la configuration initiale (Exigence 3), tout en permettant à l'Expert de les remplacer par ses propres fichiers

### Exigence 25 : Déploiement du site central

**User Story :** En tant qu'Administrateur, je veux déployer le site central en local pour les tests et sur AWS en production, afin de garantir la qualité avant mise en production.

#### Critères d'acceptation

1. THE Site_Central SHALL être conteneurisé et déployable en environnement local pour les tests
2. THE Site_Central SHALL être déployable sur AWS en environnement de production
3. THE Site_Central SHALL utiliser Terraform pour la gestion de l'infrastructure AWS

### Exigence 26 : Stack technique

**User Story :** En tant que développeur, je veux utiliser une stack technique cohérente et open-source, afin de garantir la maintenabilité et la conformité des licences.

#### Critères d'acceptation

1. THE Application_Locale SHALL utiliser Python pour le backend et React/Next.js pour le frontend PWA
2. THE Site_Central SHALL utiliser Python pour le backend et React/Next.js pour le frontend PWA
3. THE Application_Locale SHALL utiliser SQLAlchemy comme ORM et Alembic pour les migrations de base de données
4. THE Site_Central SHALL utiliser SQLAlchemy comme ORM et Alembic pour les migrations de base de données
5. THE Application_Locale SHALL utiliser Qdrant comme base de données vectorielle pour le stockage RAG
6. THE Site_Central SHALL utiliser Stripe comme solution de paiement pour l'achat de Tickets
7. THE Application_Locale SHALL utiliser exclusivement des composants sous licences gratuites et compatibles avec un usage commercial
8. THE Site_Central SHALL utiliser exclusivement des composants sous licences gratuites et compatibles avec un usage commercial

### Exigence 27 : Conformité open-source et gratuité des composants

**User Story :** En tant que porteur de projet, je veux que tous les outils, bibliothèques et dépendances utilisés dans le projet soient open-source ou gratuits, afin de garantir l'absence de coûts de licence et la liberté d'usage commercial.

#### Critères d'acceptation

1. FOR ALL outils, bibliothèques, frameworks, runtimes et dépendances utilisés dans le projet (Application_Locale, Site_Central, scripts, packaging, infrastructure), THE projet SHALL utiliser exclusivement des composants sous licence open-source ou gratuite compatible avec un usage commercial
2. THE projet SHALL maintenir dans docs/licences.md un inventaire de toutes les dépendances avec leur nom, version, licence et URL du projet source
3. IF un composant ne dispose pas d'une licence open-source ou gratuite compatible avec un usage commercial, THEN THE composant SHALL être remplacé par une alternative conforme avant intégration dans le projet
4. THE contrainte de gratuité SHALL s'appliquer également aux outils de développement, de test, de build, de packaging et de déploiement utilisés dans le projet

### Exigence 28 : Organisation du dépôt

**User Story :** En tant que développeur, je veux une organisation claire du dépôt de code, afin de faciliter le développement et la maintenance.

#### Critères d'acceptation

1. THE dépôt judi-expert SHALL contenir un répertoire docs/ avec les documents en français en format Markdown : architecture, développement, exploitation, stripe, CGU, mentions_légales, user-guide
2. THE dépôt judi-expert SHALL contenir un répertoire corpus/ avec un sous-répertoire par Domaine contenant un fichier contenu.yaml
3. THE dépôt judi-expert SHALL contenir un répertoire site-central/local/ avec les sous-répertoires : scripts/ (scripts bash ou Python de gestion), web/, rag/, et un fichier .env
4. THE dépôt judi-expert SHALL contenir un répertoire site-central/aws/ avec les sous-répertoires : terraform/, scripts/ (build, deploy), web/, app_locale_package/, et un fichier .env

### Exigence 29 : Génération de la documentation projet

**User Story :** En tant que développeur, je veux que tous les documents de référence du projet soient générés dans le répertoire docs/, afin de disposer d'une documentation complète et à jour dès le déploiement.

#### Critères d'acceptation

1. THE dépôt judi-expert SHALL générer dans docs/ les fichiers Markdown suivants en français : architecture.md, developpement.md, exploitation.md, stripe.md, cgu.md, mentions_legales.md, user-guide.md, politique_confidentialite.md, faq.md, cout-aws.md
2. THE fichier docs/architecture.md SHALL décrire l'architecture globale du système (Application_Locale, Site_Central, ECR, conteneurs Docker, flux de données)
3. THE fichier docs/developpement.md SHALL décrire les procédures de développement, les prérequis, la configuration de l'environnement de développement et les conventions de code
4. THE fichier docs/exploitation.md SHALL décrire les procédures d'exploitation : démarrage, arrêt, redémarrage, surveillance, sauvegarde et mise à jour des composants
5. THE fichier docs/stripe.md SHALL décrire l'intégration Stripe : configuration des clés API, flux de paiement, gestion des webhooks et procédures de test
6. THE fichier docs/user-guide.md SHALL décrire le guide utilisateur complet de l'Application_Locale destiné aux Experts
7. THE fichier docs/methodologie.md SHALL être généré conformément à l'Exigence 21
8. THE fichier docs/cout-aws.md SHALL décrire l'estimation des coûts AWS mensuels par service, les scénarios de dimensionnement, le mode heures ouvrables (8h-20h) et les optimisations possibles

### Exigence 30 : Scripts de build, déploiement et gestion des images

**User Story :** En tant que développeur ou administrateur, je veux disposer de scripts de build, de contrôle et de déploiement, afin d'automatiser la gestion des images Docker et le déploiement local et AWS.

#### Critères d'acceptation

1. THE répertoire site-central/local/scripts/ SHALL contenir des scripts bash ou Python pour : le build des images Docker locales, le démarrage (start), l'arrêt (stop) et le redémarrage (restart) de l'ensemble des conteneurs de l'Application_Locale
2. THE répertoire site-central/aws/scripts/ SHALL contenir des scripts bash ou Python pour : le build des images Docker de production, le push des images vers le dépôt ECR, et le déploiement de l'infrastructure et des services sur AWS
3. WHEN un développeur exécute le script de build local, THE script SHALL construire toutes les images Docker nécessaires à l'Application_Locale (site web local, BD locale, LLM, RAG)
4. WHEN un développeur exécute le script de build AWS, THE script SHALL construire les images Docker de production du Site_Central et les pousser vers le dépôt ECR
5. WHEN un administrateur exécute le script de déploiement AWS, THE script SHALL utiliser Terraform pour provisionner l'infrastructure et déployer les services du Site_Central sur AWS
6. THE répertoire site-central/aws/scripts/ SHALL contenir un script de mise à jour des images ECR permettant de publier de nouvelles versions des modules RAG par Domaine

### Exigence 31 : Génération du package d'installation de l'application locale

**User Story :** En tant que développeur, je veux générer un package d'installation autonome de l'Application_Locale, afin que l'Expert puisse installer l'ensemble du système sur son PC de manière simple et complète.

#### Critères d'acceptation

1. THE répertoire site-central/aws/app_locale_package/ SHALL contenir un script de packaging qui produit un installateur autonome téléchargeable par l'Expert depuis la page /downloads du Site_Central
2. THE script de packaging SHALL intégrer dans l'installateur : l'Amorce, les images Docker de la souche (site web local, BD locale, LLM), les fichiers de configuration par défaut et le runtime Docker gratuit adapté à l'OS cible (Windows, macOS, Linux)
3. WHEN le développeur exécute le script de packaging, THE script SHALL produire un fichier installateur unique par OS cible, prêt à être publié sur le Site_Central
4. THE installateur généré SHALL exécuter automatiquement les vérifications de prérequis PC (CPU, RAM, disque, chiffrement) définies dans l'Exigence 1 lors de son lancement par l'Expert
5. THE installateur généré SHALL installer le runtime Docker, déployer les images Docker de la souche et configurer l'Amorce sans intervention technique de l'Expert
6. THE installateur généré SHALL utiliser une solution de packaging gratuite et compatible avec un usage commercial (par exemple NSIS pour Windows, ou un script shell auto-extractible pour macOS/Linux)

### Exigence 32 : Sécurité et protection des données

**User Story :** En tant qu'Expert, je veux que mes données d'expertise restent exclusivement sur mon PC, afin de garantir la confidentialité des dossiers judiciaires.

#### Critères d'acceptation

1. THE Application_Locale SHALL stocker toutes les données d'expertise exclusivement sur le disque local du PC de l'Expert
2. THE Application_Locale SHALL ne transmettre au Site_Central que les Tickets pour vérification, sans aucune donnée d'expertise
3. WHEN l'Expert s'inscrit sur le Site_Central, THE Site_Central SHALL exiger l'engagement de responsabilité de protection des données PC (chiffrement du disque)

### Exigence 33 : Dépôt d'images ECR

**User Story :** En tant que développeur, je veux stocker les images Docker dans un registre centralisé, afin de distribuer les composants de manière fiable.

#### Critères d'acceptation

1. THE Site_Central SHALL utiliser un dépôt d'images ECR (Elastic Container Registry) pour stocker les images Docker des composants
2. WHEN l'Expert télécharge l'Application_Locale ou un module RAG, THE Site_Central SHALL fournir les images Docker depuis le dépôt ECR

### Exigence 34 : Archivage des dossiers

**User Story :** En tant qu'Expert, je veux que mes dossiers finalisés soient archivés automatiquement, afin de conserver une trace complète et immuable de chaque expertise.

#### Critères d'acceptation

1. WHEN le Step3_REF est validé, THE Application_Locale SHALL créer une archive ZIP contenant tous les fichiers du Dossier : la réquisition originale, le fichier Markdown extrait, le QMEC, les NE, le REB, le REF, le RAUX et tous les fichiers intermédiaires
2. WHILE un Dossier est archivé, THE Application_Locale SHALL interdire toute modification ou suppression des fichiers contenus dans l'archive

### Exigence 35 : Fonctionnement heures ouvrables et page de maintenance

**User Story :** En tant qu'Administrateur, je veux pouvoir limiter le fonctionnement du Site Central aux heures ouvrables (8h-20h) et afficher une page de maintenance explicite en dehors de ces horaires, afin d'optimiser les coûts AWS.

#### Critères d'acceptation

1. THE Site_Central SHALL supporter un mode de fonctionnement limité aux heures ouvrables (8h-20h, timezone Europe/Paris) via un scheduler automatique (AWS EventBridge + Lambda)
2. WHEN le scheduler déclenche l'arrêt du Site_Central (20h), THE scheduler SHALL mettre à zéro le nombre de tâches ECS Fargate et arrêter l'instance RDS PostgreSQL
3. WHEN le scheduler déclenche le démarrage du Site_Central (8h), THE scheduler SHALL démarrer l'instance RDS PostgreSQL et remettre le nombre de tâches ECS Fargate à la valeur nominale
4. WHILE le Site_Central est arrêté, THE ALB SHALL afficher une page HTML de maintenance explicite indiquant : le nom du service "Judi-Expert", un message informant que le service est disponible de 8h à 20h (heure de Paris), et un lien de contact
5. THE page de maintenance SHALL être servie directement par l'ALB via une action fixed-response (code HTTP 503) sans nécessiter de serveur actif
6. WHILE le Site_Central est arrêté, THE Application_Locale SHALL continuer à fonctionner normalement pour les étapes d'expertise (Step0 à Step3) qui sont entièrement locales
7. IF un Expert tente de créer un dossier (vérification de ticket) pendant que le Site_Central est arrêté, THEN THE Application_Locale SHALL afficher un message indiquant que le service central est temporairement indisponible et de réessayer pendant les heures ouvrables

### Exigence 36 : Scripts d'arrêt et de redémarrage manuels du Site Central

**User Story :** En tant qu'Administrateur, je veux disposer de scripts manuels pour arrêter et redémarrer le Site Central à tout moment, afin de pouvoir intervenir en dehors du scheduler automatique (maintenance, urgence, etc.).

#### Critères d'acceptation

1. THE répertoire site-central/aws/scripts/ SHALL contenir un script `site-stop.sh` (ou .py) permettant d'arrêter manuellement le Site Central (ECS Fargate scale-to-zero + arrêt RDS)
2. THE répertoire site-central/aws/scripts/ SHALL contenir un script `site-start.sh` (ou .py) permettant de redémarrer manuellement le Site Central (démarrage RDS + ECS Fargate scale-up)
3. THE répertoire site-central/aws/scripts/ SHALL contenir un script `site-status.sh` (ou .py) permettant de vérifier l'état actuel du Site Central (ECS running/stopped, RDS available/stopped)
4. WHEN l'Administrateur exécute le script `site-stop.sh`, THE script SHALL arrêter les tâches ECS et l'instance RDS, et configurer l'ALB pour servir la page de maintenance
5. WHEN l'Administrateur exécute le script `site-start.sh`, THE script SHALL démarrer l'instance RDS, attendre sa disponibilité, puis démarrer les tâches ECS et restaurer la configuration ALB normale
6. WHEN l'Administrateur exécute le script `site-status.sh`, THE script SHALL afficher l'état de chaque composant (ECS, RDS, ALB) avec un indicateur clair (actif/arrêté)
