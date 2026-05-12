"""
Judi-Expert — Service Fichier (FileService)

Encapsule la logique métier de gestion des fichiers d'étape :
formatage de taille, détection du Content-Type et remplacement
d'un fichier avec conservation de l'original.

Valide : Exigences 1.2, 3.3, 4.2, 4.3, 4.4
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.step_file import StepFile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

CONTENT_TYPE_MAP: dict[str, str] = {
    ".md": "text/markdown",
    ".pdf": "application/pdf",
    ".docx": (
        "application/vnd.openxmlformats-officedocument"
        ".wordprocessingml.document"
    ),
    ".zip": "application/zip",
}

DEFAULT_CONTENT_TYPE: str = "application/octet-stream"

_SIZE_UNITS: list[str] = ["o", "Ko", "Mo", "Go"]


class FileService:
    """Service de gestion des fichiers d'étape."""

    # ------------------------------------------------------------------
    # Formatage de la taille
    # ------------------------------------------------------------------

    def format_file_size(self, size_bytes: int) -> str:
        """Formate une taille en octets vers une chaîne lisible.

        Utilise les unités o, Ko, Mo, Go. La valeur numérique reste
        entre 0 et 1024 (exclusif) pour les unités non terminales.

        Args:
            size_bytes: Taille en octets (>= 0).

        Returns:
            Chaîne formatée, ex. ``"512 Ko"``, ``"1.5 Mo"``.
        """
        value = float(size_bytes)
        for unit in _SIZE_UNITS[:-1]:  # o, Ko, Mo
            if value < 1024:
                formatted = f"{value:.1f}".rstrip("0").rstrip(".")
                return f"{formatted} {unit}"
            value /= 1024
        # Terminal unit: Go
        formatted = f"{value:.1f}".rstrip("0").rstrip(".")
        return f"{formatted} {_SIZE_UNITS[-1]}"

    # ------------------------------------------------------------------
    # Content-Type
    # ------------------------------------------------------------------

    def get_content_type(self, filename: str) -> str:
        """Retourne le Content-Type approprié selon l'extension du fichier.

        Args:
            filename: Nom du fichier (ex. ``"rapport.pdf"``).

        Returns:
            Type MIME correspondant ou ``application/octet-stream``.
        """
        ext = Path(filename).suffix.lower()
        return CONTENT_TYPE_MAP.get(ext, DEFAULT_CONTENT_TYPE)

    # ------------------------------------------------------------------
    # Remplacement de fichier
    # ------------------------------------------------------------------

    def replace_file(
        self,
        step_file: StepFile,
        new_content: bytes,
        step_dir: str,
    ) -> None:
        """Remplace un fichier en conservant l'original avec suffixe _original.

        1. Renomme le fichier original vers ``{name}_original.{ext}``
           (sauf si déjà fait lors d'un remplacement précédent).
        2. Écrit le nouveau contenu sous le nom original.
        3. Met à jour les champs du StepFile en mémoire (le commit
           est laissé à l'appelant).

        Args:
            step_file: Enregistrement StepFile à mettre à jour.
            new_content: Contenu binaire du nouveau fichier.
            step_dir: Répertoire de l'étape sur le disque.
        """
        original_path = Path(step_dir) / step_file.filename
        stem = original_path.stem
        ext = original_path.suffix
        backup_name = f"{stem}_original{ext}"
        backup_path = Path(step_dir) / backup_name

        # 1. Conserver l'original (une seule fois)
        if not step_file.is_modified and original_path.exists():
            os.replace(original_path, backup_path)
            logger.info("Original conservé : %s → %s", original_path, backup_path)

        # 2. Écrire le nouveau contenu sous le nom original
        original_path.write_bytes(new_content)
        logger.info("Nouveau fichier écrit : %s (%d octets)", original_path, len(new_content))

        # 3. Mettre à jour le StepFile
        step_file.is_modified = True
        step_file.original_file_path = str(backup_path)
        step_file.file_size = len(new_content)
        step_file.updated_at = datetime.now(UTC)
