"""Router de gestion des tickets et paiements — Site Central."""

import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.expert import Expert
from models.ticket import Ticket
from routers.profile import get_current_expert
from schemas.tickets import (
    PurchaseRequest,
    PurchaseResponse,
    TicketResponse,
    TicketVerifyRequest,
    TicketVerifyResponse,
)
from services import stripe_service

logger = logging.getLogger(__name__)

router = APIRouter()

IS_DEV = os.environ.get("APP_ENV", "production") == "development"


@router.post("/purchase", response_model=PurchaseResponse)
async def purchase_ticket(
    _body: PurchaseRequest,
    current: tuple[Expert, str] = Depends(get_current_expert),
    db: AsyncSession = Depends(get_db),
):
    """Crée une session Stripe Checkout pour l'achat d'un ticket.
    En mode dev, génère directement un ticket gratuit sans Stripe."""
    expert, _ = current

    if IS_DEV:
        # Mode dev : génération directe d'un ticket gratuit
        ticket_code = f"DEV-{uuid.uuid4().hex[:12].upper()}"
        ticket = Ticket(
            ticket_code=ticket_code,
            expert_id=expert.id,
            domaine=expert.domaine,
            statut="actif",
            montant=Decimal("0.00"),
            stripe_payment_id=f"dev-{uuid.uuid4()}",
        )
        db.add(ticket)
        await db.commit()
        logger.info("Ticket dev généré: %s pour expert %s", ticket_code, expert.email)
        return PurchaseResponse(checkout_url=f"/monespace/tickets?dev_ticket={ticket_code}")

    try:
        session = stripe_service.create_checkout_session(
            expert_id=expert.id,
            expert_email=expert.email,
            domaine=expert.domaine,
        )
        return PurchaseResponse(checkout_url=session.url)
    except Exception as e:
        logger.error("Erreur Stripe lors de la création de session: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la création de la session de paiement",
        )


@router.get("/list", response_model=list[TicketResponse])
async def list_tickets(
    current: tuple[Expert, str] = Depends(get_current_expert),
    db: AsyncSession = Depends(get_db),
):
    """Liste tous les tickets achetés par l'expert connecté."""
    expert, _ = current

    result = await db.execute(
        select(Ticket)
        .where(Ticket.expert_id == expert.id)
        .order_by(Ticket.created_at.desc())
    )
    tickets = result.scalars().all()
    return tickets


@router.post("/verify", response_model=TicketVerifyResponse)
async def verify_ticket(
    request: TicketVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Vérifie un code de ticket (appelé par l'Application Locale).

    - Ticket actif → marque comme "utilisé", retourne success.
    - Ticket déjà utilisé → retourne erreur "déjà utilisé".
    - Ticket non trouvé → retourne erreur "invalide".
    """
    result = await db.execute(
        select(Ticket).where(Ticket.ticket_code == request.ticket_code)
    )
    ticket = result.scalars().first()

    if ticket is None:
        return TicketVerifyResponse(
            success=False,
            ticket_code=request.ticket_code,
            error="invalide",
        )

    if ticket.statut == "utilisé":
        return TicketVerifyResponse(
            success=False,
            ticket_code=request.ticket_code,
            error="déjà utilisé",
        )

    if ticket.statut == "actif":
        ticket.statut = "utilisé"
        ticket.used_at = datetime.now(timezone.utc)
        await db.commit()
        return TicketVerifyResponse(
            success=True,
            ticket_code=request.ticket_code,
        )

    # Any other status (e.g. "expiré")
    return TicketVerifyResponse(
        success=False,
        ticket_code=request.ticket_code,
        error="invalide",
    )
