Est-ce que le système peut être # Plan d'Implémentation : Judi-Expert

## Vue d'ensemble

Implémentation incrémentale du système Judi-Expert en deux composants principaux : l'Application Locale (4 conteneurs Docker) et le Site Central (AWS). Chaque tâche construit sur les précédentes, en commençant par la structure du projet et les modèles de données, puis les services backend, les frontends, l'infrastructure Terraform, les scripts et la documentation.

## Tâches

- [x] 1. Initialiser la structure du projet et les dépendances
  - [x] 1.1 Créer l'arborescence du dépôt selon l'Exigence 28
    - Créer les répertoires : `site-central/local/{scripts,web,rag}`, `site-central/aws/{terraform,scripts,web,app_locale_package}`, `docs/`, `corpus/{psychologie,psychiatrie,medecine_legale,batiment,comptabilite}`, `tests/{unit,property,integration,smoke}`
    - Créer les fichiers `.env` dans `site-central/local/` et `site-central/aws/`
    - _Exigences : 28.1, 28.2, 28.3, 28.4_

  - [x] 1.2 Configurer le backend Python (FastAPI) de l'Application Locale
    - Créer `site-central/local/web/backend/` avec `main.py`, `requirements.txt`, `Dockerfile`
    - Dépendances : fastapi, uvicorn, sqlalchemy, alembic, python-docx, docxtpl, pytesseract, qdrant-client, httpx, passlib, python-jose
    - _Exigences : 26.1, 26.3, 26.7_

  - [x] 1.3 Configurer le frontend Next.js PWA de l'Application Locale
    - Créer `site-central/local/web/frontend/` avec `package.json`, `next.config.js`, `Dockerfile`
    - Dépendances : next, react, react-dom, axios
    - _Exigences : 26.1, 12.1_

  - [x] 1.4 Configurer le backend Python (FastAPI) du Site Central
    - Créer `site-central/aws/web/backend/` avec `main.py`, `requirements.txt`, `Dockerfile`
    - Dépendances : fastapi, uvicorn, sqlalchemy, alembic, stripe, boto3, httpx
    - _Exigences : 26.2, 26.4, 26.6_

  - [x] 1.5 Configurer le frontend Next.js PWA du Site Central
    - Créer `site-central/aws/web/frontend/` avec `package.json`, `next.config.js`, `Dockerfile`
    - Dépendances : next, react, react-dom, axios, aws-amplify, @stripe/stripe-js
    - _Exigences : 26.2, 17.1_

  - [x] 1.6 Créer le fichier `domaines.yaml` et la structure des corpus
    - Créer `domaines/domaines.yaml` avec les 5 domaines (psychologie actif, les 4 autres inactifs)
    - Créer `corpus/psychologie/contenu.yaml` décrivant le contenu du corpus
    - _Exigences : 22.1, 22.2, 22.3, 22.4_

- [x] 2. Implémenter les modèles de données et migrations (Application Locale)
  - [x] 2.1 Créer les modèles SQLAlchemy de l'Application Locale
    - Implémenter les modèles `LocalConfig`, `Dossier`, `Step`, `StepFile`, `ChatMessage` dans `site-central/local/web/backend/models/`
    - Configurer SQLAlchemy avec SQLite et le moteur async
    - _Exigences : 26.3, 5.1, 5.5, 10.1_

  - [x] 2.2 Configurer Alembic pour l'Application Locale
    - Initialiser Alembic dans `site-central/local/web/backend/`
    - Générer la migration initiale avec tous les modèles
    - _Exigences : 26.3_

  - [ ]* 2.3 Écrire le test par propriété pour la validation de création de dossier
    - **Propriété 2 : Validation de création de dossier**
    - Vérifier que la création réussit ssi nom non-vide et ticket valide, et que 4 étapes "initial" sont créées
    - **Valide : Exigences 5.1, 5.5**

  - [ ]* 2.4 Écrire le test par propriété pour le tri chronologique des dossiers
    - **Propriété 4 : Tri chronologique inverse des dossiers**
    - Vérifier que la liste retournée est triée par date de création décroissante
    - **Valide : Exigences 5.6**

