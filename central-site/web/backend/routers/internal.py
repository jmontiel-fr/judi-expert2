"""Router interne — endpoints protégés par token pour les tâches automatisées.

Ce router expose les endpoints appelés par les services internes (Lambda cron,
EventBridge) et protégés par un header `X-Cron-Token` vérifié contre une
variable d'environnement.
"""

import logging
import os

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas.subscription import CronCheckResponse
from services import subscription_service

logger = logging.getLogger(__name__)

router = APIRouter()

CRON_TOKEN = os.environ.get("CRON_TOKEN", "")


async def verify_cron_token(
    x_cron_token: str | None = Header(default=None),
) -> None:
    """Vérifie le token d'authentification du cron.

    Le token est comparé à la variable d'environnement CRON_TOKEN.
    Si le token est absent ou invalide, une erreur HTTP 401 est levée.

    Args:
        x_cron_token: Valeur du header X-Cron-Token.

    Raises:
        HTTPException(401): Token manquant ou invalide.
    """
    if not CRON_TOKEN:
        logger.error("CRON_TOKEN non configuré dans l'environnement")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Service non configuré",
        )

    if not x_cron_token or x_cron_token != CRON_TOKEN:
        logger.warning("Tentative d'accès cron avec un token invalide")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide",
        )


@router.post(
    "/cron/subscription-check",
    response_model=CronCheckResponse,
    dependencies=[Depends(verify_cron_token)],
)
async def cron_subscription_check(
    db: AsyncSession = Depends(get_db),
) -> CronCheckResponse:
    """Exécute la vérification quotidienne des abonnements en échec de paiement.

    Cet endpoint est appelé par la Lambda cron via EventBridge.
    Il traite les abonnements avec un paiement en échec :
    - Premier rejet : envoie un email de relance (5 jours pour régulariser).
    - 5+ jours écoulés : bloque l'abonnement et envoie un email de suspension.

    Returns:
        Compteurs des actions effectuées : processed, emails_sent, blocked.
    """
    result = await subscription_service.process_payment_failures(db)

    logger.info(
        "Cron subscription-check terminé : %s",
        result,
    )

    return CronCheckResponse(**result)
