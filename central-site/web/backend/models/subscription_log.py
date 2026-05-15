"""Modèle SubscriptionLog — journal des actions cron sur les abonnements."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .expert import Expert


class SubscriptionLog(Base):
    """Journal des actions effectuées sur les abonnements.

    Enregistre chaque action du cron de relance (email envoyé,
    abonnement bloqué, résilié) avec horodatage et identifiant expert.

    Actions possibles :
        - "email_relance" : email de relance envoyé après premier rejet
        - "email_suspension" : email de suspension envoyé après 5 jours
        - "blocked" : abonnement bloqué pour non-paiement
        - "terminated" : abonnement résilié
    """

    __tablename__ = "subscription_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    expert_id: Mapped[int] = mapped_column(ForeignKey("experts.id"))
    action: Mapped[str] = mapped_column(String(50))
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    expert: Mapped["Expert"] = relationship()
