"""
Judi-Expert — Router FastAPI pour l'éditeur PEA.

Endpoints :
- POST /api/pea-editor/parse : Parse un fichier .docx PEA/TPE
- POST /api/pea-editor/save : Sauvegarde les blocs modifiés en .docx

Valide : Exigences 6.2, 10.2, 10.4, 13.1, 13.2, 13.3, 13.4
"""

from __future__ import annotations

import base64
import logging

from fastapi import APIRouter, HTTPException, UploadFile, status

from services.pea_editor_models import (
    PEABlockSchema,
    PEAParseResponseSchema,
    PEASaveRequestSchema,
    PEASaveResponseSchema,
    SectionInfoSchema,
)
from services.pea_editor_service import PEAEditorService
from services.pea_serializer import PEASerializer, PEASerializerError

logger = logging.getLogger(__name__)

router = APIRouter()

# Instances des services
_parser = PEAEditorService()
_serializer = PEASerializer()


@router.post("/parse", response_model=PEAParseResponseSchema)
async def parse_pea_document(file: UploadFile):
    """Parse un fichier .docx PEA/TPE et retourne sa structure en blocs.

    Accepte un fichier multipart/form-data .docx, le parse et retourne
    les blocs structurés (headings, texte, placeholders, annotations).

    Args:
        file: Fichier .docx uploadé.

    Returns:
        PEAParseResponseSchema avec les blocs, sections et métadonnées.

    Raises:
        HTTPException 400: Si le fichier n'est pas un .docx valide.
    """
    # Valider l'extension
    if file.filename and not file.filename.lower().endswith(".docx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seuls les fichiers .docx sont acceptés.",
        )

    # Lire le contenu
    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Impossible de lire le fichier : {e}",
        )

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier est vide.",
        )

    # Parser le document
    try:
        pea_doc = _parser.parse(file_bytes)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Erreur inattendue lors du parsing PEA : %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors du parsing du document.",
        )

    # Convertir en schémas Pydantic
    blocks_schema = []
    for block in pea_doc.blocks:
        block_dict = {
            "id": block.id,
            "type": block.type,
            "paragraphIndex": block.paragraph_index,
        }

        if block.type == "heading":
            block_dict["level"] = block.level
            block_dict["number"] = block.number
            block_dict["text"] = block.text
        elif block.type == "text":
            block_dict["content"] = block.content
        elif block.type == "placeholder":
            block_dict["name"] = block.name
            block_dict["fullText"] = block.full_text
        elif block.type == "annotation":
            block_dict["annotationType"] = block.annotation_type
            block_dict["suffix"] = block.suffix
            block_dict["content"] = block.content
            block_dict["isEditable"] = block.is_editable
            block_dict["fieldName"] = block.field_name
            block_dict["fieldFormat"] = block.field_format
            block_dict["sectionRef"] = block.section_ref

        blocks_schema.append(PEABlockSchema(**block_dict))

    sections_schema = [
        SectionInfoSchema(
            number=s.number,
            title=s.title,
            level=s.level,
            annotationType=s.annotation_type,
        )
        for s in pea_doc.sections
    ]

    metadata = {
        "filename": file.filename or "document.docx",
        "totalParagraphs": pea_doc.total_paragraphs,
        "totalBlocks": len(pea_doc.blocks),
        "editableBlocks": sum(
            1
            for b in pea_doc.blocks
            if b.type == "annotation" and getattr(b, "is_editable", False)
        ),
    }

    return PEAParseResponseSchema(
        blocks=blocks_schema,
        sections=sections_schema,
        metadata=metadata,
        errors=pea_doc.errors,
    )


@router.post("/save", response_model=PEASaveResponseSchema)
async def save_pea_document(request: PEASaveRequestSchema):
    """Sauvegarde les blocs PEA modifiés en fichier .docx.

    Décode le fichier source depuis base64, applique les modifications
    des annotations éditables, et écrit le résultat dans le répertoire
    de travail du dossier.

    Args:
        request: PEASaveRequestSchema avec blocs, source et infos de sortie.

    Returns:
        PEASaveResponseSchema avec le chemin du fichier écrit.

    Raises:
        HTTPException 400: Si le fichier source est invalide.
        HTTPException 500: Si l'écriture échoue.
    """
    # Décoder le fichier source depuis base64
    try:
        source_bytes = base64.b64decode(request.source_file)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fichier source base64 invalide : {e}",
        )

    if not source_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier source décodé est vide.",
        )

    # Sérialiser et écrire
    try:
        output_path = _serializer.write_to_work_dir(
            source_bytes=source_bytes,
            blocks=request.blocks,
            dossier_name=request.dossier_name,
            output_filename=request.output_filename,
        )
    except PEASerializerError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Erreur inattendue lors de la sauvegarde PEA : %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors de la sauvegarde.",
        )

    return PEASaveResponseSchema(
        success=True,
        outputPath=output_path,
        message=f"Document sauvegardé : {request.output_filename}",
    )
