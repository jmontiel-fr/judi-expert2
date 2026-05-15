"""Service Subscription — gestion des abonnements, cron de relance et résiliation.

Ce service implémente la logique métier pour :
- Le traitement des incidents de paiement (cron quotidien)
- Le contrôle d'accès basé sur le statut d'abonnement
- La programmation et l'exécution de la résiliation d'abonnement
"""

import logging
import os
from datetime import datetime, timezone

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.subscription import Subscription
from models.subscription_log import SubscriptionLog
from services.email_service import _send_email

logger = logging.getLogger(__name__)

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
stripe.api_key = STRIPE_SECRET_KEY

# Délai en jours avant blocage après premier rejet
PAYMENT_FAILURE_GRACE_DAYS = 5


async def _log_action(
    session: AsyncSession,
    expert_id: int,
    action: str,
    details: str | None = None,
) -> None:
    """Enregistre une action dans le journal subscription_logs.

    Args:
        session: Session SQLAlchemy async.
        expert_id: Identifiant de l'expert concerné.
        action: Type d'action (email_relance, email_suspension, blocked, terminated).
        details: Détails supplémentaires (optionnel).
    """
    log_entry = SubscriptionLog(
        expert_id=expert_id,
        action=action,
        details=details,
    )
    session.add(log_entry)


async def process_payment_failures(session: AsyncSession) -> dict[str, int]:
    """Traite les abonnements en échec de paiement (logique du cron quotidien).

    Pour chaque abonnement avec un paiement en échec :
    - Premier rejet (pas encore notifié) : envoie un email de relance,
      enregistre la date de première notification.
    - 5+ jours écoulés depuis la notification et paiement toujours impayé :
      bloque l'abonnement et envoie un email de suspension.

    Args:
        session: Session SQLAlchemy async.

    Returns:
        Dictionnaire avec les compteurs : processed, emails_sent, blocked.
    """
    now = datetime.now(timezone.utc)

    # Récupérer les abonnements avec un paiement en échec non encore bloqués
    result = await session.execute(
        select(Subscription).where(
            Subscription.payment_failed_at.isnot(None),
            Subscription.status.in_(["active", "terminating"]),
        )
    )
    subscriptions = result.scalars().all()

    processed = 0
    emails_sent = 0
    blocked = 0

    for sub in subscriptions:
        processed += 1

        if sub.first_rejection_notified_at is None:
            # Premier rejet : envoyer email de relance
            sub.first_rejection_notified_at = now
            sub.updated_at = now

            await _send_relance_email(session, sub)
            emails_sent += 1

            await _log_action(
                session,
                expert_id=sub.expert_id,
                action="email_relance",
                details=(
                    f"Email de relance envoyé. "
                    f"Paiement en échec depuis {sub.payment_failed_at.isoformat()}"
                ),
            )

        else:
            # Vérifier si 5+ jours se sont écoulés depuis la notification
            days_elapsed = (now - sub.first_rejection_notified_at).days
            if days_elapsed >= PAYMENT_FAILURE_GRACE_DAYS:
                # Bloquer l'abonnement
                sub.status = "blocked"
                sub.blocked_at = now
                sub.updated_at = now

                await _log_action(
                    session,
                    expert_id=sub.expert_id,
                    action="blocked",
                    details=(
                        f"Abonnement bloqué après {days_elapsed} jours "
                        f"de non-paiement"
                    ),
                )
                blocked += 1

                # Envoyer email de suspension
                await _send_suspension_email(session, sub)
                emails_sent += 1

                await _log_action(
                    session,
                    expert_id=sub.expert_id,
                    action="email_suspension",
                    details="Email de suspension envoyé",
                )

    await session.commit()

    logger.info(
        "Cron abonnement terminé : %d traités, %d emails envoyés, %d bloqués",
        processed,
        emails_sent,
        blocked,
    )

    return {
        "processed": processed,
        "emails_sent": emails_sent,
        "blocked": blocked,
    }


