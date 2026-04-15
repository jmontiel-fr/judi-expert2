"""Service d'envoi d'emails via AWS SES."""

import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "eu-west-3")
SES_SENDER_EMAIL = os.environ.get("SES_SENDER_EMAIL", "no-reply@judi-expert.fr")


def _get_ses_client():
    """Retourne un client boto3 SES."""
    return boto3.client("ses", region_name=AWS_REGION)


def send_ticket_email(
    expert_email: str,
    ticket_code: str,
    domaine: str,
) -> dict:
    """Envoie un email contenant le code du ticket à l'expert.

    Args:
        expert_email: Adresse email de l'expert.
        ticket_code: Code unique du ticket.
        domaine: Domaine d'expertise associé au ticket.

    Returns:
        Réponse SES send_email.

    Raises:
        ClientError: En cas d'erreur SES.
    """
    client = _get_ses_client()

    subject = f"Judi-Expert — Votre ticket d'expertise ({domaine})"
    body_text = (
        f"Bonjour,\n\n"
        f"Votre achat a été confirmé. Voici votre code de ticket :\n\n"
        f"    {ticket_code}\n\n"
        f"Domaine : {domaine}\n\n"
        f"Utilisez ce code dans l'Application Locale pour créer un nouveau dossier d'expertise.\n\n"
        f"Cordialement,\n"
        f"L'équipe Judi-Expert"
    )

    try:
        return client.send_email(
            Source=SES_SENDER_EMAIL,
            Destination={"ToAddresses": [expert_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": body_text, "Charset": "UTF-8"},
                },
            },
        )
    except ClientError as e:
        logger.error("Erreur SES lors de l'envoi du ticket par email: %s", e)
        raise
