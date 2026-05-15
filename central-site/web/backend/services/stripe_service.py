"""Service Stripe — création de sessions Checkout et vérification de webhooks.

Ce service gère la communication avec l'API Stripe pour la création de sessions
Checkout enrichies de métadonnées comptables et la vérification des webhooks.
Tous les experts sont traités en B2B dans les métadonnées.
"""

import logging
import os

import stripe
from fastapi import HTTPException, status

from models.expert import Expert
from services.compta_service import ComptaValidationError, build_metadata

logger = logging.getLogger(__name__)

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
APP_URL = os.environ.get("APP_URL", "http://localhost:3000")

stripe.api_key = STRIPE_SECRET_KEY


def create_checkout_session(
    expert: Expert,
    amount_cents: int,
    description: str,
    ticket_code: str | None = None,
) -> stripe.checkout.Session:
    """Crée une session Stripe Checkout pour l'achat d'un ticket.

    Charge le profil Expert (B2B/B2C), construit les métadonnées comptables
    via compta_service, puis crée la session Stripe Checkout avec ces
    métadonnées.

    Args:
        expert: Instance du modèle Expert (avec profil B2B/B2C chargé).
        amount_cents: Montant TTC en centimes (ex: 5880 pour 58.80€).
        description: Description affichée sur la page de paiement.
        ticket_code: Code unique du ticket (optionnel).

    Returns:
        Session Stripe Checkout.

    Raises:
        HTTPException(422): Si la validation des métadonnées comptables échoue.
        HTTPException(500): Si la création de la session Stripe échoue.
    """
    # --- Construire la configuration ticket pour les métadonnées ---
    ticket_config = _build_ticket_config(expert, amount_cents)

    # --- Construire les métadonnées comptables ---
    try:
        compta_metadata = build_metadata(expert, ticket_config)
    except ComptaValidationError as exc:
        logger.warning(
            "Validation comptable échouée pour expert %s: %s",
            expert.id,
            exc.message,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Erreur de validation comptable : {exc.message}",
        ) from exc

    # --- Fusionner les métadonnées comptables avec les métadonnées techniques ---
    metadata = {
        **compta_metadata,
        "expert_id": str(expert.id),
        "ticket_code": ticket_code or "",
    }

    # --- Créer la session Stripe Checkout ---
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "eur",
                        "unit_amount": amount_cents,
                        "product_data": {
                            "name": "Ticket d'expertise Judi-Expert",
                            "description": description,
                        },
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            customer_email=expert.email,
            success_url=(
                f"{APP_URL}/monespace/tickets?success=true"
                + (f"&ticket_code={ticket_code}" if ticket_code else "")
            ),
            cancel_url=f"{APP_URL}/monespace/tickets?canceled=true",
            metadata=metadata,
        )
    except stripe.error.StripeError as exc:
        logger.error(
            "Erreur Stripe lors de la création de session pour expert %s: %s",
            expert.id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la création de la session de paiement",
        ) from exc

    return session


def _build_ticket_config(expert: Expert, amount_cents: int) -> dict[str, str]:
    """Construit le dictionnaire ticket_config pour compta_service.

    Calcule les prix HT, TVA et TTC à partir du montant TTC en centimes.
    Tous les experts sont traités en B2B.

    Args:
        expert: Instance du modèle Expert.
        amount_cents: Montant TTC en centimes.

    Returns:
        Dictionnaire de configuration du ticket avec prix et infos achat.
    """
    from datetime import datetime, timezone

    amount_ttc = amount_cents / 100
    amount_ht = amount_ttc / (1 + 0.20)  # TVA 20%
    amount_tva = amount_ttc - amount_ht

    config: dict[str, str] = {
        "domaine": expert.domaine,
        "price_ht": f"{amount_ht:.2f}",
        "price_tva": f"{amount_tva:.2f}",
        "price_ttc": f"{amount_ttc:.2f}",
        "date_achat": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "service_type": "ticket-expertise",
        "abonnement": "non",
        "recurrence": "ponctuel",
    }

    return config


def verify_webhook_signature(
    payload: bytes,
    sig_header: str,
) -> stripe.Event:
    """Vérifie la signature d'un webhook Stripe et retourne l'événement.

    Args:
        payload: Corps brut de la requête.
        sig_header: Valeur du header Stripe-Signature.

    Returns:
        Événement Stripe vérifié.

    Raises:
        stripe.error.SignatureVerificationError: Si la signature est invalide.
    """
    return stripe.Webhook.construct_event(
        payload,
        sig_header,
        STRIPE_WEBHOOK_SECRET,
    )
