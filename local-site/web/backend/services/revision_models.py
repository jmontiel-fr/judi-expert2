"""
Judi-Expert — Modèles de données pour la révision documentaire.

Contient les dataclasses représentant les structures internes du pipeline
de révision (parsing, corrections, diff), les exceptions personnalisées,
et les modèles Pydantic pour les endpoints API.

Valide : Exigences 3.1, 3.2, 7.2
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal
from zipfile import ZipFile

from pydantic import BaseModel

if TYPE_CHECKING:
    from lxml.etree import _Element as Element
else:
    from typing import Any

    Element = Any


# ---------------------------------------------------------------------------
# Exceptions personnalisées
# ---------------------------------------------------------------------------


class RevisionError(Exception):
    """Erreur de base pour le service de révision."""


class DocumentParseError(RevisionError):
    """Le fichier ne peut pas être lu comme un .docx valide."""


class ChunkProcessingError(RevisionError):
    """Erreur lors du traitement d'un chunk par le LLM."""


# ---------------------------------------------------------------------------
# Dataclasses internes
# ---------------------------------------------------------------------------


@dataclass
class RunInfo:
    """Un run (segment de texte avec formatage uniforme).

    Attributes:
        text: Contenu textuel du run.
        xml_element: Référence à l'élément w:r dans le XML du document.
        properties: Copie profonde de l'élément w:rPr (formatage) ou None.
    """

    text: str
    xml_element: Element
    properties: Element | None


@dataclass
class ParagraphInfo:
    """Un paragraphe avec ses runs et métadonnées.

    Attributes:
        index: Position du paragraphe dans le document (0-based).
        runs: Liste des runs composant le paragraphe.
        xml_element: Référence à l'élément w:p dans le XML.
        properties: Élément w:pPr (propriétés de paragraphe) ou None.
        full_text: Concaténation du texte de tous les runs.
        is_in_table: Indique si le paragraphe est dans une cellule de tableau.
        table_cell_ref: Référence à l'élément w:tc parent ou None.
    """

    index: int
    runs: list[RunInfo]
    xml_element: Element
    properties: Element | None
    full_text: str
    is_in_table: bool = False
    table_cell_ref: Element | None = None


@dataclass
class ParsedDocument:
    """Document parsé avec références XML préservées.

    Attributes:
        paragraphs: Liste ordonnée des paragraphes extraits.
        document_xml: Racine w:document de l'arbre XML.
        package: Archive .docx ouverte (ZipFile) pour réécriture.
    """

    paragraphs: list[ParagraphInfo]
    document_xml: Element
    package: ZipFile


@dataclass
class ParagraphCorrection:
    """Résultat de la correction LLM pour un paragraphe.

    Attributes:
        paragraph_index: Index du paragraphe corrigé.
        original_text: Texte original avant correction.
        corrected_text: Texte après correction par le LLM.
        has_changes: True si le texte a été modifié.
    """

    paragraph_index: int
    original_text: str
    corrected_text: str
    has_changes: bool


@dataclass
class DiffOperation:
    """Une opération de diff atomique.

    Attributes:
        op: Type d'opération (equal, insert, delete, replace).
        original_text: Texte original concerné par l'opération.
        new_text: Nouveau texte (vide pour delete, rempli pour insert/replace).
    """

    op: Literal["equal", "insert", "delete", "replace"]
    original_text: str
    new_text: str


# ---------------------------------------------------------------------------
# Modèles Pydantic (API)
# ---------------------------------------------------------------------------


class TextRevisionRequest(BaseModel):
    """Requête de révision de texte copié-collé.

    Attributes:
        text: Texte brut à réviser.
    """

    text: str


class TextRevisionResponse(BaseModel):
    """Réponse de révision pour texte et fichiers .txt/.md.

    Attributes:
        corrected_text: Texte corrigé par le LLM.
        filename: Nom du fichier de sortie ou None pour texte copié-collé.
    """

    corrected_text: str
    filename: str | None = None
