# Requirements Document

## Introduction

Refactoring terminologique du projet Judi-Expert pour éliminer l'ambiguïté du terme « local ». Actuellement, « local » désigne à la fois le composant client (Application Locale installée chez l'expert) et le mode de déploiement dev (exécution sur le PC du développeur en localhost). Ce refactoring introduit une séparation claire :

- **site-client** : le composant installé sur le PC de l'expert (anciennement « Application Locale » / « local-site »)
- **site-central** : le composant hébergé sur AWS (inchangé dans le concept, clarifié dans la nomenclature)
- **local** : réservé exclusivement au mode de déploiement dev (communication en localhost sur le PC du développeur)
- **prod (aws)** : mode de déploiement production (communication entre judi-expert.fr et le PC de l'expert)

## Glossary

- **Site_Client** : Composant applicatif installé sur le PC de l'expert judiciaire, orchestrant les conteneurs Docker pour le workflow d'expertise (OCR, LLM, backend, frontend). Anciennement appelé « Application Locale » ou « local-site ».
- **Site_Central** : Plateforme web hébergée sur AWS, gérant l'inscription des experts, les paiements, la distribution du corpus RAG et l'administration.
- **Mode_Local** : Mode de déploiement développeur où le Site_Client et le Site_Central communiquent en localhost sur le même PC.
- **Mode_Prod** : Mode de déploiement production où le Site_Central est accessible via judi-expert.fr et le Site_Client est installé sur le PC de l'expert.
- **Arborescence** : Structure des répertoires et fichiers du dépôt Git.
- **Scripts_Dev** : Ensemble des scripts shell dans le répertoire `scripts-dev/` utilisés pour le développement.
- **Documentation** : Fichiers Markdown dans le répertoire `docs/` décrivant l'architecture, le développement, l'exploitation et l'utilisation.
- **UI_Client** : Interface utilisateur frontend du Site_Client (Next.js PWA sur le PC de l'expert).
- **UI_Central** : Interface utilisateur frontend du Site_Central (Next.js PWA hébergée sur AWS).
- **Package_Installateur** : Répertoire et artefacts de packaging de l'installateur pour le Site_Client (NSIS pour Windows, shell pour Unix).

## Requirements

### Requirement 1: Renommage du répertoire principal du Site Client

**User Story:** En tant que développeur, je veux que le répertoire racine du Site Client soit nommé `client-site/` au lieu de `local-site/`, afin que la structure du dépôt reflète la terminologie officielle et ne crée pas de confusion avec le mode de déploiement local.

#### Acceptance Criteria

1. WHEN le refactoring est appliqué, THE Arborescence SHALL contenir un répertoire `client-site/` à la racine du dépôt à la place de `local-site/`
2. WHEN le refactoring est appliqué, THE Arborescence SHALL ne plus contenir de répertoire `local-site/` à la racine du dépôt
3. WHEN le répertoire est renommé, THE Arborescence SHALL préserver l'intégralité du contenu et de la structure interne de l'ancien répertoire `local-site/`

### Requirement 2: Renommage des scripts de développement

**User Story:** En tant que développeur, je veux que les scripts de développement utilisent « client » au lieu de « local » dans leurs noms de fichiers, afin que la convention de nommage soit cohérente avec la nouvelle terminologie.

#### Acceptance Criteria

1. WHEN le refactoring est appliqué, THE Scripts_Dev SHALL renommer `dev-local-start.sh` en `dev-client-start.sh`
2. WHEN le refactoring est appliqué, THE Scripts_Dev SHALL renommer `dev-local-stop.sh` en `dev-client-stop.sh`
3. WHEN le refactoring est appliqué, THE Scripts_Dev SHALL renommer `dev-local-restart.sh` en `dev-client-restart.sh`
4. WHEN le refactoring est appliqué, THE Scripts_Dev SHALL renommer `dev-local-status.sh` en `dev-client-status.sh`
5. WHEN un script est renommé, THE Scripts_Dev SHALL mettre à jour toutes les références internes entre scripts (notamment dans `_common.sh` et les scripts eux-mêmes)

### Requirement 3: Mise à jour du contenu des scripts de développement

**User Story:** En tant que développeur, je veux que le contenu des scripts utilise la terminologie « client-site » pour référencer le répertoire et les services du Site Client, afin que les commandes Docker Compose et les chemins soient corrects après le renommage.

#### Acceptance Criteria

1. WHEN un script référence le répertoire du Site Client, THE Scripts_Dev SHALL utiliser le chemin `client-site/` au lieu de `local-site/`
2. WHEN un script affiche des messages ou des labels de statut, THE Scripts_Dev SHALL utiliser « Site Client » ou « client » au lieu de « Application Locale » ou « local » pour désigner le composant
3. WHEN un script référence des noms de conteneurs ou services Docker, THE Scripts_Dev SHALL utiliser un préfixe ou suffixe cohérent avec « client » au lieu de « local »

### Requirement 4: Mise à jour de la documentation

**User Story:** En tant que développeur ou utilisateur, je veux que toute la documentation dans `docs/` utilise « Site Client » et « Site Central » comme terminologie officielle, afin que la documentation soit claire et non ambiguë.

#### Acceptance Criteria

1. WHEN la documentation mentionne le composant installé chez l'expert, THE Documentation SHALL utiliser le terme « Site Client » au lieu de « Application Locale »
2. WHEN la documentation mentionne le répertoire du Site Client, THE Documentation SHALL référencer `client-site/` au lieu de `local-site/`
3. WHEN la documentation décrit le mode de déploiement développeur, THE Documentation SHALL utiliser « mode local » ou « déploiement local » exclusivement pour désigner l'exécution en localhost sur le PC du développeur
4. WHEN la documentation décrit le mode de déploiement production, THE Documentation SHALL utiliser « mode prod » ou « déploiement AWS » pour désigner la communication entre judi-expert.fr et le PC de l'expert
5. WHEN la documentation référence les scripts de développement, THE Documentation SHALL utiliser les nouveaux noms (`dev-client-start.sh`, `dev-client-stop.sh`, etc.)

### Requirement 5: Mise à jour de l'interface utilisateur du Site Client

**User Story:** En tant qu'expert judiciaire, je veux que l'interface du Site Client affiche « Site Client » comme terminologie, afin que l'affichage soit cohérent avec la documentation et le Site Central.

#### Acceptance Criteria

1. WHEN l'UI du Site Client affiche un titre, un label ou un texte descriptif faisant référence au composant, THE UI_Client SHALL utiliser « Site Client » au lieu de « Application Locale »
2. WHEN l'UI du Site Client affiche un lien ou une référence vers le Site Central, THE UI_Client SHALL utiliser le terme « Site Central »
3. WHEN l'UI du Site Client affiche des informations sur le mode de déploiement, THE UI_Client SHALL distinguer clairement « mode local (dev) » de « Site Client »

### Requirement 6: Mise à jour de l'interface utilisateur du Site Central

**User Story:** En tant qu'administrateur ou expert, je veux que l'interface du Site Central utilise « Site Client » pour désigner le composant installé chez l'expert, afin que la terminologie soit cohérente sur l'ensemble de la plateforme.

#### Acceptance Criteria

1. WHEN l'UI du Site Central affiche un texte faisant référence au composant installé chez l'expert, THE UI_Central SHALL utiliser « Site Client » au lieu de « Application Locale »
2. WHEN l'UI du Site Central affiche un lien de téléchargement ou une référence au package installateur, THE UI_Central SHALL utiliser la terminologie « Site Client »

### Requirement 7: Renommage du package installateur

**User Story:** En tant que développeur, je veux que le répertoire de packaging de l'installateur soit renommé de `app_locale_package/` en `app_client_package/`, afin que le nommage reflète la nouvelle terminologie.

#### Acceptance Criteria

1. WHEN le refactoring est appliqué, THE Arborescence SHALL contenir un répertoire `central-site/app_client_package/` à la place de `central-site/app_locale_package/`
2. WHEN le répertoire est renommé, THE Package_Installateur SHALL préserver l'intégralité du contenu (scripts NSIS, scripts shell, fichiers de configuration)
3. WHEN les scripts de packaging référencent le composant client, THE Package_Installateur SHALL utiliser « client » au lieu de « locale » dans les noms de fichiers générés et les messages

### Requirement 8: Mise à jour de la convention de nommage des packages

**User Story:** En tant que développeur, je veux que la convention de nommage des archives et installateurs utilise « client » au lieu de « local », afin que les artefacts de build soient cohérents avec la terminologie.

#### Acceptance Criteria

1. WHEN un package est généré pour le Site Client, THE Package_Installateur SHALL nommer l'artefact selon le pattern `judi-expert-client-{version}.{ext}` au lieu de `judi-expert-local-{version}.{ext}`
2. WHEN le bucket S3 est structuré pour les packages, THE Package_Installateur SHALL utiliser le chemin `packages/client/` au lieu de `packages/local/`
3. WHEN les images Docker du Site Client sont archivées, THE Package_Installateur SHALL utiliser le pattern `judi-expert-client-{service}-{version}.tar.gz` au lieu de `judi-expert-local-{service}-{version}.tar.gz`

### Requirement 9: Mise à jour des fichiers de configuration Docker Compose et .env

**User Story:** En tant que développeur, je veux que les fichiers Docker Compose et .env utilisent la terminologie « client » dans les noms de services, commentaires et variables, afin que la configuration soit cohérente avec le reste du projet.

#### Acceptance Criteria

1. WHEN le fichier `docker-compose.yml` du Site Client définit des services, THE Site_Client SHALL utiliser des noms de services incluant « client » au lieu de « local » si des références au terme « local » au sens composant existent
2. WHEN le fichier `.env` du Site Client contient des commentaires explicatifs, THE Site_Client SHALL utiliser « Site Client » au lieu de « Application Locale » dans ces commentaires
3. WHEN le fichier `docker-compose.dev.yml` du Site Central référence le Site Client, THE Site_Central SHALL utiliser la terminologie « client » au lieu de « local »

### Requirement 10: Mise à jour des fichiers steering et configuration Kiro

**User Story:** En tant que développeur, je veux que les fichiers de steering (`.kiro/steering/`) reflètent la nouvelle terminologie et la nouvelle arborescence, afin que l'assistant IA ait un contexte à jour.

#### Acceptance Criteria

1. WHEN les fichiers steering décrivent la structure du projet, THE Site_Client SHALL être référencé sous le répertoire `client-site/` au lieu de `local-site/`
2. WHEN les fichiers steering listent les commandes de développement, THE Scripts_Dev SHALL être référencés par leurs nouveaux noms (`dev-client-start.sh`, etc.)
3. WHEN les fichiers steering décrivent l'architecture à deux composants, THE Documentation SHALL utiliser « Site Client » au lieu de « Application Locale »
4. WHEN les fichiers steering mentionnent le mode de déploiement local, THE Documentation SHALL clairement indiquer que « local » désigne le mode dev (localhost) et non le composant client

### Requirement 11: Cohérence du terme « local » après refactoring

**User Story:** En tant que développeur, je veux que le terme « local » ne soit plus jamais utilisé pour désigner le composant client dans aucun fichier du dépôt, afin d'éliminer toute ambiguïté.

#### Acceptance Criteria

1. WHEN le refactoring est terminé, THE Arborescence SHALL ne contenir aucune occurrence du terme « local » utilisé pour désigner le composant Site Client (dans les noms de fichiers, répertoires, variables, commentaires ou textes UI)
2. WHILE le terme « local » est utilisé dans le projet, THE Documentation SHALL l'employer exclusivement pour désigner le mode de déploiement dev (exécution en localhost)
3. IF un développeur introduit le terme « local » pour désigner le composant client, THEN THE Documentation SHALL servir de référence pour corriger l'usage vers « client » ou « Site Client »
