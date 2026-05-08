# Document d'Exigences — Gestion des Versions

## Introduction

Cette fonctionnalité met en place un système complet de gestion des versions pour Judi-Expert, couvrant quatre axes : la mise à jour forcée de l'Application Locale au démarrage (via un endpoint de version sur le Site Central), la mise à jour en arrière-plan du modèle LLM Mistral (via le registre Ollama), la vérification automatique du modèle dans les scripts de développement, et le versionnage du Site Central lui-même. Le Site Central expose un endpoint de version que l'Application Locale interroge à chaque démarrage pour déterminer si une mise à jour est disponible. Les mises à jour applicatives sont bloquantes (l'expert ne peut pas utiliser l'application tant que la mise à jour n'est pas appliquée), tandis que les mises à jour du modèle LLM sont non-bloquantes (téléchargement en arrière-plan, activation au prochain redémarrage). La version courante de chaque composant (Application Locale et Site Central) est centralisée dans un fichier unique `VERSION` et affichée dans l'interface. Toutes les communications de version respectent la restriction aux heures ouvrables (8h-20h Europe/Paris) et aucune donnée de dossier ne transite vers le Site Central.

## Glossaire

- **Application_Locale** : Application web locale (Next.js + FastAPI + Docker Compose) installée sur le PC de l'expert
- **Site_Central** : Plateforme web hébergée sur AWS gérant l'administration, les tickets et la distribution des mises à jour
- **Version_Endpoint** : Endpoint REST du Site_Central retournant les informations de version courante de l'Application_Locale
- **Version_Applicative** : Numéro de version de l'Application_Locale au format semver (ex : 1.2.0)
- **Version_Modèle** : Identifiant de version du modèle LLM Mistral sur le registre Ollama (digest SHA256)
- **Mise_À_Jour_Forcée** : Processus bloquant de mise à jour de l'Application_Locale empêchant toute utilisation tant que la mise à jour n'est pas terminée
- **Mise_À_Jour_Arrière_Plan** : Processus non-bloquant de téléchargement du nouveau modèle LLM pendant que l'expert continue à travailler
- **SiteCentralClient** : Client HTTP centralisé de l'Application_Locale pour les appels au Site_Central avec retry et vérification des heures ouvrables
- **LocalConfig** : Modèle SQLAlchemy stockant la configuration locale de l'Application_Locale (mot de passe, domaine, versions)
- **Ollama_Entrypoint** : Script bash d'initialisation du conteneur judi-llm gérant le démarrage d'Ollama et le téléchargement du modèle
- **Page_Connexion** : Page de connexion/lancement de l'Application_Locale affichée à l'expert au démarrage
- **Écran_Mise_À_Jour** : Écran bloquant affiché pendant le téléchargement et l'application d'une mise à jour forcée
- **Administrateur_Central** : Utilisateur administrateur du Site_Central autorisé à publier de nouvelles versions
- **Heures_Ouvrables** : Plage horaire 8h-20h Europe/Paris pendant laquelle la communication avec le Site_Central est autorisée
- **Script_Dev** : Scripts start.sh et restart.sh utilisés par les développeurs pour lancer l'Application_Locale en environnement de développement
- **Version_Site_Central** : Numéro de version du Site Central au format semver, défini dans `central-site/VERSION`
- **Page_Admin** : Interface d'administration du Site Central accessible aux Administrateur_Central

## Exigences

### Exigence 1 : Centralisation du numéro de version applicative

**User Story :** En tant que développeur, je veux que le numéro de version de l'Application Locale soit défini dans un fichier unique, afin d'éviter les incohérences entre les différents composants qui référencent la version.

#### Critères d'acceptation

1. THE Application_Locale SHALL définir la Version_Applicative dans un fichier unique `local-site/VERSION` contenant le numéro de version au format semver (MAJOR.MINOR.PATCH) sur la première ligne et la date de publication au format ISO (YYYY-MM-DD) sur la deuxième ligne
2. WHEN le backend FastAPI démarre, THE Application_Locale SHALL lire la Version_Applicative depuis le fichier `VERSION` et l'exposer via la variable `APP_VERSION`
3. WHEN le script package.sh génère l'installateur, THE script SHALL lire la Version_Applicative depuis le fichier `VERSION` au lieu d'utiliser la variable d'environnement `JUDI_VERSION`
4. WHEN le fichier `VERSION` est absent ou illisible, THE Application_Locale SHALL refuser de démarrer et afficher un message d'erreur indiquant que le fichier de version est manquant

### Exigence 2 : Endpoint de version sur le Site Central

**User Story :** En tant qu'administrateur du Site Central, je veux un endpoint de version que les Applications Locales peuvent interroger, afin de contrôler la distribution des mises à jour.

#### Critères d'acceptation

1. THE Site_Central SHALL exposer un endpoint GET `/api/version` retournant un objet JSON contenant les champs `latest_version` (string semver), `download_url` (string URL), `mandatory` (booléen) et `release_notes` (string optionnel)
2. WHEN l'Administrateur_Central publie une nouvelle version, THE Site_Central SHALL mettre à jour les informations retournées par le Version_Endpoint
3. THE Site_Central SHALL stocker les informations de version dans un modèle `AppVersion` en base de données avec les champs `version`, `download_url`, `mandatory`, `release_notes` et `published_at`
4. THE Site_Central SHALL exposer un endpoint POST `/api/admin/versions` accessible uniquement aux Administrateur_Central pour publier une nouvelle version
5. WHEN le endpoint POST `/api/admin/versions` est appelé, THE Site_Central SHALL valider que le champ `version` respecte le format semver avant d'enregistrer la nouvelle version

### Exigence 3 : Vérification de version applicative au démarrage

**User Story :** En tant qu'expert, je veux que mon application vérifie automatiquement si une mise à jour est disponible au démarrage, afin de toujours travailler avec la dernière version.

#### Critères d'acceptation

1. WHEN l'Application_Locale démarre et que l'heure courante est dans les Heures_Ouvrables, THE Application_Locale SHALL interroger le Version_Endpoint du Site_Central pour obtenir la dernière Version_Applicative disponible
2. WHEN la Version_Applicative locale est inférieure à la version retournée par le Version_Endpoint et que le champ `mandatory` est true, THE Application_Locale SHALL déclencher une Mise_À_Jour_Forcée
3. WHEN une Mise_À_Jour_Forcée est déclenchée, THE Application_Locale SHALL afficher l'Écran_Mise_À_Jour et bloquer toute interaction de l'expert jusqu'à la fin de la mise à jour
4. WHEN l'Application_Locale démarre en dehors des Heures_Ouvrables, THE Application_Locale SHALL ignorer la vérification de version et démarrer normalement avec la version courante
5. IF la communication avec le Site_Central échoue après les tentatives de retry, THEN THE Application_Locale SHALL journaliser l'erreur et démarrer normalement avec la version courante
6. THE Application_Locale SHALL stocker la Version_Applicative courante dans le champ `app_version` du modèle LocalConfig

### Exigence 4 : Processus de mise à jour forcée de l'Application Locale

**User Story :** En tant qu'expert, je veux que la mise à jour de mon application soit automatique et fiable, afin de ne pas avoir à intervenir manuellement.

#### Critères d'acceptation

1. WHEN une Mise_À_Jour_Forcée est déclenchée, THE Application_Locale SHALL télécharger les nouvelles images Docker depuis l'URL fournie par le Version_Endpoint
2. WHEN le téléchargement des images est terminé, THE Application_Locale SHALL arrêter les conteneurs existants, charger les nouvelles images et redémarrer les conteneurs via Docker Compose
3. WHILE la Mise_À_Jour_Forcée est en cours, THE Écran_Mise_À_Jour SHALL afficher une barre de progression indiquant l'étape courante (téléchargement, installation, redémarrage)
4. WHEN la Mise_À_Jour_Forcée est terminée, THE Application_Locale SHALL mettre à jour le champ `app_version` dans LocalConfig et rediriger l'expert vers la Page_Connexion
5. IF le téléchargement ou l'installation échoue, THEN THE Application_Locale SHALL annuler la mise à jour, restaurer les conteneurs précédents et afficher un message d'erreur avec la possibilité de réessayer
6. THE Mise_À_Jour_Forcée SHALL préserver tous les volumes Docker (web_data, dossiers_data, ollama_data, qdrant_data) pour garantir qu'aucune donnée de dossier n'est perdue

### Exigence 5 : Affichage de la version sur l'Application Locale

**User Story :** En tant qu'expert, je veux voir la version de mon application sur chaque page, afin de vérifier que je travaille avec la bonne version.

#### Critères d'acceptation

1. THE Application_Locale SHALL afficher la Version_Applicative courante dans le pied de page (footer) de toutes les pages au format « App Locale V{MAJOR}.{MINOR}.{PATCH} - {date_version} » où {date_version} est la date de publication au format « {jour} {mois} {année} » (ex : « App Locale V1.2.0 - 17 avril 2026 »)
2. WHEN une Mise_À_Jour_Forcée vient de se terminer, THE Page_Connexion SHALL afficher un bandeau d'information indiquant « Application mise à jour en version {version} »
3. THE Application_Locale SHALL exposer un endpoint GET `/api/version` retournant la Version_Applicative courante pour que le frontend puisse l'afficher

### Exigence 6 : Vérification de version du modèle LLM au démarrage

**User Story :** En tant qu'expert, je veux que mon application vérifie si une nouvelle version du modèle Mistral est disponible, afin de bénéficier des améliorations du modèle sans intervention manuelle.

#### Critères d'acceptation

1. WHEN l'Application_Locale démarre, THE Ollama_Entrypoint SHALL vérifier si une version plus récente du modèle LLM est disponible sur le registre Ollama en comparant le digest local avec le digest distant
2. WHEN une nouvelle Version_Modèle est disponible, THE Application_Locale SHALL afficher un avertissement sur la Page_Connexion indiquant « Une nouvelle version du modèle IA est en cours de téléchargement »
3. WHEN une nouvelle Version_Modèle est disponible, THE Ollama_Entrypoint SHALL démarrer une Mise_À_Jour_Arrière_Plan en téléchargeant le nouveau modèle sans interrompre le service Ollama existant
4. WHILE la Mise_À_Jour_Arrière_Plan est en cours, THE Application_Locale SHALL continuer à utiliser la version courante du modèle pour toutes les requêtes LLM
5. WHEN la Mise_À_Jour_Arrière_Plan est terminée, THE Application_Locale SHALL utiliser la nouvelle Version_Modèle au prochain redémarrage du conteneur judi-llm
6. IF le téléchargement du nouveau modèle échoue, THEN THE Application_Locale SHALL journaliser l'erreur et continuer à utiliser la version courante du modèle

### Exigence 7 : Suivi de l'état de mise à jour du modèle LLM

**User Story :** En tant qu'expert, je veux connaître l'état du téléchargement du nouveau modèle, afin de savoir quand il sera disponible.

#### Critères d'acceptation

1. THE Application_Locale SHALL exposer un endpoint GET `/api/llm/update-status` retournant l'état de la Mise_À_Jour_Arrière_Plan (statut : `idle`, `downloading`, `ready`, `error`) et le pourcentage de progression
2. WHEN le statut est `downloading`, THE Page_Connexion SHALL afficher la progression du téléchargement du nouveau modèle
3. WHEN le statut est `ready`, THE Page_Connexion SHALL afficher un message indiquant « Nouveau modèle prêt — sera activé au prochain redémarrage »
4. THE Application_Locale SHALL stocker la Version_Modèle courante dans le champ `llm_model_version` du modèle LocalConfig

### Exigence 8 : Vérification du modèle LLM dans les scripts de développement

**User Story :** En tant que développeur, je veux que les scripts start.sh et restart.sh vérifient automatiquement si le modèle Mistral a évolué, afin de toujours travailler avec la dernière version du modèle en développement.

#### Critères d'acceptation

1. WHEN le Script_Dev start.sh est exécuté, THE Script_Dev SHALL vérifier si une version plus récente du modèle LLM est disponible en exécutant `ollama pull` avec le tag du modèle configuré dans la variable `LLM_MODEL`
2. WHEN le Script_Dev restart.sh est exécuté, THE Script_Dev SHALL vérifier si une version plus récente du modèle LLM est disponible en exécutant `ollama pull` avec le tag du modèle configuré dans la variable `LLM_MODEL`
3. WHEN une nouvelle version du modèle est détectée par le Script_Dev, THE Script_Dev SHALL forcer le téléchargement du nouveau modèle avant de démarrer les conteneurs applicatifs
4. WHILE le téléchargement du modèle est en cours dans le Script_Dev, THE Script_Dev SHALL afficher la progression du téléchargement dans la console
5. IF le téléchargement du modèle échoue dans le Script_Dev, THEN THE Script_Dev SHALL afficher un message d'erreur et interrompre le démarrage

### Exigence 9 : Isolation des données lors des vérifications de version

**User Story :** En tant qu'expert, je veux que les vérifications de version ne transmettent aucune donnée de dossier au Site Central, afin de garantir la confidentialité de mes données conformément au RGPD et à l'AI Act.

#### Critères d'acceptation

1. THE Application_Locale SHALL transmettre uniquement la Version_Applicative courante comme paramètre lors de l'interrogation du Version_Endpoint (aucune donnée de dossier, aucun identifiant d'expert)
2. THE SiteCentralClient SHALL valider que les requêtes vers le Version_Endpoint ne contiennent aucun champ relatif aux dossiers ou aux données personnelles de l'expert
3. THE Application_Locale SHALL effectuer les vérifications de version exclusivement via le protocole HTTPS

