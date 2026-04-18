"""Service de lecture/écriture du contenu corpus depuis les fichiers YAML."""

import logging
from datetime import date
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class CorpusContentService:
    """Service de lecture/écriture du contenu corpus depuis les fichiers YAML."""

    def __init__(self, corpus_base_path: Path) -> None:
        self.corpus_base_path = corpus_base_path

    def load_contenu(self, domaine: str) -> list[dict[str, Any]]:
        """Lit et parse le fichier contenu.yaml d'un domaine.

        Args:
            domaine: Nom du domaine (ex: 'psychologie').

        Returns:
            Liste des éléments de contenu, ou liste vide si fichier absent.

        Raises:
            ValueError: Si le fichier YAML est malformé.
        """
        path = self._resolve_contenu_path(domaine)
        if not path.exists():
            return []

        with open(path, encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ValueError(f"Erreur de parsing YAML ({path}): {e}") from e

        if data is None:
            return []

        if not isinstance(data, dict) or "contenu" not in data:
            raise ValueError(
                f"Le fichier {path} doit contenir une clé 'contenu'"
            )

        contenu = data["contenu"]
        if contenu is None:
            return []
        if not isinstance(contenu, list):
            raise ValueError(
                f"La clé 'contenu' dans {path} doit contenir une liste"
            )

        return contenu

    def load_urls(self, domaine: str) -> list[dict[str, Any]]:
        """Lit et parse le fichier urls/urls.yaml d'un domaine.

        Args:
            domaine: Nom du domaine (ex: 'psychologie').

        Returns:
            Liste des entrées URL, ou liste vide si fichier absent.

        Raises:
            ValueError: Si le fichier YAML est malformé.
        """
        path = self._resolve_urls_path(domaine)
        if not path.exists():
            return []

        with open(path, encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ValueError(f"Erreur de parsing YAML ({path}): {e}") from e

        if data is None:
            return []

        if not isinstance(data, dict) or "urls" not in data:
            raise ValueError(
                f"Le fichier {path} doit contenir une clé 'urls'"
            )

        urls = data["urls"]
        if urls is None:
            return []

        if not isinstance(urls, list):
            raise ValueError(
                f"La clé 'urls' dans {path} doit contenir une liste"
            )

        return urls

    def save_pdf(
        self, domaine: str, filename: str, content: bytes
    ) -> dict[str, Any]:
        """Enregistre un PDF dans documents/ et met à jour contenu.yaml.

        Args:
            domaine: Nom du domaine.
            filename: Nom du fichier PDF.
            content: Contenu binaire du fichier.

        Returns:
            Dictionnaire de l'entrée ajoutée dans contenu.yaml.

        Raises:
            FileExistsError: Si un fichier du même nom existe déjà.
            ValueError: Si le YAML existant est malformé.
        """
        documents_dir = self.corpus_base_path / domaine / "documents"
        documents_dir.mkdir(parents=True, exist_ok=True)

        target_path = documents_dir / filename
        if target_path.exists():
            raise FileExistsError(
                f"Un document portant ce nom existe déjà : {filename}"
            )

        target_path.write_bytes(content)

        entry: dict[str, Any] = {
            "nom": f"documents/{filename}",
            "description": "",
            "type": "document",
            "date_ajout": date.today().isoformat(),
        }

        contenu_path = self._resolve_contenu_path(domaine)
        existing = self._load_yaml_list(contenu_path, "contenu")
        existing.append(entry)

        contenu_path.parent.mkdir(parents=True, exist_ok=True)
        with open(contenu_path, "w", encoding="utf-8") as f:
            yaml.dump(
                {"contenu": existing},
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        return entry

    def add_url(self, domaine: str, entry: dict[str, Any]) -> dict[str, Any]:
        """Ajoute une entrée dans urls/urls.yaml.

        Args:
            domaine: Nom du domaine.
            entry: Dictionnaire avec les champs nom, url, description, type.

        Returns:
            Dictionnaire de l'entrée ajoutée (avec date_ajout).
        """
        entry_with_date = {**entry, "date_ajout": date.today().isoformat()}

        urls_path = self._resolve_urls_path(domaine)
        existing = self._load_yaml_list(urls_path, "urls")
        existing.append(entry_with_date)

        urls_path.parent.mkdir(parents=True, exist_ok=True)
        with open(urls_path, "w", encoding="utf-8") as f:
            yaml.dump(
                {"urls": existing},
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        return entry_with_date

    def _resolve_contenu_path(self, domaine: str) -> Path:
        """Résout le chemin vers contenu.yaml d'un domaine."""
        return self.corpus_base_path / domaine / "contenu.yaml"

    def _resolve_urls_path(self, domaine: str) -> Path:
        """Résout le chemin vers urls/urls.yaml d'un domaine."""
        return self.corpus_base_path / domaine / "urls" / "urls.yaml"

    def _load_yaml_list(self, path: Path, key: str) -> list[dict[str, Any]]:
        """Charge une liste depuis un fichier YAML, ou retourne une liste vide.

        Args:
            path: Chemin vers le fichier YAML.
            key: Clé racine attendue ('contenu' ou 'urls').

        Returns:
            Liste des éléments existants.
        """
        if not path.exists():
            return []

        with open(path, encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ValueError(f"Erreur de parsing YAML ({path}): {e}") from e

        if data is None or key not in data:
            return []

        items = data[key]
        if items is None:
            return []

        if not isinstance(items, list):
            raise ValueError(f"La clé '{key}' dans {path} doit contenir une liste")

        return items
