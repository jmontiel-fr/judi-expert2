# Gestion des Versions — Judi-Expert

Ce document décrit le système complet de gestion des versions pour Judi-Expert, couvrant le versionnage de l'Application Locale, du Site Central, et du modèle LLM.

---

## 1. Format du fichier VERSION

Chaque composant possède un fichier `VERSION` servant de **source unique de vérité** pour le numéro de version.

### Structure

Le fichier contient exactement **2 lignes** :

```
MAJOR.MINOR.PATCH
YYYY-MM-DD
```

- **Ligne 1** : numéro de version au format [semver](https://semver.org/) (ex : `1.0.0`)
- **Ligne 2** : date de publication au format ISO 8601 (ex : `2026-05-08`)

### Emplacements

| Fichier | Composant | Description |
|---------|-----------|-------------|
| `local-site/VERSION` | Application Locale | Version de l'application installée sur le PC de l'expert |
| `central-site/VERSION` | Site Central | Version du Site Central déployé sur AWS |
| `central-site/app_locale_package/VERSION` | Package installateur | Copie de `local-site/VERSION`, synchronisée à chaque release |

> **Important** : Le fichier `central-site/app_locale_package/VERSION` doit **toujours** être synchronisé avec `local-site/VERSION`. Le script `package.sh` effectue cette copie automatiquement lors de la génération de l'installateur.

### Exemple concret

```
1.0.0
2026-05-08
```

Ce fichier indique la version `1.0.0` publiée le 8 mai 2026.

### Comportement au démarrage

- Le backend FastAPI lit le fichier `VERSION` au démarrage et expose la version via la variable `APP_VERSION`
- Si le fichier est **absent ou illisible**, l'application refuse de démarrer avec un message d'erreur explicite

---

## 2. Conventions semver

Le projet suit le [Semantic Versioning 2.0.0](https://semver.org/) :

| Composant | Quand incrémenter | Exemples |
|-----------|-------------------|----------|
| **MAJOR** | Changements incompatibles (breaking changes) | Refonte de l'API, suppression de fonctionnalités, changement de format de données |
| **MINOR** | Nouvelles fonctionnalités rétrocompatibles | Ajout d'un endpoint, nouvelle page, amélioration d'un workflow |
| **PATCH** | Corrections de bugs | Fix d'un crash, correction d'affichage, patch de sécurité |

### Règles

- La version initiale est `1.0.0`
- Les versions de pré-release ne sont pas utilisées en production
- L'Application Locale et le Site Central ont des versions **indépendantes**
- Le format est strictement `X.Y.Z` (3 nombres entiers non-négatifs séparés par des points)

---

## 3. Processus de publication d'une version

### Qui publie ?

Seul un **Administrateur Central** (authentifié via AWS Cognito) peut publier une nouvelle version de l'Application Locale.

### Comment publier ?

L'administrateur publie via l'endpoint `POST /api/admin/versions` du Site Central :

```bash
curl -X POST https://central.judi-expert.fr/api/admin/versions \
  -H "Authorization: Bearer <token_admin>" \
  -H "Content-Type: application/json" \
  -d '{
    "version": "1.1.0",
    "download_url": "https://s3.eu-west-1.amazonaws.com/judi-expert-production-assets/packages/local/judi-expert-local-1.1.0.tar.gz",
    "mandatory": true,
    "release_notes": "Ajout du workflow psychiatrie et corrections de bugs OCR"
  }'
```

### Paramètres de la requête

| Champ | Type | Obligatoire | Description |
|-------|------|-------------|-------------|
| `version` | string | Oui | Numéro de version semver (validé par regex `^\d+\.\d+\.\d+$`) |
| `download_url` | string | Oui | URL de téléchargement du package d'images Docker |
| `mandatory` | bool | Non (défaut: `true`) | Si `true`, la mise à jour est bloquante |
| `release_notes` | string | Non | Notes de version (Markdown) |

### Stockage

Les versions publiées sont stockées dans le modèle `AppVersion` en base PostgreSQL :

| Champ | Type | Description |
|-------|------|-------------|
| `id` | int | Identifiant auto-incrémenté |
| `version` | string(20) | Numéro semver |
| `download_url` | string(500) | URL de téléchargement |
| `mandatory` | bool | Mise à jour obligatoire |
| `release_notes` | text | Notes de version |
| `published_at` | datetime | Date de publication (automatique) |

### Consultation de la dernière version

L'endpoint `GET /api/version` retourne toujours la **dernière version publiée** :

```bash
curl https://central.judi-expert.fr/api/version
```

Réponse :

```json
{
  "latest_version": "1.1.0",
  "download_url": "https://s3.eu-west-1.amazonaws.com/judi-expert-production-assets/packages/local/judi-expert-local-1.1.0.tar.gz",
  "mandatory": true,
  "release_notes": "Ajout du workflow psychiatrie et corrections de bugs OCR"
}
```

---

## 4. Processus de mise à jour forcée

### Déclenchement

Au démarrage, l'Application Locale effectue les vérifications suivantes :

1. **Vérification des heures ouvrables** : la communication avec le Site Central n'est autorisée qu'entre 8h et 20h (Europe/Paris). En dehors de cette plage, l'application démarre normalement.
2. **Interrogation du Site Central** : `GET /api/version` via le `SiteCentralClient` (avec retry et backoff exponentiel).
3. **Comparaison des versions** : si la version locale est inférieure à `latest_version` ET `mandatory = true`, une mise à jour forcée est déclenchée.

### Déroulement de la mise à jour

```
┌─────────────────────────────────────────────────────────┐
│  Écran de Mise à Jour (bloquant)                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. Téléchargement des images Docker    [████████░░] 80%│
│  2. Arrêt des conteneurs                [          ]  0%│
│  3. Chargement des nouvelles images     [          ]  0%│
│  4. Redémarrage des conteneurs          [          ]  0%│
│                                                         │
│  Mise à jour en cours... Veuillez patienter.            │
└─────────────────────────────────────────────────────────┘
```

**Étapes détaillées :**

1. **Téléchargement** : récupération de l'archive d'images Docker depuis `download_url`
2. **Arrêt** : `docker compose down` (arrêt des conteneurs existants)
3. **Chargement** : `docker load` des nouvelles images
4. **Redémarrage** : `docker compose up -d` avec les nouvelles images

### Rollback en cas d'échec

Si une étape échoue :
- Les conteneurs précédents sont restaurés
- Un message d'erreur est affiché avec un bouton « Réessayer »
- L'expert peut continuer à utiliser la version précédente

### Préservation des données

Les **volumes Docker** sont toujours préservés pendant la mise à jour :
- `web_data` : base SQLite (dossiers, configuration)
- `dossiers_data` : fichiers des dossiers d'expertise
- `ollama_data` : modèle LLM téléchargé
- `qdrant_data` : index vectoriel RAG

> **Aucune donnée de dossier n'est perdue** lors d'une mise à jour.

### Isolation des données

Les requêtes de vérification de version ne transmettent **que** la version courante (`current_version`). Aucune donnée de dossier, aucun identifiant d'expert ne transite vers le Site Central. Toutes les communications se font exclusivement via HTTPS.

---

## 5. Mise à jour du modèle LLM

Le modèle LLM (Mistral 7B Instruct) est géré indépendamment de l'application, via le conteneur Ollama.

### Vérification au démarrage

Au démarrage du conteneur `judi-llm`, le script `ollama-entrypoint.sh` :

1. Démarre le serveur Ollama
2. Compare le **digest SHA256** du modèle local avec le digest distant sur le registre Ollama
3. Si un nouveau modèle est disponible, lance le téléchargement en arrière-plan

### Téléchargement non-bloquant

- Le téléchargement s'effectue en **arrière-plan** : l'expert continue à travailler avec le modèle courant
- La progression est suivie via un fichier d'état JSON
- Le nouveau modèle sera **activé au prochain redémarrage** du conteneur

### Fichier d'état

Le fichier `/root/.ollama/update-status.json` (dans le volume `ollama_data`) contient l'état de la mise à jour :

```json
{
  "status": "downloading",
  "progress": 45,
  "model": "mistral:7b-instruct-v0.3-q4_0",
  "started_at": "2026-05-08T10:30:00Z",
  "error": null
}
```

| Statut | Description |
|--------|-------------|
| `idle` | Pas de mise à jour en cours, modèle à jour |
| `downloading` | Téléchargement en cours |
| `ready` | Nouveau modèle téléchargé, activation au prochain redémarrage |
| `error` | Échec du téléchargement (le modèle courant reste actif) |

### Endpoint de suivi

Le backend expose `GET /api/llm/update-status` pour que le frontend affiche la progression :
- Pendant le téléchargement : barre de progression sur la page de connexion
- Quand prêt : message « Nouveau modèle prêt — sera activé au prochain redémarrage »

### En cas d'échec

Si le téléchargement échoue, l'erreur est journalisée et le modèle courant continue à fonctionner normalement. Aucune intervention manuelle n'est requise.

---

## 6. Affichage de la version dans l'interface

### Format d'affichage

```
V{MAJOR}.{MINOR}.{PATCH} - {jour} {mois} {année}
```

Les mois sont affichés en français :

| Mois | Affichage |
|------|-----------|
| 01 | janvier |
| 02 | février |
| 03 | mars |
| 04 | avril |
| 05 | mai |
| 06 | juin |
| 07 | juillet |
| 08 | août |
| 09 | septembre |
| 10 | octobre |
| 11 | novembre |
| 12 | décembre |

### Exemples

- **Application Locale** : `App Locale V1.0.0 - 8 mai 2026`
- **Site Central** : `Site Central V1.0.0 - 8 mai 2026`

### Emplacement

La version est affichée dans le **footer** (pied de page) de toutes les pages :
- À gauche : copyright (`© 2026 Judi-Expert`)
- Suivi de la version formatée

### Source des données

| Site | Endpoint | Champ |
|------|----------|-------|
| Application Locale | `GET /api/version` | `current_version` + `current_date` |
| Site Central | `GET /api/health` | `version` |

---

## 7. Exemples concrets

### Contenu d'un fichier VERSION

```
1.0.0
2026-05-08
```

### Publier une nouvelle version (admin)

```bash
# Authentification (récupérer un token admin via Cognito)
TOKEN="eyJhbGciOiJSUzI1NiIs..."

# Publication de la version 1.1.0
curl -X POST https://central.judi-expert.fr/api/admin/versions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "version": "1.1.0",
    "download_url": "https://s3.eu-west-1.amazonaws.com/judi-expert-production-assets/packages/local/judi-expert-local-1.1.0.tar.gz",
    "mandatory": true,
    "release_notes": "## Nouveautés\n- Ajout du domaine psychiatrie\n- Amélioration de l OCR\n\n## Corrections\n- Fix crash au step 3"
  }'
```

Réponse :

```json
{
  "id": 2,
  "version": "1.1.0",
  "download_url": "https://s3.eu-west-1.amazonaws.com/judi-expert-production-assets/packages/local/judi-expert-local-1.1.0.tar.gz",
  "mandatory": true,
  "release_notes": "## Nouveautés\n- Ajout du domaine psychiatrie\n- Amélioration de l OCR\n\n## Corrections\n- Fix crash au step 3",
  "published_at": "2026-06-15T14:30:00Z"
}
```

### Consulter la dernière version publiée

```bash
curl https://central.judi-expert.fr/api/version
```

Réponse :

```json
{
  "latest_version": "1.1.0",
  "download_url": "https://s3.eu-west-1.amazonaws.com/judi-expert-production-assets/packages/local/judi-expert-local-1.1.0.tar.gz",
  "mandatory": true,
  "release_notes": "## Nouveautés\n- Ajout du domaine psychiatrie\n- Amélioration de l OCR\n\n## Corrections\n- Fix crash au step 3"
}
```

### Vérifier la version du Site Central

```bash
curl https://central.judi-expert.fr/api/health
```

Réponse :

```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### Vérifier l'état de mise à jour du modèle LLM

```bash
curl http://localhost:8000/api/llm/update-status
```

Réponse (téléchargement en cours) :

```json
{
  "status": "downloading",
  "progress": 67,
  "current_model": "mistral:7b-instruct-v0.3-q4_0",
  "error_message": null
}
```

---

## Références

- [Semantic Versioning 2.0.0](https://semver.org/)
- [ISO 8601 — Format de date](https://fr.wikipedia.org/wiki/ISO_8601)
- Architecture détaillée : `docs/architecture.md`
- Guide de développement : `docs/developpement.md`
