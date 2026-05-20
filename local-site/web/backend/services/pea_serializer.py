"""
Judi-Expert — Service de sérialisation PEA.

Reconstruit un fichier .docx à partir des blocs modifiés par l'utilisateur,
en préservant les styles et la structure du document source.

Valide : Exigences 12.1, 12.2, 12.3, 12.4, 13.2, 13.3
"""

from __future__ import annotations

import io
import logging
import os
from pathlib import Path

from docx import Document as DocxDocument

from .pea_editor_models import AnnotationBlock, PEABlockSchema

logger = logging.getLogger(__name__)

# Répertoire de base pour les dossiers d'expertise
DATA_DIR = os.environ.get("DATA_DIR", "data")


class PEASerializerError(Exception):
    """Erreur lors de la sérialisation PEA."""

    pass


class PEASerializer:
    """Sérialise les blocs PEA modifiés en fichier .docx.

    Ouvre le document source, applique les modifications des annotations
    éditables, et écrit le résultat dans le répertoire de travail du dossier.
    """

    def serialize(self, source_bytes: bytes, blocks: list[PEABlockSchema]) -> bytes:
        """Sérialise les blocs modifiés dans le document source.

        Args:
            source_bytes: Contenu binaire du fichier .docx source.
            blocks: Liste des blocs avec contenu potentiellement modifié.

        Returns:
            Contenu binaire du fichier .docx résultant.

        Raises:
            PEASerializerError: Si le document source est invalide.
        """
        try:
            doc = DocxDocument(io.BytesIO(source_bytes))
        except Exception as e:
            raise PEASerializerError(
                f"Impossible d'ouvrir le document source : {e}"
            ) from e

        # Construire un mapping paragraph_index → bloc modifié (annotations éditables)
        modified_blocks: dict[int, PEABlockSchema] = {}
        for block in blocks:
            if (
                block.type == "annotation"
                and block.is_editable
                and block.content is not None
            ):
                idx = block.paragraph_index
                modified_blocks[idx] = block

        # Appliquer les modifications
        paragraphs = doc.paragraphs
        for para_idx, block in modified_blocks.items():
            if para_idx < len(paragraphs):
                self._rebuild_paragraph(paragraphs[para_idx], block)

        # Écrire en mémoire
        output = io.BytesIO()
        doc.save(output)
        return output.getvalue()

    def _rebuild_paragraph(self, paragraph, block: PEABlockSchema) -> None:
        """Reconstruit un paragraphe d'annotation avec le contenu modifié.

        Préserve le style du paragraphe mais remplace le texte par le format
        d'annotation standard : @type suffix : contenu @

        Args:
            paragraph: Paragraphe python-docx à modifier.
            block: Bloc avec le contenu modifié.
        """
        # Construire le texte de l'annotation
        ann_type = block.annotation_type or ""
        suffix = block.suffix or ""
        content = block.content or ""

        if suffix:
            new_text = f"@{ann_type} {suffix} : {content} @"
        else:
            new_text = f"@{ann_type} : {content} @"

        # Préserver le style du premier run, remplacer tout le texte
        if paragraph.runs:
            # Garder le style du premier run
            first_run = paragraph.runs[0]
            # Supprimer tous les runs sauf le premier
            for run in paragraph.runs[1:]:
                run._element.getparent().remove(run._element)
            # Mettre à jour le texte du premier run
            first_run.text = new_text
        else:
            # Pas de runs existants, ajouter directement
            paragraph.text = new_text

    def write_to_work_dir(
        self,
        source_bytes: bytes,
        blocks: list[PEABlockSchema],
        dossier_name: str,
        output_filename: str,
    ) -> str:
        """Sérialise et écrit le fichier dans le répertoire de travail.

        Args:
            source_bytes: Contenu binaire du fichier .docx source.
            blocks: Liste des blocs avec contenu modifié.
            dossier_name: Nom du dossier d'expertise.
            output_filename: Nom du fichier de sortie.

        Returns:
            Chemin complet du fichier écrit.

        Raises:
            PEASerializerError: Si l'écriture échoue.
        """
        # Sérialiser
        output_bytes = self.serialize(source_bytes, blocks)

        # Construire le chemin de sortie
        work_dir = Path(DATA_DIR) / "dossiers" / dossier_name / "travail"
        work_dir.mkdir(parents=True, exist_ok=True)

        output_path = work_dir / output_filename

        try:
            output_path.write_bytes(output_bytes)
            logger.info(
                "PEA sérialisé : %s (%d octets)",
                output_path,
                len(output_bytes),
            )
        except OSError as e:
            raise PEASerializerError(
                f"Impossible d'écrire le fichier : {e}"
            ) from e

        return str(output_path)
