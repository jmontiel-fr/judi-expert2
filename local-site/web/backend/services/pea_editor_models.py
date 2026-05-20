"""
Judi-Expert — Modèles de données pour l'éditeur PEA.

Contient les dataclasses représentant les structures internes du parsing PEA
(blocs, sections, document) et les schémas Pydantic pour les endpoints API
avec alias camelCase pour la sérialisation JSON frontend.

Valide : Exigences 11.1, 11.2, 11.3, 11.4, 12.3
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

import uuid


# ---------------------------------------------------------------------------
# Dataclasses internes (parsing)
# ---------------------------------------------------------------------------


@dataclass
class PEABlock:
    """Bloc générique du document PEA.

    Attributes:
        id: Identifiant unique UUID pour le tracking et les clés React.
        type: Type de bloc (heading, text, placeholder, annotation).
        paragraph_index: Position du paragraphe dans le .docx source (0-based).
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: Literal["heading", "text", "placeholder", "annotation"] = "text"
    paragraph_index: int = 0


@dataclass
class HeadingBlock(PEABlock):
    """Titre de section.

    Attributes:
        level: Niveau de titre (1-6, correspondant à H1-H6).
        number: Numérotation de la section (ex: "2.1.3").
        text: Texte du titre.
    """

    type: Literal["heading"] = "heading"
    level: int = 1
    number: str = ""
    text: str = ""


@dataclass
class TextBlock(PEABlock):
    """Texte normal (lecture seule).

    Attributes:
        content: Contenu textuel brut du paragraphe.
    """

    type: Literal["text"] = "text"
    content: str = ""


@dataclass
class PlaceholderBlock(PEABlock):
    """Placeholder <<...>>.

    Attributes:
        name: Nom du placeholder sans les délimiteurs << >>.
        full_text: Texte complet du paragraphe contenant le placeholder.
    """

    type: Literal["placeholder"] = "placeholder"
    name: str = ""
    full_text: str = ""


@dataclass
class AnnotationBlock(PEABlock):
    """Annotation @type ... @.

    Attributes:
        annotation_type: Type d'annotation (remplir, dires, analyse, etc.).
        suffix: Paramètres après le type (ex: "section_2.1.3").
        content: Contenu textuel de l'annotation.
        is_editable: True pour remplir, dires, analyse, conclusion.
        field_name: Pour @remplir : nom du champ.
        field_format: Pour @remplir : format attendu.
        section_ref: Pour @dires/@analyse : référence de section.
    """

    type: Literal["annotation"] = "annotation"
    annotation_type: str = ""
    suffix: str = ""
    content: str = ""
    is_editable: bool = False
    field_name: str | None = None
    field_format: str | None = None
    section_ref: str | None = None


@dataclass
class SectionInfo:
    """Information sur une section du document.

    Attributes:
        number: Numérotation de la section (ex: "2.1.3").
        title: Texte du titre de la section.
        level: Niveau de profondeur (1-4).
        annotation_type: Type d'annotation associé (dires ou analyse).
    """

    number: str = ""
    title: str = ""
    level: int = 1
    annotation_type: str = "dires"


@dataclass
class PEADocument:
    """Résultat complet du parsing PEA.

    Attributes:
        blocks: Liste ordonnée des blocs extraits du document.
        sections: Liste des sections pour la palette d'annotations.
        errors: Erreurs de parsing non fatales (annotations non fermées, etc.).
        filename: Nom du fichier source.
        total_paragraphs: Nombre total de paragraphes dans le document.
    """

    blocks: list[PEABlock] = field(default_factory=list)
    sections: list[SectionInfo] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    filename: str = ""
    total_paragraphs: int = 0


# ---------------------------------------------------------------------------
# Modèles Pydantic (API) — alias camelCase pour sérialisation JSON frontend
# ---------------------------------------------------------------------------


class PEABlockSchema(BaseModel):
    """Schéma JSON d'un bloc PEA.

    Attributes:
        id: Identifiant unique du bloc.
        type: Type de bloc.
        paragraph_index: Position dans le document source.
        level: Niveau de titre (heading uniquement).
        number: Numérotation de section (heading uniquement).
        text: Texte du titre (heading uniquement).
        content: Contenu textuel (text/annotation).
        name: Nom du placeholder (placeholder uniquement).
        full_text: Texte complet du paragraphe (placeholder uniquement).
        annotation_type: Type d'annotation (annotation uniquement).
        suffix: Paramètres de l'annotation.
        is_editable: Indique si le bloc est modifiable.
        field_name: Nom du champ (@remplir).
        field_format: Format attendu (@remplir).
        section_ref: Référence de section (@dires/@analyse).
    """

    id: str
    type: Literal["heading", "text", "placeholder", "annotation"]
    paragraph_index: int = Field(alias="paragraphIndex")
    # Heading fields
    level: int | None = None
    number: str | None = None
    text: str | None = None
    # Text fields
    content: str | None = None
    # Placeholder fields
    name: str | None = None
    full_text: str | None = Field(None, alias="fullText")
    # Annotation fields
    annotation_type: str | None = Field(None, alias="annotationType")
    suffix: str | None = None
    is_editable: bool | None = Field(None, alias="isEditable")
    field_name: str | None = Field(None, alias="fieldName")
    field_format: str | None = Field(None, alias="fieldFormat")
    section_ref: str | None = Field(None, alias="sectionRef")

    class Config:
        populate_by_name = True


class SectionInfoSchema(BaseModel):
    """Schéma JSON d'une section.

    Attributes:
        number: Numérotation de la section.
        title: Texte du titre.
        level: Niveau de profondeur.
        annotation_type: Type d'annotation associé.
    """

    number: str
    title: str
    level: int
    annotation_type: str = Field(alias="annotationType")

    class Config:
        populate_by_name = True


class PEAParseResponseSchema(BaseModel):
    """Réponse du endpoint /parse.

    Attributes:
        blocks: Liste des blocs du document parsé.
        sections: Liste des sections pour la palette.
        metadata: Métadonnées du document (filename, counts).
        errors: Erreurs de parsing non fatales.
    """

    blocks: list[PEABlockSchema]
    sections: list[SectionInfoSchema]
    metadata: dict
    errors: list[str]


class PEASaveRequestSchema(BaseModel):
    """Requête du endpoint /save.

    Attributes:
        blocks: Blocs avec contenu modifié.
        source_file: Fichier source encodé en base64.
        dossier_name: Nom du dossier actif.
        output_filename: Nom du fichier de sortie.
    """

    blocks: list[PEABlockSchema]
    source_file: str = Field(alias="sourceFile")
    dossier_name: str = Field(alias="dossierName")
    output_filename: str = Field(alias="outputFilename")

    class Config:
        populate_by_name = True


class PEASaveResponseSchema(BaseModel):
    """Réponse du endpoint /save.

    Attributes:
        success: Indique si la sauvegarde a réussi.
        output_path: Chemin complet du fichier écrit.
        message: Message descriptif du résultat.
    """

    success: bool
    output_path: str = Field(alias="outputPath")
    message: str

    class Config:
        populate_by_name = True
