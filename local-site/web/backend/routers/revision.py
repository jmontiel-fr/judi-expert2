"""Router Révision — upload de fichiers et soumission de texte pour révision.

Expose deux endpoints :
- POST /upload : accepte un fichier .docx, .txt ou .md en multipart/form-data
- POST /text : accepte du texte brut en JSON pour révision directe

Valide : Exigences 2.1, 2.2, 2.3, 2.4, 2b.1, 2b.2, 2b.3, 2b.4, 5.3, 5b.1, 7.1, 7.2, 7.5
"""

from __future__ import annotations

import logging
import os
import tempfile

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse

from services.llm_service import LLMConnectionError, LLMService, LLMTimeoutError
from services.revision_models import (
    DocumentParseError,
    TextRevisionRequest,
    TextRevisionResponse,
)
from services.revision_service import RevisionService

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS: set[str] = {".docx", ".txt", ".md"}
MAX_FILE_SIZE_BYTES: int = 20 * 1024 * 1024  # 20 MB
MAX_TEXT_LENGTH: int = 100_000  # 100 000 caractères


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_file_extension(filename: str | None) -> str:
    """Extrait et normalise l'extension du fichier.

    Args:
        filename: Nom du fichier uploadé.

    Returns:
        Extension en minuscules avec le point (ex: '.docx').

    Raises:
        HTTPException: Si le nom de fichier est absent ou l'extension invalide.
    """
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nom de fichier manquant.",
        )
    _, ext = os.path.splitext(filename)
    return ext.lower()


def _get_revision_service() -> RevisionService:
    """Instancie le RevisionService avec ses dépendances.

    Returns:
        Instance de RevisionService prête à l'emploi.
    """
    llm_service = LLMService()
    return RevisionService(llm_service)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/upload")
async def upload_and_revise(file: UploadFile = File(...)):
    """Reçoit un fichier .docx, .txt ou .md et le révise via le LLM.

    - .docx → retourne FileResponse avec track changes (fichier-revu.docx)
    - .txt/.md → retourne JSON avec texte corrigé + filename pour download

    Args:
        file: Fichier uploadé en multipart/form-data.

    Returns:
        FileResponse (.docx) ou TextRevisionResponse (.txt/.md).

    Raises:
        HTTPException 400: Format non supporté ou fichier corrompu.
        HTTPException 413: Fichier > 20 MB.
        HTTPException 503: LLM indisponible.
    """
    # 1. Valider l'extension
    ext = _get_file_extension(file.filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Format non supporté : '{ext}'. "
                f"Formats acceptés : .docx, .txt, .md"
            ),
        )

    # 2. Lire le contenu et valider la taille
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Le fichier dépasse la taille maximale autorisée de 20 MB "
                f"({len(file_bytes) / (1024 * 1024):.1f} MB reçu)."
            ),
        )

    # 3. Appeler le service de révision
    service = _get_revision_service()
    try:
        result = await service.revise_document(file_bytes, ext)
    except DocumentParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Impossible de lire le fichier : {exc}",
        )
    except (LLMTimeoutError, LLMConnectionError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Le service de révision est temporairement indisponible.",
        )

    # 4. Retourner le résultat selon le type
    if ext == ".docx":
        # Écrire les bytes dans un fichier temporaire pour FileResponse
        tmp_file = tempfile.NamedTemporaryFile(
            delete=False, suffix=".docx", prefix="judi_revision_",
        )
        try:
            tmp_file.write(result)
            tmp_file.close()
            return FileResponse(
                path=tmp_file.name,
                filename="fichier-revu.docx",
                media_type=(
                    "application/vnd.openxmlformats-officedocument"
                    ".wordprocessingml.document"
                ),
                background=None,
            )
        except Exception:
            # Nettoyage en cas d'erreur
            os.unlink(tmp_file.name)
            raise
    else:
        # .txt ou .md → retourner JSON
        output_filename = f"fichier-revu{ext}"
        return JSONResponse(
            content=TextRevisionResponse(
                corrected_text=result,
                filename=output_filename,
            ).model_dump(),
        )


@router.post("/text", response_model=TextRevisionResponse)
async def revise_text(request: TextRevisionRequest) -> TextRevisionResponse:
    """Reçoit du texte brut copié-collé et le révise via le LLM.

    Args:
        request: Corps JSON contenant le texte à réviser.

    Returns:
        TextRevisionResponse avec le texte corrigé.

    Raises:
        HTTPException 400: Texte vide ou > 100 000 caractères.
        HTTPException 503: LLM indisponible.
    """
    # 1. Valider le texte
    text = request.text

    if not text or not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le texte soumis est vide.",
        )

    if len(text) > MAX_TEXT_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Le texte dépasse la limite de {MAX_TEXT_LENGTH:,} caractères "
                f"({len(text):,} caractères reçus)."
            ),
        )

    # 2. Appeler le service de révision
    service = _get_revision_service()
    try:
        corrected_text = await service.revise_text(text)
    except (LLMTimeoutError, LLMConnectionError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Le service de révision est temporairement indisponible.",
        )

    return TextRevisionResponse(corrected_text=corrected_text)
