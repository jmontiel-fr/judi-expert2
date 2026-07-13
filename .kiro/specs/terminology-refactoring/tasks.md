# Implementation Plan: Terminology Refactoring

## Overview

Ce plan implémente le refactoring terminologique pour éliminer l'ambiguïté du terme « local » dans le projet Judi-Expert. L'approche est phasée : renommages structurels (git mv) d'abord, puis mises à jour de contenu par catégorie, puis validation. Aucune modification fonctionnelle n'est introduite.

## Tasks

- [x] 1. Renommage des répertoires et fichiers (git mv)
  - [x] 1.1 Renommer le répertoire principal `local-site/` en `client-site/`
    - Exécuter `git mv local-site/ client-site/`
    - Vérifier que la structure interne est préservée intégralement
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 1.2 Renommer le répertoire de packaging `central-site/app_locale_package/` en `central-site/app_client_package/`
    - Exécuter `git mv central-site/app_locale_package/ central-site/app_client_package/`
    - Vérifier que le contenu (scripts NSIS, scripts shell, configs) est préservé
    - _Requirements: 7.1, 7.2_

  - [x] 1.3 Renommer les scripts de développement dans `scripts-dev/`
    - Exécuter `git mv scripts-dev/dev-local-start.sh scripts-dev/dev-client-start.sh`
    - Exécuter `git mv scripts-dev/dev-local-stop.sh scripts-dev/dev-client-stop.sh`
    - Exécuter `git mv scripts-dev/dev-local-restart.sh scripts-dev/dev-client-restart.sh`
    - Exécuter `git mv scripts-dev/dev-local-status.sh scripts-dev/dev-client-status.sh`
    - Exécuter `git mv scripts-dev/build-and-deploy-local.sh scripts-dev/build-and-deploy-client.sh`
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 2. Mise à jour du contenu des scripts de développement
  - [x] 2.1 Mettre à jour le contenu de `scripts-dev/dev-client-start.sh`
    - Remplacer les chemins `local-site/` par `client-site/` (docker-compose.yml, docker-compose.gpu.yml)
    - Remplacer les messages « Application Locale » → « Site Client », « Judi-Expert Local » → « Judi-Expert Client »
    - Mettre à jour les références internes au nom du script (`dev-local-start.sh` → `dev-client-start.sh`)
    - _Requirements: 3.1, 3.2, 2.5_

  - [x] 2.2 Mettre à jour le contenu de `scripts-dev/dev-client-stop.sh`
    - Remplacer les chemins `local-site/` par `client-site/`
    - Remplacer les messages « Application Locale » / « local » au sens composant → « Site Client » / « client »
    - Mettre à jour les références au nom du script
    - _Requirements: 3.1, 3.2, 2.5_

  - [x] 2.3 Mettre à jour le contenu de `scripts-dev/dev-client-restart.sh`
    - Mêmes patterns de remplacement que pour stop/start (chemins + messages)
    - _Requirements: 3.1, 3.2, 2.5_

  - [x] 2.4 Mettre à jour le contenu de `scripts-dev/dev-client-status.sh`
    - Mêmes patterns de remplacement (chemins + messages)
    - _Requirements: 3.1, 3.2, 2.5_

  - [x] 2.5 Mettre à jour `scripts-dev/_common.sh`
    - Remplacer les références `dev-local-start.sh` → `dev-client-start.sh` dans `show_help` et messages
    - Remplacer « Application Locale » → « Site Client » dans les messages d'aide
    - Remplacer les chemins `local-site/` → `client-site/` si présents
    - _Requirements: 2.5, 3.2_

  - [x] 2.6 Mettre à jour `scripts-dev/build-and-deploy-client.sh`
    - Remplacer les chemins `local-site/` → `client-site/`
    - Remplacer les noms d'images/artefacts `judi-expert-local-*` → `judi-expert-client-*`
    - Remplacer `packages/local/` → `packages/client/` pour les chemins S3
    - _Requirements: 3.1, 8.1, 8.2, 8.3_

- [x] 3. Checkpoint - Vérifier les scripts
  - Vérifier que les scripts renommés sont syntaxiquement valides (`bash -n scripts-dev/dev-client-*.sh`)
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Mise à jour du packaging et Docker
  - [x] 4.1 Mettre à jour `central-site/app_client_package/package.sh`
    - Renommer la variable `LOCAL_DIR` → `CLIENT_DIR` avec chemin `$PROJECT_ROOT/client-site`
    - Mettre à jour `VERSION_FILE` : `local-site/VERSION` → `client-site/VERSION`
    - Remplacer les messages « Application Locale » → « Site Client »
    - Remplacer toutes les références `$LOCAL_DIR` → `$CLIENT_DIR`
    - Renommer les patterns d'artefacts `judi-expert-local-*` → `judi-expert-client-*`
    - _Requirements: 7.3, 8.1, 8.3_

  - [x] 4.2 Mettre à jour `central-site/app_client_package/nsis/judi-expert-installer.nsi`
    - Remplacer les noms de fichiers output contenant « local » → « client »
    - Remplacer les chaînes d'affichage « Application Locale » → « Site Client »
    - _Requirements: 7.3, 8.1_

  - [x] 4.3 Mettre à jour `client-site/docker-compose.yml` (commentaires uniquement)
    - Remplacer le commentaire « Application Locale Docker Compose » → « Site Client Docker Compose »
    - Remplacer « Orchestre les conteneurs de l'Application Locale » → « Orchestre les conteneurs du Site Client »
    - Ne PAS modifier les noms de services, conteneurs, volumes ou ports
    - _Requirements: 9.1, 9.2_

  - [x] 4.4 Mettre à jour `client-site/.env` (commentaires uniquement)
    - Remplacer le commentaire « Application Locale (.env) » → « Site Client (.env) »
    - Ne PAS modifier les variables d'environnement
    - _Requirements: 9.2_

  - [x] 4.5 Mettre à jour `central-site/docker-compose.dev.yml` (commentaires/références)
    - Remplacer les commentaires « Application Locale » → « Site Client »
    - Remplacer les références `local-site/` → `client-site/` si présentes
    - _Requirements: 9.3_