### Exigence 10 : Intégration de la version dans le téléchargement de l'installateur

**User Story :** En tant qu'administrateur du Site Central, je veux que l'endpoint de téléchargement de l'installateur utilise la version publiée, afin que les experts téléchargent toujours la dernière version.

#### Critères d'acceptation

1. WHEN un expert accède à l'endpoint GET `/api/downloads/app`, THE Site_Central SHALL retourner les informations de téléchargement avec la Version_Applicative la plus récente publiée via le modèle AppVersion
2. THE Site_Central SHALL inclure la Version_Applicative dans le nom du fichier installateur retourné (ex : `judi-expert-installer-1.2.0.exe`)
3. WHEN aucune version n'est publiée dans le modèle AppVersion, THE Site_Central SHALL utiliser la version par défaut « 0.1.0 » comme valeur de repli

### Exigence 11 : Centralisation du numéro de version du Site Central

**User Story :** En tant que développeur, je veux que le numéro de version du Site Central soit défini dans un fichier unique, afin de pouvoir suivre les déploiements et garantir la cohérence entre les composants du Site Central.

#### Critères d'acceptation

1. THE Site_Central SHALL définir la Version_Site_Central dans un fichier unique `central-site/VERSION` contenant le numéro de version au format semver (MAJOR.MINOR.PATCH) sur la première ligne et la date de publication au format ISO (YYYY-MM-DD) sur la deuxième ligne
2. WHEN le backend FastAPI du Site Central démarre, THE Site_Central SHALL lire la Version_Site_Central depuis le fichier `VERSION` et l'exposer via la variable `APP_VERSION`
3. WHEN le fichier `central-site/VERSION` est absent ou illisible, THE Site_Central SHALL refuser de démarrer et afficher un message d'erreur indiquant que le fichier de version est manquant
4. THE Site_Central SHALL exposer un endpoint GET `/api/health` retournant la Version_Site_Central dans le champ `version` en complément du statut existant