- [x] 3. Implémenter les modèles de données et migrations (Site Central)
  - [x] 3.1 Créer les modèles SQLAlchemy du Site Central
    - Implémenter les modèles `Expert`, `Ticket`, `Domaine`, `CorpusVersion`, `ContactMessage` dans `site-central/aws/web/backend/models/`
    - Configurer SQLAlchemy avec PostgreSQL
    - _Exigences : 26.4, 15.2, 19.3_

  - [x] 3.2 Configurer Alembic pour le Site Central
    - Initialiser Alembic dans `site-central/aws/web/backend/`
    - Générer la migration initiale incluant le compte admin par défaut (admin@judi-expert.fr / "change-me")
    - _Exigences : 26.4, 19.1_

  - [ ]* 3.3 Écrire le test par propriété pour la génération de ticket unique
    - **Propriété 10 : Génération de ticket unique après paiement**
    - Vérifier qu'un paiement produit exactement un ticket unique avec le bon domaine et statut "actif"
    - **Valide : Exigences 15.2**

  - [ ]* 3.4 Écrire le test par propriété pour le cycle de vie des tickets
    - **Propriété 3 : Cycle de vie des tickets (idempotence d'utilisation)**
    - Vérifier que la première vérification réussit, les suivantes échouent avec "déjà utilisé"
    - **Valide : Exigences 5.3, 5.4, 15.2, 15.4**

- [x] 4. Checkpoint — Vérifier les modèles de données
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implémenter le service OCR (`judi-ocr`)
  - [x] 5.1 Créer le service OCR FastAPI
    - Implémenter le conteneur `judi-ocr` avec FastAPI, pytesseract, pdf2image, PyMuPDF, Pillow
    - Route `POST /api/ocr/extract` : accepte un PDF multipart, détecte le type (scan vs texte), extrait le texte via Tesseract (langue `fra`) ou PyMuPDF
    - Retourner `{ text, pages, confidence }`
    - Créer le `Dockerfile` pour `judi-ocr` avec Tesseract, Poppler et les dépendances Python
    - _Exigences : 6.2, 6.3, 6.8, 2.1_

  - [ ]* 5.2 Écrire les tests unitaires pour le service OCR
    - Tester l'extraction de PDF-scan (image) et de PDF texte
    - Tester la gestion des erreurs (PDF corrompu, fichier vide)
    - _Exigences : 6.2, 6.3_

- [x] 6. Implémenter le service LLM (`judi-llm`)
  - [x] 6.1 Configurer le conteneur Ollama avec Mistral 7B
    - Créer le `docker-compose.yml` pour le conteneur `judi-llm` basé sur l'image Ollama officielle
    - Configurer le téléchargement automatique du modèle `mistral:7b-instruct-v0.3` au premier démarrage
    - Exposer le port 11434
    - _Exigences : 2.1, 26.7_

  - [x] 6.2 Implémenter le client LLM dans le backend
    - Créer `site-central/local/web/backend/services/llm_service.py`
    - Implémenter les appels à l'API Ollama (`/api/chat`, `/api/generate`)
    - Définir les prompts système : `PROMPT_STRUCTURATION_MD`, `PROMPT_GENERATION_QMEC`, `PROMPT_GENERATION_REF`, `PROMPT_GENERATION_RAUX_P1`, `PROMPT_GENERATION_RAUX_P2`, `PROMPT_CHATBOT`
    - _Exigences : 6.4, 7.2, 9.2, 9.3, 11.2_

- [x] 7. Implémenter le service RAG (`judi-rag`)
  - [x] 7.1 Configurer le conteneur Qdrant
    - Ajouter le conteneur `judi-rag` au `docker-compose.yml` basé sur l'image Qdrant officielle
    - Exposer les ports 6333 (REST) et 6334 (gRPC)
    - _Exigences : 26.5, 2.1_

  - [x] 7.2 Implémenter le service RAG dans le backend
    - Créer `site-central/local/web/backend/services/rag_service.py`
    - Implémenter la classe `RAGService` avec les méthodes : `search`, `index_document`, `index_url`, `delete_collection`, `list_documents`
    - Utiliser le modèle d'embedding `sentence-transformers/all-MiniLM-L6-v2` via FastEmbed
    - Gérer les collections : `corpus_{domaine}`, `config_{domaine}`, `system_docs`
    - _Exigences : 3.5, 3.6, 11.2_

  - [ ]* 7.3 Écrire le test par propriété pour le round-trip d'indexation RAG
    - **Propriété 13 : Round-trip d'indexation RAG**
    - Vérifier qu'un document indexé est retrouvable par recherche sur son contenu
    - **Valide : Exigences 3.5**

  - [ ]* 7.4 Écrire le test par propriété pour le parsing round-trip domaines.yaml
    - **Propriété 12 : Parsing round-trip du fichier domaines.yaml**
    - Vérifier que sérialisation → parsing produit une structure équivalente
    - **Valide : Exigences 22.1, 22.2**

- [x] 8. Implémenter le Docker Compose de l'Application Locale
  - [x] 8.1 Créer le fichier `docker-compose.yml` complet
    - Définir les 4 services : `judi-web` (ports 3000, 8000), `judi-llm` (port 11434), `judi-rag` (ports 6333, 6334), `judi-ocr` (port 8001)
    - Configurer les volumes pour la persistance des données (SQLite, fichiers dossiers, modèle LLM)
    - Configurer les dépendances de démarrage entre conteneurs
    - _Exigences : 2.1, 2.2_

- [x] 9. Checkpoint — Vérifier les services de base
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Implémenter l'API backend de l'Application Locale
  - [x] 10.1 Implémenter l'authentification locale
    - Routes `POST /api/auth/setup` et `POST /api/auth/login`
    - Hachage du mot de passe avec passlib (bcrypt)
    - Gestion du token JWT local
    - _Exigences : 3.1, 14.1_

  - [x] 10.2 Implémenter les routes de configuration
    - Routes `/api/config/domain`, `/api/config/rag-versions`, `/api/config/rag-install`, `/api/config/tpe`, `/api/config/template`, `/api/config/documents`
    - Blocage des fonctionnalités si RAG non configuré
    - Upload/remplacement du TPE et du Template Rapport (.docx) avec indexation dans la base RAG
    - _Exigences : 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 4.1, 4.2_

  - [x] 10.3 Implémenter les routes de gestion des dossiers
    - Routes `GET/POST /api/dossiers`, `GET /api/dossiers/{id}`, `GET /api/dossiers/{id}/steps/{step}`
    - Création de dossier avec vérification de ticket via le Site Central
    - Tri chronologique inverse des dossiers
    - Création automatique des 4 étapes au statut "initial"
    - _Exigences : 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

  - [x] 10.4 Implémenter le moteur de workflow séquentiel
    - Créer `site-central/local/web/backend/services/workflow_engine.py`
    - Imposer l'ordre Step0 → Step1 → Step2 → Step3
    - Gérer les transitions de statut : initial → réalisé → validé
    - Interdire l'accès aux étapes suivantes tant que l'étape courante n'est pas validée
    - Interdire toute modification d'une étape validée
    - _Exigences : 10.1, 10.2, 10.3, 10.4_

  - [ ]* 10.5 Écrire le test par propriété pour la machine à états du workflow
    - **Propriété 6 : Machine à états du workflow d'expertise**
    - Vérifier les invariants : ordre séquentiel, blocage, immutabilité des étapes validées, verrouillage final
    - **Valide : Exigences 7.4, 8.4, 9.5, 10.1, 10.2, 10.3, 10.4**

  - [x] 10.6 Implémenter les routes Step0 (Extraction OCR)
    - Routes `POST /api/dossiers/{id}/step0/extract`, `GET/PUT /api/dossiers/{id}/step0/markdown`
    - Appel au service OCR (`judi-ocr`) pour extraction du texte brut
    - Appel au LLM pour structuration en Markdown (identification QT, destinataire, sections)
    - Stockage du fichier Markdown généré
    - _Exigences : 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

  - [x] 10.7 Implémenter les routes Step1 (PEMEC)
    - Routes `POST /api/dossiers/{id}/step1/execute`, `GET /api/dossiers/{id}/step1/download`, `POST /api/dossiers/{id}/step1/validate`
    - Récupération du TPE et du contexte domaine via RAG
    - Génération du QMEC via LLM (QT + TPE + contexte RAG)
    - _Exigences : 7.1, 7.2, 7.3, 7.4_

  - [x] 10.8 Implémenter les routes Step2 (Upload)
    - Routes `POST /api/dossiers/{id}/step2/upload`, `POST /api/dossiers/{id}/step2/validate`
    - Validation du format .docx pour les fichiers NE et REB
    - Stockage des fichiers dans le dossier correspondant
    - _Exigences : 8.1, 8.2, 8.3, 8.4_

  - [ ]* 10.9 Écrire le test par propriété pour la validation du format .docx
    - **Propriété 5 : Validation du format de fichier .docx**
    - Vérifier que seuls les fichiers .docx sont acceptés, les autres sont rejetés avec message d'erreur
    - **Valide : Exigences 8.2, 8.3**

  - [x] 10.10 Implémenter les routes Step3 (REF + RAUX)
    - Routes `POST /api/dossiers/{id}/step3/execute`, `GET /api/dossiers/{id}/step3/download/{type}`, `POST /api/dossiers/{id}/step3/validate`
    - Génération du REF via LLM (REB + QT + NE + Template Rapport) avec docxtpl pour le rendu .docx
    - Génération du RAUX Partie 1 (contestations) et Partie 2 (révision) via LLM + RAG
    - Validation : verrouillage définitif du dossier + archivage ZIP
    - _Exigences : 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [ ]* 10.11 Écrire le test par propriété pour la complétude de l'archive
    - **Propriété 7 : Complétude et immutabilité de l'archive**
    - Vérifier que l'archive ZIP contient tous les fichiers du dossier et qu'aucune modification n'est possible après archivage
    - **Valide : Exigences 9.6, 34.1, 34.2**

  - [x] 10.12 Implémenter les routes du ChatBot
    - Routes `POST /api/chatbot/message`, `GET /api/chatbot/history`
    - Utilisation du LLM avec contexte RAG (corpus domaine + documentation système)
    - Stockage de l'historique des conversations
    - _Exigences : 11.1, 11.2, 11.3_

  - [x] 10.13 Implémenter la route de vérification de ticket
    - Route `POST /api/tickets/verify` : appel HTTP au Site Central pour vérification
    - Gestion des erreurs réseau (Site Central indisponible pendant heures non ouvrables)
    - _Exigences : 5.2, 5.3, 5.4, 35.7_

- [x] 11. Checkpoint — Vérifier l'API de l'Application Locale
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Implémenter l'API backend du Site Central
  - [x] 12.1 Implémenter l'authentification Cognito
    - Routes `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`
    - Intégration AWS Cognito User Pools via boto3
    - Formulaire d'inscription avec champs obligatoires (Nom, Prénom, adresse, Domaine) et cases à cocher (Mentions légales, CGU, engagement protection données)
    - Case optionnelle newsletter
    - _Exigences : 13.1, 13.2, 13.3, 13.4, 13.5, 14.1, 14.2, 14.3_

  - [ ]* 12.2 Écrire le test par propriété pour la validation du formulaire d'inscription
    - **Propriété 8 : Validation du formulaire d'inscription**
    - Vérifier que l'inscription réussit ssi tous les champs obligatoires sont remplis et toutes les cases obligatoires cochées
    - **Valide : Exigences 13.3, 13.4, 13.5**

  - [ ]* 12.3 Écrire le test par propriété pour l'uniformité du message d'erreur de connexion
    - **Propriété 9 : Uniformité du message d'erreur de connexion**
    - Vérifier que le message d'erreur est identique quel que soit le type d'identifiant invalide
    - **Valide : Exigences 14.3**

  - [x] 12.4 Implémenter les routes de profil
    - Routes `GET/PUT /api/profile`, `PUT /api/profile/password`, `DELETE /api/profile/delete`
    - Changement de mot de passe via Cognito, suppression de compte
    - _Exigences : 18.5_

  - [x] 12.5 Implémenter les routes de paiement Stripe
    - Routes `POST /api/tickets/purchase`, `GET /api/tickets/list`, `POST /api/tickets/verify`
    - Création de session Stripe Checkout
    - Webhook `POST /api/webhooks/stripe` pour confirmation de paiement et génération de ticket unique
    - Envoi du ticket par email à l'expert
    - Vérification de ticket (appelé par l'Application Locale)
    - _Exigences : 15.1, 15.2, 15.3, 15.4_

  - [x] 12.6 Implémenter les routes de corpus et téléchargements
    - Routes `GET /api/corpus`, `GET /api/corpus/{domaine}/versions`, `GET /api/downloads/app`
    - Lecture du fichier `domaines.yaml` pour lister les corpus
    - Distribution des images Docker RAG depuis ECR
    - _Exigences : 18.1, 18.2, 4.2, 33.1, 33.2_

  - [x] 12.7 Implémenter les routes de contact et administration
    - Route `POST /api/contact` : formulaire avec sélection domaine et objet
    - Routes `GET /api/admin/experts`, `GET /api/admin/stats/tickets`
    - Filtre par domaine pour les statistiques de tickets (jour, mois courant, mois passés)
    - _Exigences : 18.3, 19.2, 19.3, 19.4_

  - [ ]* 12.8 Écrire le test par propriété pour le filtrage des statistiques de tickets
    - **Propriété 11 : Filtrage des statistiques de tickets par domaine**
    - Vérifier que le filtre retourne uniquement les tickets du domaine sélectionné, ou tous si "Tous"
    - **Valide : Exigences 19.4**

- [x] 13. Checkpoint — Vérifier l'API du Site Central
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Implémenter le frontend de l'Application Locale (Next.js PWA)
  - [x] 14.1 Créer le layout principal (Header + Footer)
    - Header : Logo "Judi-expert Local" (texte), Dossiers, Configuration, Site Central (lien externe), FAQ (lien externe)
    - Footer : "© ItechSource 2026", CHU (lien externe), Mentions légales, CGU (lien externe), Contact (lien externe)
    - _Exigences : 12.3, 12.4, 20.2_

  - [x] 14.2 Implémenter la page de configuration initiale (`/setup`)
    - Formulaire : mot de passe local + sélection du domaine d'expertise
    - Blocage si RAG non configuré
    - _Exigences : 3.1, 3.2_

  - [x] 14.3 Implémenter la page de connexion locale (`/login`)
    - Formulaire email/mot de passe local
    - _Exigences : 3.1_

  - [x] 14.4 Implémenter la page de configuration (`/config`)
    - Liste des versions RAG disponibles avec contenu détaillé
    - Téléchargement et installation du module RAG
    - Upload/remplacement du TPE et du Template Rapport
    - Liste des documents présents dans la base RAG
    - Proposition des fichiers exemples psychologie comme valeurs par défaut
    - _Exigences : 3.3, 3.4, 3.5, 3.6, 3.7, 4.1, 4.2, 24.6_

  - [x] 14.5 Implémenter la page d'accueil — liste des dossiers (`/`)
    - Liste des dossiers en ordre chronologique inverse
    - Bouton de création de dossier (nom + ticket)
    - _Exigences : 5.1, 5.6, 12.2_

  - [x] 14.6 Implémenter la page de détail dossier (`/dossier/[id]`)
    - Affichage des 4 étapes avec état (initial, réalisé, validé) et lien d'accès
    - _Exigences : 5.7_

  - [x] 14.7 Implémenter les vues des étapes (`/dossier/[id]/step/[n]`)
    - Step0 : upload PDF-scan, bouton "Extraction", bouton "Visualiser", édition Markdown
    - Step1 : bouton "Execute", bouton "Download" QMEC, bouton "Valider"
    - Step2 : upload NE.docx + REB.docx, validation format .docx, bouton "Valider"
    - Step3 : bouton "Execute", boutons "Download" REF et RAUX, bouton "Valider"
    - _Exigences : 6.1, 6.5, 6.6, 6.7, 7.1, 7.3, 7.4, 8.1, 8.2, 8.3, 8.4, 9.1, 9.4, 9.5_

  - [x] 14.8 Implémenter la page ChatBot (`/chatbot`)
    - Interface conversationnelle avec historique
    - Envoi de messages et affichage des réponses
    - _Exigences : 11.1, 11.3_

- [x] 15. Implémenter le frontend du Site Central (Next.js PWA)
  - [x] 15.1 Créer le layout principal (Header + Footer)
    - Header : Logo "Judi-expert", Corpus, FAQ, Connexion/Inscription (ou "Mon Espace" si connecté, "Administration" si admin)
    - Footer : "© ITechSource 2026", Mentions légales, CGU, FAQ, Contact
    - _Exigences : 17.1, 17.2, 17.3, 17.4, 19.2_

  - [x] 15.2 Implémenter la page d'accueil / Landing Page (`/`)
    - Section accueil : image libre de droits, message principal "Réduisez de 50%...", messages RGPD/AI Act, mention "Le site est ouvert pendant les horaires bureau de 8h à 20h"
    - Section domaines couverts (Santé, Bâtiment, Comptabilité)
    - Section "Comment ça marche ?" avec workflow
    - Section workflow d'expertise avec schéma (exemple psychologie)
    - Section conformité AI Act
    - _Exigences : 16.1, 16.2, 16.3, 16.4, 16.5_

  - [x] 15.3 Implémenter les pages d'authentification
    - Page `/inscription` : formulaire Cognito (Nom, Prénom, adresse, Domaine, cases à cocher)
    - Page `/connexion` : formulaire email/mot de passe + Captcha Google V2
    - Intégration AWS Amplify JS pour Cognito
    - _Exigences : 13.1, 13.2, 13.3, 13.4, 13.5, 14.1, 14.2_

  - [x] 15.4 Implémenter les pages de contenu
    - Pages `/corpus`, `/contact`, `/downloads`, `/faq`
    - Page `/downloads` : téléchargement du package Application Locale + document methodologie.md en PDF
    - _Exigences : 18.1, 18.2, 18.3, 20.1, 20.3_

  - [x] 15.5 Implémenter l'espace personnel (`/monespace`)
    - Navigation par onglets
    - Page `/monespace/profil` : paramètres, changement mot de passe, suppression compte
    - Page `/monespace/tickets` : liste des tickets avec dates et montants, bouton d'achat Stripe
    - _Exigences : 18.4, 18.5, 18.6, 15.1_

  - [x] 15.6 Implémenter les pages légales
    - Pages `/mentions-legales`, `/cgu`, `/politique-confidentialite`
    - _Exigences : 20.1_

  - [x] 15.7 Implémenter la page d'administration (`/admin`)
    - Onglet "Experts" : liste des experts inscrits avec domaine et date
    - Onglet "Statistiques tickets" : filtre par domaine, liste des achats (jour, mois courant, mois passés)
    - _Exigences : 19.3, 19.4_

- [x] 16. Checkpoint — Vérifier les frontends
  - Ensure all tests pass, ask the user if questions arise.

- [x] 17. Implémenter l'infrastructure Terraform (Site Central AWS)
  - [x] 17.1 Créer les modules Terraform de base
    - VPC, sous-réseaux publics/privés, groupes de sécurité
    - ECR (Elastic Container Registry) pour les images Docker
    - RDS PostgreSQL (instance arrêtable)
    - S3 bucket pour les assets statiques
    - _Exigences : 25.2, 25.3, 33.1_

  - [x] 17.2 Créer les modules Terraform ECS Fargate + ALB
    - ECS Cluster, Task Definition, Service (scalable à zéro)
    - Application Load Balancer avec règle fixed-response pour la page de maintenance (HTTP 503)
    - CloudFront CDN devant l'ALB et S3
    - _Exigences : 25.2, 25.3, 35.4, 35.5_

  - [x] 17.3 Créer le module Terraform Cognito
    - User Pool avec configuration d'inscription
    - App Client pour le frontend
    - _Exigences : 13.2, 25.3_

  - [x] 17.4 Créer le module Terraform pour le scheduler heures ouvrables
    - AWS EventBridge rules pour démarrage (8h) et arrêt (20h) timezone Europe/Paris
    - Lambda functions pour scale ECS à zéro / valeur nominale et start/stop RDS
    - _Exigences : 35.1, 35.2, 35.3_

  - [ ]* 17.5 Écrire le test par propriété pour la validation des prérequis système
    - **Propriété 1 : Validation des prérequis système**
    - Vérifier que la validation accepte ssi toutes les conditions minimales sont satisfaites, et que le message d'erreur liste exactement les conditions non remplies
    - **Valide : Exigences 1.1, 1.2**

- [x] 18. Implémenter les scripts de gestion
  - [x] 18.1 Créer les scripts locaux (`site-central/local/scripts/`)
    - Script `build.sh` : build des images Docker locales (judi-web, judi-llm, judi-rag, judi-ocr)
    - Script `start.sh` : démarrage de tous les conteneurs via docker-compose
    - Script `stop.sh` : arrêt de tous les conteneurs
    - Script `restart.sh` : redémarrage complet
    - _Exigences : 30.1, 30.3_

  - [x] 18.2 Créer les scripts AWS (`site-central/aws/scripts/`)
    - Script `build.sh` : build des images Docker de production
    - Script `push-ecr.sh` : push des images vers ECR
    - Script `deploy.sh` : déploiement Terraform (plan + apply)
    - Script `update-rag.sh` : mise à jour des images RAG par domaine dans ECR
    - _Exigences : 30.2, 30.4, 30.5, 30.6_

  - [x] 18.3 Créer les scripts d'arrêt/démarrage/statut manuels
    - Script `site-stop.sh` : arrêt ECS (scale-to-zero) + arrêt RDS + configuration ALB maintenance
    - Script `site-start.sh` : démarrage RDS (attente disponibilité) + démarrage ECS + restauration ALB
    - Script `site-status.sh` : affichage état ECS, RDS, ALB avec indicateurs actif/arrêté
    - _Exigences : 36.1, 36.2, 36.3, 36.4, 36.5, 36.6_

  - [x] 18.4 Créer l'Amorce (lanceur de l'Application Locale)
    - Script/exécutable qui vérifie le runtime Docker, démarre Docker si nécessaire, puis lance `docker-compose up`
    - _Exigences : 1.4, 1.5, 2.2_

- [x] 19. Implémenter le script de packaging de l'Application Locale
  - [x] 19.1 Créer le script de packaging (`site-central/aws/app_locale_package/`)
    - Script qui produit un installateur autonome par OS (Windows via NSIS, macOS/Linux via script shell auto-extractible)
    - Intégration de l'Amorce, des images Docker souche, des fichiers de configuration par défaut et du runtime Docker gratuit
    - Vérification automatique des prérequis PC (CPU, RAM, disque, chiffrement) à l'installation
    - _Exigences : 31.1, 31.2, 31.3, 31.4, 31.5, 31.6, 1.1, 1.2, 1.3_

- [x] 20. Checkpoint — Vérifier l'infrastructure et les scripts
  - Ensure all tests pass, ask the user if questions arise.

- [x] 21. Créer le corpus du domaine psychologie
  - [x] 21.1 Préparer les documents et URLs du corpus psychologie
    - Créer `corpus/psychologie/documents/` avec des documents PDF publics de référence (guides méthodologiques, textes réglementaires, référentiels de bonnes pratiques)
    - Créer `corpus/psychologie/urls/urls.yaml` avec des URLs publiques (sites institutionnels, bases juridiques, ressources académiques)
    - Mettre à jour `corpus/psychologie/contenu.yaml` avec la description de chaque entrée
    - _Exigences : 23.1, 23.2, 23.3, 23.4, 23.5_

  - [x] 21.2 Vérifier et compléter les fichiers exemples psychologie
    - Vérifier que `corpus/psychologie/TPE_psychologie.tpl` est structuré selon les bonnes pratiques (identification, motif, anamnèse, examen clinique, tests, analyse, conclusions)
    - Vérifier que `corpus/psychologie/template_rapport_psychologie.docx` contient les champs de fusion (placeholders) pour destinataire, QT, réponses, analyse, conclusions
    - S'assurer que le template ne contient pas d'identité en dur
    - _Exigences : 24.1, 24.2, 24.3, 24.4, 24.5_

- [x] 22. Générer la documentation projet
  - [x] 22.1 Générer les documents Markdown dans `docs/`
    - `architecture.md` : architecture globale (Application Locale, Site Central, ECR, conteneurs, flux)
    - `developpement.md` : procédures de développement, prérequis, configuration environnement, conventions
    - `exploitation.md` : procédures d'exploitation (démarrage, arrêt, surveillance, sauvegarde, mise à jour)
    - `stripe.md` : intégration Stripe (clés API, flux paiement, webhooks, tests)
    - `user-guide.md` : guide utilisateur complet de l'Application Locale
    - `methodologie.md` : présentation de la solution, usage IA, conformité réglementaire, autorisations experts judiciaires
    - `cout-aws.md` : estimation coûts AWS mensuels, scénarios dimensionnement, mode heures ouvrables 8h-20h, optimisations
    - _Exigences : 29.1, 29.2, 29.3, 29.4, 29.5, 29.6, 29.7, 29.8, 21.1, 21.2, 21.3_

  - [x] 22.2 Générer les documents légaux dans `docs/`
    - `cgu.md` : conditions générales d'utilisation
    - `mentions_legales.md` : mentions légales
    - `politique_confidentialite.md` : politique de confidentialité
    - `faq.md` : questions fréquentes
    - `licences.md` : inventaire des dépendances avec nom, version, licence, URL
    - _Exigences : 20.1, 27.2, 29.1_

- [x] 23. Implémenter la sécurité et la protection des données
  - [x] 23.1 Vérifier l'isolation des données d'expertise
    - S'assurer que l'Application Locale ne transmet au Site Central que les tickets
    - Vérifier que toutes les données d'expertise sont stockées exclusivement en local
    - Implémenter le Captcha Google V2 sur la page de connexion du Site Central
    - _Exigences : 32.1, 32.2, 32.3, 14.1_

- [x] 24. Intégration finale et câblage
  - [x] 24.1 Câbler le frontend et le backend de l'Application Locale
    - Connecter toutes les pages Next.js aux routes FastAPI correspondantes
    - Vérifier le flux complet Step0 → Step1 → Step2 → Step3
    - _Exigences : 10.1, 10.2, 10.3, 10.4_

  - [x] 24.2 Câbler le frontend et le backend du Site Central
    - Connecter toutes les pages Next.js aux routes FastAPI correspondantes
    - Intégrer Amplify JS pour l'authentification Cognito
    - Intégrer Stripe.js pour le paiement
    - _Exigences : 13.2, 15.1, 17.1_

  - [x] 24.3 Câbler l'Application Locale avec le Site Central
    - Vérification de ticket : appel HTTP de l'Application Locale vers le Site Central
    - Téléchargement des modules RAG depuis ECR
    - Gestion de l'indisponibilité du Site Central (heures non ouvrables)
    - _Exigences : 5.2, 5.3, 33.2, 35.6, 35.7_

  - [ ]* 24.4 Écrire les tests d'intégration
    - Test Docker Compose : démarrage et communication inter-conteneurs
    - Test flux complet Step0 → Step3 avec données exemples psychologie
    - Test flux paiement Stripe (mode test)
    - _Exigences : 2.1, 10.1, 15.1_

- [x] 25. Checkpoint final — Vérification complète
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Les tâches marquées avec `*` sont optionnelles et peuvent être ignorées pour un MVP plus rapide
- Chaque tâche référence les exigences spécifiques pour la traçabilité
- Les checkpoints permettent une validation incrémentale
- Les tests par propriétés valident les 13 propriétés de correction définies dans le document de conception
- Les tests unitaires valident les cas spécifiques et les cas limites
- Le projet utilise exclusivement des composants open-source/gratuits (Exigences 26.7, 26.8, 27.1)
