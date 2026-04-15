"""Router des webhooks Stripe — Site Central."""

import logging
from decimal import Decimal
from uuid import uuid4

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.ticket import Ticket
from services import email_service, stripe_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    stripe_signature: str = Header(...),
):
    """Webhook Stripe — traite les événements de paiement.

    Vérifie la signature, traite checkout.session.completed,
    génère un ticket unique et l'envoie par email.
    """
    payload = await request.body()

    try:
        event = stripe_service.verify_webhook_signature(payload, stripe_signature)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Signature webhook invalide",
        )

    if event["type"] == "checkout.session.completed":
        session_data = event["data"]["object"]
        metadata = session_data.get("metadata", {})
        expert_id = metadata.get("expert_id")
        domaine = metadata.get("domaine", "")
        customer_email = session_data.get("customer_email", "")
        payment_intent = session_data.get("payment_intent", "")
        amount_total = session_data.get("amount_total", 0)

        ticket_code = str(uuid4())

        ticket = Ticket(
            ticket_code=ticket_code,
            expert_id=int(expert_id),
            domaine=domaine,
            statut="actif",
            montant=Decimal(amount_total) / Decimal(100),
            stripe_payment_id=payment_intent,
        )
        db.add(ticket)
        await db.commit()

        try:
            email_service.send_ticket_email(customer_email, ticket_code, domaine)
        except Exception as e:
            logger.error("Erreur lors de l'envoi de l'email du ticket: %s", e)

    return {"status": "ok"}