async def check_access(session: AsyncSession, expert_id: int) -> bool:
    """Vérifie si un expert a accès aux services basés sur l'abonnement.

    L'accès est refusé uniquement si le statut de l'abonnement est "blocked".
    Les statuts "active" et "terminating" permettent l'accès.

    Args:
        session: Session SQLAlchemy async.
        expert_id: Identifiant de l'expert.

    Returns:
        True si l'expert a accès, False sinon.
    """
    result = await session.execute(
        select(Subscription).where(Subscription.expert_id == expert_id)
    )
    subscription = result.scalar_one_or_none()

    if subscription is None:
        # Pas d'abonnement trouvé — pas d'accès aux services abonnement
        return False

    return subscription.status != "blocked"


async def schedule_termination(
    session: AsyncSession, expert_id: int
) -> dict[str, str]:
    """Programme la résiliation d'un abonnement en fin de période de facturation.

    La résiliation prend effet à la fin de la période de facturation en cours
    (current_period_end). L'expert conserve l'accès jusqu'à cette date.

    Args:
        session: Session SQLAlchemy async.
        expert_id: Identifiant de l'expert.

    Returns:
        Dictionnaire avec la date de résiliation effective et un message.

    Raises:
        ValueError: Si aucun abonnement actif n'est trouvé ou si une
            résiliation est déjà programmée.
    """
    now = datetime.now(timezone.utc)

    result = await session.execute(
        select(Subscription).where(Subscription.expert_id == expert_id)
    )
    subscription = result.scalar_one_or_none()

    if subscription is None:
        raise ValueError("Aucun abonnement trouvé pour cet expert")

    if subscription.status == "terminated":
        raise ValueError("L'abonnement est déjà résilié")

    if subscription.status == "terminating":
        raise ValueError("Une résiliation est déjà programmée")

    if subscription.status == "blocked":
        raise ValueError(
            "L'abonnement est bloqué pour non-paiement. "
            "Veuillez régulariser votre situation avant de résilier."
        )

    # La date effective de résiliation est la fin de la période en cours
    termination_date = subscription.current_period_end

    subscription.status = "terminating"
    subscription.termination_scheduled_at = now
    subscription.termination_effective_at = termination_date
    subscription.updated_at = now

    await _log_action(
        session,
        expert_id=expert_id,
        action="termination_scheduled",
        details=(
            f"Résiliation programmée pour le "
            f"{termination_date.strftime('%Y-%m-%d')}"
        ),
    )

    await session.commit()

    logger.info(
        "Résiliation programmée pour expert %d, effective le %s",
        expert_id,
        termination_date.isoformat(),
    )

    return {
        "termination_date": termination_date.strftime("%Y-%m-%d"),
        "message": "Résiliation programmée",
    }


async def execute_termination(
    session: AsyncSession, subscription: Subscription
) -> None:
    """Exécute la résiliation effective d'un abonnement.

    Annule le paiement récurrent Stripe et envoie un email de confirmation
    à l'expert.

    Args:
        session: Session SQLAlchemy async.
        subscription: Instance du modèle Subscription à résilier.

    Raises:
        stripe.error.StripeError: Si l'annulation Stripe échoue.
    """
    now = datetime.now(timezone.utc)

    # Annuler l'abonnement Stripe
    try:
        stripe.Subscription.cancel(subscription.stripe_subscription_id)
    except stripe.error.StripeError as exc:
        logger.error(
            "Erreur Stripe lors de l'annulation de l'abonnement %s "
            "pour expert %d: %s",
            subscription.stripe_subscription_id,
            subscription.expert_id,
            exc,
        )
        await _log_action(
            session,
            expert_id=subscription.expert_id,
            action="termination_failed",
            details=f"Erreur Stripe : {exc}",
        )
        await session.commit()
        raise

    # Mettre à jour le statut
    subscription.status = "terminated"
    subscription.termination_effective_at = now
    subscription.updated_at = now

    await _log_action(
        session,
        expert_id=subscription.expert_id,
        action="terminated",
        details=(
            f"Abonnement Stripe {subscription.stripe_subscription_id} annulé"
        ),
    )

    # Envoyer email de confirmation
    await _send_termination_email(session, subscription)

    await session.commit()

    logger.info(
        "Abonnement %s résilié pour expert %d",
        subscription.stripe_subscription_id,
        subscription.expert_id,
    )