- [x] 5. Mise à jour de la documentation
  - [x] 5.1 Mettre à jour les fichiers `docs/*.md` (search-and-replace)
    - Remplacer « Application Locale » → « Site Client » (respecter la casse)
    - Remplacer « application locale » → « Site Client »
    - Remplacer `local-site/` → `client-site/`
    - Remplacer `dev-local-` → `dev-client-`
    - Remplacer `app_locale_package` → `app_client_package`
    - Remplacer `judi-expert-local-` → `judi-expert-client-`
    - Remplacer `packages/local/` → `packages/client/`
    - Conserver « mode local », « déploiement local », « localhost » inchangés
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 5.2 Mettre à jour les fichiers `.kiro/steering/*.md`
    - Mettre à jour `structure.md` : arborescence `local-site/` → `client-site/`, convention packages `local` → `client`, chemins S3
    - Mettre à jour `tech.md` : commandes dev `dev-local-*` → `dev-client-*`, chemins, commentaires
    - Mettre à jour `product.md` : « Application Locale » → « Site Client »
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

- [x] 6. Mise à jour de l'interface utilisateur
  - [x] 6.1 Mettre à jour le frontend du Site Client (`client-site/web/frontend/src/`)
    - Rechercher et remplacer « Application Locale » → « Site Client » dans les chaînes i18n/textes
    - Mettre à jour les titres de pages, labels de navigation, textes descriptifs
    - Vérifier que « Site Central » est utilisé pour les références au composant central
    - _Requirements: 5.1, 5.2, 5.3_

  - [x] 6.2 Mettre à jour le frontend du Site Central (`central-site/web/frontend/src/`)
    - Remplacer les chaînes « Application Locale » → « Site Client » dans les textes
    - Mettre à jour les pages de téléchargement et tableau de bord admin
    - Mettre à jour les noms de fichiers de téléchargement affichés (`judi-expert-local-*` → `judi-expert-client-*`)
    - _Requirements: 6.1, 6.2_

- [x] 7. Mise à jour Terraform et chemins S3
  - [x] 7.1 Mettre à jour les fichiers Terraform (`central-site/terraform/`)
    - Remplacer les variables et chemins S3 `packages/local/` → `packages/client/`
    - Remplacer les noms d'artefacts `judi-expert-local-*` → `judi-expert-client-*`
    - Remplacer les références `local-site/` → `client-site/` dans les commentaires ou descriptions
    - _Requirements: 8.2_

- [x] 8. Checkpoint - Validation intermédiaire
  - Vérifier la syntaxe de tous les scripts modifiés (`bash -n`)
  - Vérifier que `docker-compose.yml` est valide (`docker compose config` dans `client-site/`)
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Script de validation et tests
  - [x] 9.1 Créer et exécuter un script de validation post-refactoring
    - Vérifier que `local-site/` n'existe plus
    - Vérifier qu'aucun `scripts-dev/dev-local-*` n'existe
    - Vérifier que `central-site/app_locale_package/` n'existe plus
    - Exécuter un grep exhaustif pour détecter les occurrences résiduelles de `local-site`, `dev-local-`, `app_locale_package`, `judi-expert-local-` dans les fichiers source
    - Distinguer les faux positifs (mode de déploiement « local ») des vrais oublis
    - _Requirements: 11.1, 11.2_

  - [x] 9.2 Exécuter les tests unitaires existants
    - Lancer `pytest tests/unit/ -v` et vérifier que tous les tests passent sans modification
    - _Requirements: 11.1_

  - [x] 9.3 Exécuter les tests property et smoke existants
    - Lancer `pytest tests/property/ -v` et `pytest tests/smoke/ -v`
    - Confirmer zéro régression fonctionnelle
    - _Requirements: 11.1_

- [x] 10. Final checkpoint - Validation complète
  - Ensure all tests pass, ask the user if questions arise.
  - Vérifier que le script de validation (9.1) retourne zéro occurrence résiduelle
  - Le refactoring est terminé quand aucun fichier ne contient « local » au sens du composant client

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Aucune modification fonctionnelle — uniquement des renommages et mises à jour de texte
- Le terme « local » dans le sens mode de déploiement dev (localhost) reste inchangé
- Les noms de services Docker, variables d'environnement, ports, volumes et réseaux ne sont PAS modifiés
- Les migrations Alembic ne sont pas nécessaires (aucun changement de schéma)
- Property-based testing ne s'applique pas à ce refactoring (opération de renommage textuel)
- Utiliser `git mv` pour tous les renommages de fichiers/répertoires afin de préserver l'historique Git

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["2.1", "2.2", "2.3", "2.4", "2.5", "2.6"] },
    { "id": 2, "tasks": ["4.1", "4.2", "4.3", "4.4", "4.5"] },
    { "id": 3, "tasks": ["5.1", "5.2", "6.1", "6.2", "7.1"] },
    { "id": 4, "tasks": ["9.1"] },
    { "id": 5, "tasks": ["9.2", "9.3"] }
  ]
}
```
