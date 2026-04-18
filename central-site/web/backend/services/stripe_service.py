"""Service Stripe — création de sessions Checkout et vérification de webhooks."""

import os

import stripe

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
APP_URL = os.environ.get("APP_URL", "http://localhost:3000")

stripe.api_key = STRIPE_SECRET_KEY


def create_checkout_session(
    expert_id: int,
    expert_email: str,
    domaine: str,
    amount_cents: int,
    description: str,
    ticket_code: str | None = None,
) -> stripe.checkout.Session:
    """Crée une session Stripe Checkout pour l'achat d'un ticket.

    Args:
        expert_id: ID de l'expert en base.
        expert_email: Email de l'expert.
        domaine: Domaine d'expertise.
        amount_cents: Montant TTC en centimes (ex: 5880 pour 58.80€).
        description: Description affichée sur la page de paiement.

    Returns:
        Session Stripe Checkout.
    """
    return stripe.checkout.Session.create(
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
        customer_email=expert_email,
        success_url=f"{APP_URL}/monespace/tickets?success=true" + (f"&ticket_code={ticket_code}" if ticket_code else ""),
        cancel_url=f"{APP_URL}/monespace/tickets?canceled=true",
        metadata={
            "expert_id": str(expert_id),
            "domaine": domaine,
            "ticket_code": ticket_code or "",
        },
    )


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
