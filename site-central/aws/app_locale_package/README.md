# Judi-Expert — Packaging de l'Application Locale

Ce répertoire contient les scripts et fichiers nécessaires pour produire
les installateurs autonomes de l'Application Locale Judi-Expert.

## Structure

```
app_locale_package/
├── package.sh                  # Script principal de packaging
├── nsis/
│   └── judi-expert-installer.nsi  # Script NSIS (installateur Windows)
├── unix/
│   └── install.sh              # Script shell auto-extractible (macOS/Linux)
├── common/
│   ├── prerequisites_check.py  # Vérification des prérequis système
│   ├── amorce.sh               # Lanceur Amorce (macOS/Linux)
│   ├── amorce.bat              # Lanceur Amorce (Windows)
│   └── default.env             # Configuration .env par défaut
├── output/                     # Installateurs générés (gitignored)
└── README.md
```

## Prérequis de build

- **Docker** : installé et en cours d'exécution (pour construire et exporter les images)
- **NSIS** (optionnel) : requis uniquement pour générer l'installateur Windows
  - Installation : https://nsis.sourceforge.io/ (gratuit, licence zlib/libpng)
  - Sur Linux/macOS : `apt install nsis` ou `brew install nsis`

## Utilisation

### Générer tous les installateurs

```bash
./package.sh
```

### Générer pour un OS spécifique

```bash
./package.sh linux          # Linux uniquement
./package.sh macos          # macOS uniquement
./package.sh windows        # Windows uniquement (nécessite NSIS)
./package.sh linux macos    # Linux et macOS
```

### Options

```bash
./package.sh --version 2.0.0 all     # Spécifier la version
./package.sh --skip-build linux      # Ne pas reconstruire les images Docker
./package.sh --skip-export macos     # Utiliser les images Docker en cache
```

## Contenu de l'installateur

Chaque installateur embarque :

1. **Amorce** : script lanceur qui vérifie Docker et démarre les conteneurs
2. **Images Docker** : fichiers `.tar` des 5 images (web-backend, web-frontend, ocr, ollama, qdrant)
3. **Configuration** : `docker-compose.yml` et `.env` par défaut
4. **Runtime Docker** : téléchargement et installation automatique si absent

## Processus d'installation (côté Expert)

1. L'installateur vérifie les prérequis système (CPU ≥ 4, RAM ≥ 8 Go, disque ≥ 50 Go, chiffrement actif)
2. Si les prérequis ne sont pas satisfaits, un message d'erreur détaillé est affiché et l'installation est interrompue
3. Docker est installé automatiquement si absent
4. Les images Docker sont chargées depuis les fichiers `.tar` embarqués
5. Les fichiers de configuration sont déployés
6. Un raccourci/lanceur est créé

## Outils utilisés

| Outil | Licence | Usage |
|-------|---------|-------|
| NSIS | zlib/libpng (open-source) | Installateur Windows |
| Shell script | — | Installateur macOS/Linux (auto-extractible) |
| Docker | Apache 2.0 | Runtime conteneurs |
| tar/gzip | GPL | Compression de l'archive |

Tous les outils sont gratuits et compatibles avec un usage commercial.