### Exigence 12 : Affichage de la version du Site Central dans l'interface

**User Story :** En tant qu'administrateur du Site Central, je veux voir la version du Site Central dans l'interface, afin de vérifier quel déploiement est actif en production.

#### Critères d'acceptation

1. THE Site_Central SHALL afficher la Version_Site_Central dans le pied de page (footer) de toutes les pages au format « Site Central V{MAJOR}.{MINOR}.{PATCH} - {date_version} » où {date_version} est la date de publication au format « {jour} {mois} {année} » (ex : « Site Central V1.2.0 - 17 avril 2026 »)
2. THE Site_Central SHALL exposer la Version_Site_Central au frontend via l'endpoint GET `/api/health` existant, enrichi du champ `version`
3. THE Page_Admin SHALL afficher la Version_Site_Central et la dernière Version_Applicative publiée dans un encart récapitulatif

### Exigence 13 : Cohérence de version lors du déploiement du Site Central

**User Story :** En tant que développeur, je veux que les scripts de déploiement du Site Central utilisent le fichier VERSION comme source unique, afin d'éviter les incohérences entre le code déployé et la version affichée.

#### Critères d'acceptation

1. WHEN les scripts de déploiement du Site Central (build.sh, push-ecr.sh, deploy.sh) sont exécutés, THE scripts SHALL lire la Version_Site_Central depuis le fichier `central-site/VERSION`
2. THE scripts de déploiement SHALL taguer les images Docker du Site Central avec la Version_Site_Central (ex : `judi-central-backend:1.2.0`)
3. WHEN le script docker-compose.dev.yml est utilisé en développement, THE Site_Central SHALL lire la Version_Site_Central depuis le fichier `VERSION` de la même manière qu'en production

