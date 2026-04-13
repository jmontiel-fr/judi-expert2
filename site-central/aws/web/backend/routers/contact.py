"""Router du formulaire de contact — Site Central."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.contact_message import ContactMessage
from schemas.contact import ContactRequest, ContactResponse

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_optional_expert_id(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Optional[int]:
    """Tente d'extraire l'expert_id si un token Bearer est fourni."""
    if not authorization or not authorization.startswith("Bearer "):
        return None

    access_token = authorization[len("Bearer "):]
    if not access_token:
        return None

    try:
        from services import cognito_service
        from sqlalchemy import select
        from models.expert import Expert

        user_info = cognito_service.get_user(access_token)
        cognito_sub = user_info["Username"]

        result = await db.execute(
            select(Expert).where(Expert.cognito_sub == cognito_sub, Expert.is_deleted == False)
        )
        expert = result.scalar_one_or_none()
        return expert.id if expert else None
    except Exception:
        return None


@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def submit_contact(
    request: ContactRequest,
    db: AsyncSession = Depends(get_db),
    expert_id: Optional[int] = Depends(_get_optional_expert_id),
):
    """Soumet un message de contact. Aucune authentification requise."""
    contact = ContactMessage(
        expert_id=expert_id,
        domaine=request.domaine,
        objet=request.objet,
        message=request.message,
    )
    db.add(contact)
    await db.commit()

    return ContactResponse(message="Message de contact envoyé avec succès")
