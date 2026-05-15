"""Router de gestion de l'abonnement expert — Site Central.

Endpoints :
- POST /api/subscription/terminate : programmer la résiliation
- GET /api/subscription/status : retourner le statut de l'abonnement
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.expert import Expert
from models.subscription import Subscription
from routers.profile import get_current_expert
from schemas.subscription import SubscriptionResponse, TerminationResponse
from services import subscription_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/terminate", response_model=TerminationResponse)
async def terminate_subscription(
    current: tuple[Expert, str] = Depends(get_current_expert),
    db: AsyncSession = Depends(get_db),
) -> TerminationResponse:
    """Programme la résiliation de l'abonnement de l'expert connecté.

    La résiliation prend effet à la fin de la période de facturation en cours.
    L'expert conserve l'accès jusqu'à cette date.

    Returns:
        TerminationResponse avec la date effective et un message de confirmation.

    Raises:
        HTTPException 400: Si aucun abonnement actif ou résiliation déjà programmée.
    """
    expert, _ = current

    try:
        result = await subscription_service.schedule_termination(
            session=db, expert_id=expert.id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    # Le service retourne termination_date en format string "YYYY-MM-DD".
    # On récupère la date effective directement depuis la subscription
    # pour fournir un datetime complet au schéma.
    result_sub = await db.execute(
        select(Subscription).where(Subscription.expert_id == expert.id)
    )
    subscription = result_sub.scalar_one()

    return TerminationResponse(
        termination_date=subscription.termination_effective_at,
        message=result["message"],
    )


@router.get("/status", response_model=SubscriptionResponse)
async def get_subscription_status(
    current: tuple[Expert, str] = Depends(get_current_expert),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    """Retourne le statut de l'abonnement de l'expert connecté.

    Returns:
        SubscriptionResponse avec le statut, la date de résiliation éventuelle
        et la fin de période de facturation.

    Raises:
        HTTPException 404: Si aucun abonnement trouvé pour cet expert.
    """
    expert, _ = current

    result = await db.execute(
        select(Subscription).where(Subscription.expert_id == expert.id)
    )
    subscription = result.scalar_one_or_none()

    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun abonnement trouvé pour cet expert",
        )

    return SubscriptionResponse(
        status=subscription.status,
        termination_date=subscription.termination_effective_at,
        current_period_end=subscription.current_period_end,
    )
