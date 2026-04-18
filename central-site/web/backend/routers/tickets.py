"""Router de gestion des tickets et paiements — Site Central."""

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.expert import Expert
from models.ticket import Ticket
from routers.profile import get_current_expert
from schemas.tickets import (
    PurchaseRequest,
    PurchaseResponse,
    TicketPriceResponse,
    TicketResponse,
    TicketVerifyRequest,
    TicketVerifyResponse,
)
from services import email_service, stripe_service
from services.ticket_token_service import generate_ticket_token, verify_ticket_token

logger = logging.getLogger(__name__)

router = APIRouter()

IS_DEV = os.environ.get("APP_ENV", "production") == "development"
TICKET_VALIDITY_HOURS = int(os.environ.get("TICKET_VALIDITY_HOURS", "48"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_ticket_config(db: AsyncSession):
    """Récupère la configuration du prix des tickets."""
    from models.ticket_config import TicketConfig

    result = await db.execute(select(TicketConfig).limit(1))
    config = result.scalar_one_or_none()
    if config is None:
        config = TicketConfig(prix_ht=Decimal("49.00"), tva_rate=Decimal("20.00"))
        db.add(config)
        await db.commit()
        await db.refresh(config)
    return config


def _compute_ttc(prix_ht: Decimal, tva_rate: Decimal) -> Decimal:
    """Calcule le prix TTC."""
    return (prix_ht * (Decimal("1") + tva_rate / Decimal("100"))).quantize(Decimal("0.01"))


def _create_ticket_and_token(
    ticket_code: str,
    expert: Expert,
    montant: Decimal,
    stripe_payment_id: str,
) -> tuple[Ticket, str]:
    """Crée un objet Ticket et génère le token signé."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=TICKET_VALIDITY_HOURS)

    token = generate_ticket_token(
        ticket_code=ticket_code,
        email=expert.email,
        created_at=now,
    )

    expires_at_naive = expires_at.replace(tzinfo=None)

    ticket = Ticket(
        ticket_code=ticket_code,
        ticket_token=token,
        expert_id=expert.id,
        domaine=expert.domaine,
        statut="actif",
        montant=montant,
        stripe_payment_id=stripe_payment_id,
        expires_at=expires_at_naive,
    )
    return ticket, token


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/price", response_model=TicketPriceResponse)
async def get_ticket_price(db: AsyncSession = Depends(get_db)):
    """Retourne le prix actuel du ticket (endpoint public)."""
    config = await _get_ticket_config(db)
    prix_ttc = _compute_ttc(config.prix_ht, config.tva_rate)
    return TicketPriceResponse(
        prix_ht=config.prix_ht,
        tva_rate=config.tva_rate,
        prix_ttc=prix_ttc,
    )


@router.post("/purchase", response_model=PurchaseResponse)
async def purchase_ticket(
    _body: PurchaseRequest,
    current: tuple[Expert, str] = Depends(get_current_expert),
    db: AsyncSession = Depends(get_db),
):
    """Crée une session Stripe Checkout pour l'achat d'un ticket.

    Dev et prod passent tous les deux par Stripe Checkout.
    En dev : clés Stripe de test, ticket pré-créé en 'en_attente',
             confirmé au retour success via /confirm.
    En prod : ticket créé par le webhook Stripe après paiement.
    """
    expert, _ = current
    config = await _get_ticket_config(db)
    prix_ttc = _compute_ttc(config.prix_ht, config.tva_rate)
    amount_cents = int(prix_ttc * Decimal("100"))

    description = (
        f"Ticket d'expertise Judi-Expert — "
        f"{config.prix_ht:.2f} € HT + TVA {config.tva_rate:.0f}% "
        f"= {prix_ttc:.2f} € TTC"
    )

    # En dev : pré-créer le ticket en attente de confirmation Stripe
    ticket_code = None
    if IS_DEV:
        ticket_code = f"DEV-{uuid.uuid4().hex[:12].upper()}"
        ticket, _token = _create_ticket_and_token(
            ticket_code=ticket_code,
            expert=expert,
            montant=prix_ttc,
            stripe_payment_id=f"dev-pending-{uuid.uuid4()}",
        )
        ticket.statut = "en_attente"
        db.add(ticket)
        await db.commit()
        logger.info("Ticket dev en attente: %s pour %s", ticket_code, expert.email)

    try:
        session = stripe_service.create_checkout_session(
            expert_id=expert.id,
            expert_email=expert.email,
            domaine=expert.domaine,
            amount_cents=amount_cents,
            description=description,
            ticket_code=ticket_code,
        )
        return PurchaseResponse(checkout_url=session.url)
    except Exception as e:
        logger.error("Erreur Stripe: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la création de la session de paiement",
        )


@router.post("/confirm")
async def confirm_ticket(
    ticket_code: str = Query(...),
    current: tuple[Expert, str] = Depends(get_current_expert),
    db: AsyncSession = Depends(get_db),
):
    """Confirme un ticket après retour de Stripe Checkout (dev uniquement).

    En dev, le webhook Stripe ne fonctionne pas (pas d'URL publique).
    Ce endpoint est appelé par le frontend au retour de la page success.
    """
    if not IS_DEV:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Endpoint dev uniquement")

    expert, _ = current
    result = await db.execute(
        select(Ticket).where(
            Ticket.ticket_code == ticket_code,
            Ticket.expert_id == expert.id,
        )
    )
    ticket = result.scalars().first()

    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket introuvable")

    if ticket.statut == "en_attente":
        ticket.statut = "actif"
        await db.commit()
        logger.info("Ticket dev confirmé: %s", ticket_code)

        # Envoyer le token par email
        try:
            email_service.send_ticket_email(
                expert_email=expert.email,
                ticket_code=ticket.ticket_token or ticket_code,
                domaine=expert.domaine,
            )
        except Exception as e:
            logger.error("Erreur envoi email ticket: %s", e)

    return {"message": "Ticket confirmé", "ticket_code": ticket_code}


@router.get("/list", response_model=list[TicketResponse])
async def list_tickets(
    current: tuple[Expert, str] = Depends(get_current_expert),
    db: AsyncSession = Depends(get_db),
):
    """Liste tous les tickets de l'expert connecté."""
    expert, _ = current
    result = await db.execute(
        select(Ticket)
        .where(Ticket.expert_id == expert.id)
        .order_by(Ticket.created_at.desc())
    )
    return result.scalars().all()


@router.post("/verify", response_model=TicketVerifyResponse)
async def verify_ticket(
    request: TicketVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Vérifie un token ticket signé (appelé par l'Application Locale)."""
    result = verify_ticket_token(request.ticket_token)

    if not result["valid"]:
        error = result["error"]
        code = result.get("payload", {}).get("ticket_code", "") if result.get("payload") else ""
        return TicketVerifyResponse(
            success=False,
            ticket_code=code or request.ticket_token[:20],
            error=error,
        )

    payload = result["payload"]
    ticket_code = payload["ticket_code"]

    db_result = await db.execute(
        select(Ticket).where(Ticket.ticket_code == ticket_code)
    )
    ticket = db_result.scalars().first()

    if ticket is None:
        return TicketVerifyResponse(success=False, ticket_code=ticket_code, error="invalide")

    if ticket.statut == "utilisé":
        return TicketVerifyResponse(success=False, ticket_code=ticket_code, error="déjà utilisé")

    if ticket.statut != "actif":
        return TicketVerifyResponse(success=False, ticket_code=ticket_code, error="invalide")

    ticket.statut = "utilisé"
    ticket.used_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    logger.info("Ticket vérifié et utilisé: %s", ticket_code)

    return TicketVerifyResponse(success=True, ticket_code=ticket_code)


@router.delete("/{ticket_id}")
async def delete_ticket(
    ticket_id: int,
    current: tuple[Expert, str] = Depends(get_current_expert),
    db: AsyncSession = Depends(get_db),
):
    """Supprime un ticket (dev uniquement)."""
    if not IS_DEV:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Non autorisé en production")

    expert, _ = current
    result = await db.execute(
        select(Ticket).where(Ticket.id == ticket_id, Ticket.expert_id == expert.id)
    )
    ticket = result.scalars().first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket introuvable")

    await db.delete(ticket)
    await db.commit()
    return {"message": "Ticket supprimé"}