async def _send_relance_email(
    session: AsyncSession, subscription: Subscription
) -> None:
    """Envoie un email de relance pour paiement en échec.

    Args:
        session: Session SQLAlchemy async.
        subscription: Abonnement concerné.
    """
    from models.expert import Expert

    result = await session.execute(
        select(Expert).where(Expert.id == subscription.expert_id)
    )
    expert = result.scalar_one_or_none()

    if expert is None:
        logger.error(
            "Expert %d introuvable pour l'envoi de l'email de relance",
            subscription.expert_id,
        )
        return

    subject = "Judi-Expert — Incident de paiement sur votre abonnement"
    body = (
        f"Bonjour {expert.prenom} {expert.nom},\n\n"
        f"Nous avons constaté un incident de paiement sur votre abonnement "
        f"Judi-Expert.\n\n"
        f"Veuillez régulariser votre situation dans un délai de "
        f"{PAYMENT_FAILURE_GRACE_DAYS} jours afin d'éviter la suspension "
        f"de votre accès.\n\n"
        f"Si vous avez déjà effectué le paiement, veuillez ignorer ce "
        f"message.\n\n"
        f"Cordialement,\n"
        f"L'équipe Judi-Expert"
    )

    try:
        _send_email(to_email=expert.email, subject=subject, body_text=body)
    except Exception as exc:
        logger.error(
            "Échec envoi email relance à expert %d (%s): %s",
            expert.id,
            expert.email,
            exc,
        )


async def _send_suspension_email(
    session: AsyncSession, subscription: Subscription
) -> None:
    """Envoie un email de notification de suspension d'abonnement.

    Args:
        session: Session SQLAlchemy async.
        subscription: Abonnement concerné.
    """
    from models.expert import Expert

    result = await session.execute(
        select(Expert).where(Expert.id == subscription.expert_id)
    )
    expert = result.scalar_one_or_none()

    if expert is None:
        logger.error(
            "Expert %d introuvable pour l'envoi de l'email de suspension",
            subscription.expert_id,
        )
        return

    subject = "Judi-Expert — Suspension de votre abonnement"
    body = (
        f"Bonjour {expert.prenom} {expert.nom},\n\n"
        f"Votre abonnement Judi-Expert a été suspendu en raison d'un "
        f"défaut de paiement non régularisé dans le délai imparti de "
        f"{PAYMENT_FAILURE_GRACE_DAYS} jours.\n\n"
        f"Votre accès aux services est désormais bloqué.\n\n"
        f"Pour rétablir votre accès, veuillez régulariser votre paiement "
        f"depuis votre espace personnel.\n\n"
        f"Cordialement,\n"
        f"L'équipe Judi-Expert"
    )

    try:
        _send_email(to_email=expert.email, subject=subject, body_text=body)
    except Exception as exc:
        logger.error(
            "Échec envoi email suspension à expert %d (%s): %s",
            expert.id,
            expert.email,
            exc,
        )


async def _send_termination_email(
    session: AsyncSession, subscription: Subscription
) -> None:
    """Envoie un email de confirmation de résiliation d'abonnement.

    Args:
        session: Session SQLAlchemy async.
        subscription: Abonnement résilié.
    """
    from models.expert import Expert

    result = await session.execute(
        select(Expert).where(Expert.id == subscription.expert_id)
    )
    expert = result.scalar_one_or_none()

    if expert is None:
        logger.error(
            "Expert %d introuvable pour l'envoi de l'email de résiliation",
            subscription.expert_id,
        )
        return

    subject = "Judi-Expert — Confirmation de résiliation de votre abonnement"
    body = (
        f"Bonjour {expert.prenom} {expert.nom},\n\n"
        f"Nous vous confirmons la résiliation de votre abonnement "
        f"Judi-Expert.\n\n"
        f"Le paiement récurrent Stripe a été annulé. Vous ne serez plus "
        f"prélevé(e) à compter de cette date.\n\n"
        f"Nous vous remercions pour votre confiance et restons à votre "
        f"disposition.\n\n"
        f"Cordialement,\n"
        f"L'équipe Judi-Expert"
    )

    try:
        _send_email(to_email=expert.email, subject=subject, body_text=body)
    except Exception as exc:
        logger.error(
            "Échec envoi email résiliation à expert %d (%s): %s",
            expert.id,
            expert.email,
            exc,
        )