### Exigence 14 : Fichier VERSION dans le package installateur (app_locale_package)

**User Story :** En tant que développeur, je veux que le package installateur contienne un fichier VERSION identique à celui de local-site, afin que l'installateur connaisse la version qu'il installe.

#### Critères d'acceptation

1. THE app_locale_package SHALL contenir un fichier `VERSION` au format identique à `local-site/VERSION` (semver sur la première ligne, date ISO sur la deuxième ligne)
2. WHEN le script package.sh génère l'installateur, THE script SHALL copier le fichier `local-site/VERSION` dans le package
3. THE fichier `central-site/app_locale_package/VERSION` SHALL être synchronisé avec `local-site/VERSION` à chaque release

### Exigence 15 : Documentation de la gestion des versions

**User Story :** En tant que développeur, je veux une documentation centralisée décrivant le système de gestion des versions, afin de comprendre rapidement le fonctionnement et les conventions.

#### Critères d'acceptation

1. THE projet SHALL contenir un fichier `docs/version-management.md` décrivant le système complet de gestion des versions
2. THE documentation SHALL décrire le format du fichier VERSION, les conventions semver, le processus de mise à jour forcée, la mise à jour du modèle LLM, et l'affichage de la version dans l'interface
3. THE documentation SHALL inclure des exemples concrets de fichiers VERSION et de commandes de publication de version
