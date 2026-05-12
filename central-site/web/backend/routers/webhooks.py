"""Router des webhooks Stripe — Site Central."""

import logging
from datetime import datetime, timezone
from decimal import Decimal

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.ticket import Ticket
from services import email_service, stripe_service
from services.ticket_token_service import generate_ticket_token

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    stripe_signature: str = Header(...),
):
    """Webhook Stripe — traite les événements de paiement.

    Vérifie la signature, traite checkout.session.completed.
    Si le ticket existe déjà (pré-créé par /purchase), le confirme.
    Sinon, crée un nouveau ticket avec token signé.
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
        ticket_code_from_metadata = metadata.get("ticket_code", "")

        # Cas 1 : le ticket a été pré-créé par /purchase (ticket_code dans metadata)
        # → le confirmer (passer de "en_attente" à "actif")
        if ticket_code_from_metadata:
            result = await db.execute(
                select(Ticket).where(Ticket.ticket_code == ticket_code_from_metadata)
            )
            existing_ticket = result.scalars().first()

            if existing_ticket:
                if existing_ticket.statut == "en_attente":
                    existing_ticket.statut = "actif"
                    existing_ticket.stripe_payment_id = payment_intent

                    # Générer le token signé s'il n'existe pas encore
                    if not existing_ticket.ticket_token:
                        now = datetime.now(timezone.utc)
                        token = generate_ticket_token(
                            ticket_code=ticket_code_from_metadata,
                            email=customer_email,
                            created_at=now,
                        )
                        existing_ticket.ticket_token = token
                        from services.ticket_token_service import TICKET_VALIDITY_HOURS
                        from datetime import timedelta
                        existing_ticket.expires_at = now + timedelta(hours=TICKET_VALIDITY_HOURS)

                    await db.commit()
                    logger.info(
                        "Webhook: ticket %s confirmé (en_attente → actif)",
                        ticket_code_from_metadata,
                    )

                    # Envoyer l'email avec le token
                    try:
                        email_service.send_ticket_email(
                            customer_email, ticket_code_from_metadata, domaine
                        )
                    except Exception as e:
                        logger.error("Erreur envoi email ticket: %s", e)

                    return {"status": "ok"}

                # Ticket déjà actif (confirmé via /confirm avant le webhook)
                logger.info(
                    "Webhook: ticket %s déjà actif — ignoré",
                    ticket_code_from_metadata,
                )
                return {"status": "ok"}

        # Cas 2 : pas de ticket_code dans metadata (fallback, ne devrait pas arriver)
        # → créer un nouveau ticket avec token signé
        from uuid import uuid4

        ticket_code = str(uuid4())
        now = datetime.now(timezone.utc)

        token = generate_ticket_token(
            ticket_code=ticket_code,
            email=customer_email,
            created_at=now,
        )

        from services.ticket_token_service import TICKET_VALIDITY_HOURS
        from datetime import timedelta

        ticket = Ticket(
            ticket_code=ticket_code,
            ticket_token=token,
            expert_id=int(expert_id),
            domaine=domaine,
            statut="actif",
            montant=Decimal(amount_total) / Decimal(100),
            stripe_payment_id=payment_intent,
            expires_at=now + timedelta(hours=TICKET_VALIDITY_HOURS),
        )
        db.add(ticket)
        await db.commit()

        logger.info("Webhook: nouveau ticket %s créé avec token", ticket_code)

        try:
            email_service.send_ticket_email(customer_email, ticket_code, domaine)
        except Exception as e:
            logger.error("Erreur lors de l'envoi de l'email du ticket: %s", e)

    return {"status": "ok"}
