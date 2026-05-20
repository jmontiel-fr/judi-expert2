"""Service d'envoi d'emails via SMTP.

Configuration via variables d'environnement SMTP_*.
SMTP Gandi (mail.gandi.net) en production.
"""

import logging
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

SMTP_HOST = os.environ.get("SMTP_HOST", "mail.gandi.net")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM_NAME = os.environ.get("SMTP_FROM_NAME", "Judi-Expert")
SMTP_NOTIFICATION_TO = os.environ.get("SMTP_NOTIFICATION_TO", "contact@judi-expert.fr")

IS_DEV = os.environ.get("APP_ENV", "production") == "development"


def _send_email(
    to_email: str,
    subject: str,
    body_text: str,
    attachment: bytes | None = None,
    attachment_filename: str | None = None,
) -> None:
    """Envoie un email via SMTP Gmail.

    Args:
        to_email: Adresse email du destinataire.
        subject: Sujet de l'email.
        body_text: Corps du message en texte brut.
        attachment: Contenu binaire de la pièce jointe (optionnel).
        attachment_filename: Nom du fichier joint (optionnel).
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning(
            "SMTP non configuré (SMTP_USER/SMTP_PASSWORD manquants). "
            "Email non envoyé à %s — sujet: %s",
            to_email, subject,
        )
        if IS_DEV:
            logger.info("=== EMAIL DEV (non envoyé) ===")
            logger.info("  To: %s", to_email)
            logger.info("  Subject: %s", subject)
            logger.info("  Body: %s", body_text[:200])
            if attachment_filename:
                logger.info("  Attachment: %s (%d bytes)", attachment_filename, len(attachment or b""))
            logger.info("=== FIN EMAIL DEV ===")
        return

    from_addr = f"{SMTP_FROM_NAME} <{SMTP_USER}>"

    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body_text, "plain", "utf-8"))

    if attachment and attachment_filename:
        part = MIMEApplication(attachment, Name=attachment_filename)
        part["Content-Disposition"] = f'attachment; filename="{attachment_filename}"'
        msg.attach(part)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        logger.info("Email envoyé à %s — sujet: %s", to_email, subject)
    except Exception as e:
        logger.error("Erreur SMTP lors de l'envoi à %s: %s", to_email, e)
        raise


def send_ticket_email(
    expert_email: str,
    ticket_code: str,
    domaine: str,
    ticket_file: bytes | None = None,
    ticket_filename: str | None = None,
) -> None:
    """Envoie un email contenant le ticket à l'expert.

    Args:
        expert_email: Adresse email de l'expert.
        ticket_code: Code unique du ticket.
        domaine: Domaine d'expertise associé.
        ticket_file: Contenu binaire du fichier ticket (optionnel).
        ticket_filename: Nom du fichier ticket (optionnel).
    """
    subject = f"Judi-Expert — Votre ticket d'expertise ({domaine})"
    body_text = (
        f"Bonjour,\n\n"
        f"Votre ticket d'expertise a été généré avec succès.\n\n"
        f"    Code : {ticket_code}\n"
        f"    Domaine : {domaine}\n\n"
    )

    if ticket_file and ticket_filename:
        body_text += (
            f"Le fichier ticket est joint à cet email.\n"
            f"Chargez-le dans l'Application Locale pour créer un nouveau dossier.\n"
            f"Ce ticket est valide 48 heures à compter de sa date d'émission.\n\n"
        )
    else:
        body_text += (
            f"Utilisez ce code dans l'Application Locale pour créer "
            f"un nouveau dossier d'expertise.\n\n"
        )

    body_text += (
        f"Cordialement,\n"
        f"L'équipe Judi-Expert"
    )

    _send_email(
        to_email=expert_email,
        subject=subject,
        body_text=body_text,
        attachment=ticket_file,
        attachment_filename=ticket_filename,
    )


def send_registration_notification(
    expert_email: str,
    nom: str,
    prenom: str,
    domaine: str,
) -> None:
    """Envoie une notification d'inscription à contact@judi-expert.fr.

    Appelé après chaque inscription réussie en production.
    Permet à l'administrateur d'être informé des nouvelles inscriptions.

    Args:
        expert_email: Email de l'expert inscrit.
        nom: Nom de l'expert.
        prenom: Prénom de l'expert.
        domaine: Domaine d'expertise choisi.
    """
    subject = f"Nouvelle inscription — {prenom} {nom} ({domaine})"
    body_text = (
        f"Bonjour,\n\n"
        f"Un nouvel expert vient de s'inscrire sur Judi-Expert.\n\n"
        f"    Nom : {nom}\n"
        f"    Prénom : {prenom}\n"
        f"    Email : {expert_email}\n"
        f"    Domaine : {domaine}\n\n"
        f"Cordialement,\n"
        f"Judi-Expert (notification automatique)"
    )

    _send_email(
        to_email=SMTP_NOTIFICATION_TO,
        subject=subject,
        body_text=body_text,
    )
