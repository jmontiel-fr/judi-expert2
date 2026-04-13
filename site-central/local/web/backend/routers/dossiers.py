"""Router de gestion des dossiers d'expertise.

Valide : Exigences 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models.dossier import Dossier
from models.local_config import LocalConfig
from models.step import Step
from routers.auth import get_current_user
from services.site_central_client import SiteCentralClient, SiteCentralError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class DossierListItem(BaseModel):
    id: int
    nom: str
    ticket_id: str
    domaine: str
    statut: str
    created_at: datetime


class DossierListResponse(BaseModel):
    dossiers: list[DossierListItem]


class DossierCreateRequest(BaseModel):
    nom: str = Field(..., min_length=1, description="Nom du dossier")
    ticket_id: str = Field(..., min_length=1, description="Code du ticket")


class StepItem(BaseModel):
    step_number: int
    statut: str
    executed_at: datetime | None = None
    validated_at: datetime | None = None


class DossierDetailResponse(BaseModel):
    id: int
    nom: str
    ticket_id: str
    domaine: str
    statut: str
    created_at: datetime
    updated_at: datetime
    steps: list[StepItem]


class StepFileItem(BaseModel):
    id: int
    filename: str
    file_path: str
    file_type: str
    file_size: int
    created_at: datetime


class StepDetailResponse(BaseModel):
    id: int
    step_number: int
    statut: str
    executed_at: datetime | None = None
    validated_at: datetime | None = None
    files: list[StepFileItem]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_local_config(db: AsyncSession) -> LocalConfig:
    """Récupère la configuration locale ou lève 404."""
    result = await db.execute(select(LocalConfig).limit(1))
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration initiale non effectuée",
        )
    return config


async def _verify_ticket(ticket_code: str) -> dict:
    """Vérifie un ticket auprès du Site Central.

    Utilise le client centralisé avec retry et gestion des heures ouvrables.
    Returns a dict with keys: valid (bool), message (str).
    Raises HTTPException on network / Site Central errors.
    """
    client = SiteCentralClient()
    try:
        resp = await client.post(
            "/api/tickets/verify",
            json={"ticket_code": ticket_code},
        )
    except SiteCentralError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=exc.message,
        )

    if resp.status_code == 200:
        data = resp.json()
        # Site Central returns {success: bool, ticket_code: str, error?: str}
        if data.get("success"):
            return {"valid": True, "message": "Ticket valide"}
        error = data.get("error", "Ticket invalide ou déjà utilisé")
        return {"valid": False, "message": error}

    # Non-200 response
    try:
        body = resp.json()
        detail = body.get("detail", body.get("message", "Ticket invalide ou déjà utilisé"))
    except Exception:
        detail = "Ticket invalide ou déjà utilisé"
    return {"valid": False, "message": detail}


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter()


# ---- 1. GET /  (list dossiers) --------------------------------------------

@router.get("", response_model=DossierListResponse)
async def list_dossiers(
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Liste tous les dossiers triés par date de création décroissante."""
    result = await db.execute(
        select(Dossier).order_by(Dossier.created_at.desc(), Dossier.id.desc())
    )
    dossiers = result.scalars().all()
    return DossierListResponse(
        dossiers=[
            DossierListItem(
                id=d.id,
                nom=d.nom,
                ticket_id=d.ticket_id,
                domaine=d.domaine,
                statut=d.statut,
                created_at=d.created_at,
            )
            for d in dossiers
        ]
    )


# ---- 2. POST /  (create dossier) ------------------------------------------

@router.post("", response_model=DossierDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_dossier(
    body: DossierCreateRequest,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crée un nouveau dossier après vérification du ticket."""
    # Check ticket uniqueness locally first
    existing = await db.execute(
        select(Dossier).where(Dossier.ticket_id == body.ticket_id)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce ticket a déjà été utilisé pour créer un dossier",
        )

    # Verify ticket with Site Central
    ticket_result = await _verify_ticket(body.ticket_id)
    if not ticket_result["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ticket_result["message"],
        )

    # Get domaine from local config
    config = await _get_local_config(db)

    # Create dossier
    dossier = Dossier(
        nom=body.nom,
        ticket_id=body.ticket_id,
        domaine=config.domaine,
        statut="actif",
    )
    db.add(dossier)
    await db.flush()  # get dossier.id

    # Create 4 steps (0, 1, 2, 3) all with statut="initial"
    steps: list[Step] = []
    for step_number in range(4):
        step = Step(
            dossier_id=dossier.id,
            step_number=step_number,
            statut="initial",
        )
        db.add(step)
        steps.append(step)

    await db.commit()
    await db.refresh(dossier)
    for s in steps:
        await db.refresh(s)

    return DossierDetailResponse(
        id=dossier.id,
        nom=dossier.nom,
        ticket_id=dossier.ticket_id,
        domaine=dossier.domaine,
        statut=dossier.statut,
        created_at=dossier.created_at,
        updated_at=dossier.updated_at,
        steps=[
            StepItem(
                step_number=s.step_number,
                statut=s.statut,
                executed_at=s.executed_at,
                validated_at=s.validated_at,
            )
            for s in sorted(steps, key=lambda s: s.step_number)
        ],
    )


# ---- 3. GET /{id}  (dossier detail) ---------------------------------------

@router.get("/{dossier_id}", response_model=DossierDetailResponse)
async def get_dossier(
    dossier_id: int,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retourne le détail d'un dossier avec ses étapes."""
    result = await db.execute(
        select(Dossier)
        .options(selectinload(Dossier.steps))
        .where(Dossier.id == dossier_id)
    )
    dossier = result.scalar_one_or_none()
    if dossier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier non trouvé",
        )

    return DossierDetailResponse(
        id=dossier.id,
        nom=dossier.nom,
        ticket_id=dossier.ticket_id,
        domaine=dossier.domaine,
        statut=dossier.statut,
        created_at=dossier.created_at,
        updated_at=dossier.updated_at,
        steps=[
            StepItem(
                step_number=s.step_number,
                statut=s.statut,
                executed_at=s.executed_at,
                validated_at=s.validated_at,
            )
            for s in sorted(dossier.steps, key=lambda s: s.step_number)
        ],
    )


# ---- 4. GET /{id}/steps/{step}  (step detail) -----------------------------

@router.get("/{dossier_id}/steps/{step_number}", response_model=StepDetailResponse)
async def get_step_detail(
    dossier_id: int,
    step_number: int,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retourne le détail d'une étape spécifique avec ses fichiers."""
    if step_number not in (0, 1, 2, 3):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le numéro d'étape doit être entre 0 et 3",
        )

    # Verify dossier exists
    dossier_result = await db.execute(
        select(Dossier).where(Dossier.id == dossier_id)
    )
    if dossier_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier non trouvé",
        )

    result = await db.execute(
        select(Step)
        .options(selectinload(Step.files))
        .where(Step.dossier_id == dossier_id, Step.step_number == step_number)
    )
    step = result.scalar_one_or_none()
    if step is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Étape non trouvée",
        )

    return StepDetailResponse(
        id=step.id,
        step_number=step.step_number,
        statut=step.statut,
        executed_at=step.executed_at,
        validated_at=step.validated_at,
        files=[
            StepFileItem(
                id=f.id,
                filename=f.filename,
                file_path=f.file_path,
                file_type=f.file_type,
                file_size=f.file_size,
                created_at=f.created_at,
            )
            for f in step.files
        ],
    )
