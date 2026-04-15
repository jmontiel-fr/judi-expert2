"""Service de lecture et parsing du fichier domaines.yaml."""

from pathlib import Path
from typing import Any

import yaml

# Chemin vers domaines.yaml : configurable via variable d'environnement ou chemin par défaut
import os

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DOMAINES_PATH_ENV = os.environ.get("DOMAINES_YAML_PATH")
if _DOMAINES_PATH_ENV:
    _DOMAINES_PATH = Path(_DOMAINES_PATH_ENV)
else:
    # En développement local : remonter depuis central-site/web/backend -> racine
    try:
        _PROJECT_ROOT = _BACKEND_DIR.parents[2]
        _DOMAINES_PATH = _PROJECT_ROOT / "domaines" / "domaines.yaml"
    except IndexError:
        # En conteneur Docker : /app/ est le répertoire de travail
        _DOMAINES_PATH = Path("/data/domaines/domaines.yaml")


def load_domaines(domaines_path: Path | None = None) -> list[dict[str, Any]]:
    """Lit et parse le fichier domaines.yaml.

    Args:
        domaines_path: Chemin optionnel vers le fichier. Par défaut, utilise
            le chemin standard relatif à la racine du projet.

    Returns:
        Liste des configurations de domaines.

    Raises:
        FileNotFoundError: Si le fichier domaines.yaml n'existe pas.
        ValueError: Si le fichier est mal formé.
    """
    path = domaines_path or _DOMAINES_PATH

    if not path.exists():
        raise FileNotFoundError(f"Fichier domaines.yaml introuvable : {path}")

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or "domaines" not in data:
        raise ValueError("Le fichier domaines.yaml doit contenir une clé 'domaines'")

    domaines = data["domaines"]
    if not isinstance(domaines, list):
        raise ValueError("La clé 'domaines' doit contenir une liste")

    return domaines
