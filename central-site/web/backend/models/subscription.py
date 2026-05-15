"""Modèle Subscription — abonnement d'un expert au Site Central."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .expert import Expert


class Subscription(Base):
    """Abonnement Stripe d'un expert.

    Statuts possibles :
        - active : abonnement en cours, paiement à jour
        - blocked : paiement en échec depuis plus de 5 jours, accès suspendu
        - terminating : résiliation programmée, accès maintenu jusqu'à fin de période
        - terminated : abonnement résilié effectivement
    """

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    expert_id: Mapped[int] = mapped_column(
        ForeignKey("experts.id"), unique=True
    )
    stripe_subscription_id: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="active")

    current_period_end: Mapped[datetime] = mapped_column()
    termination_scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True
    )
    termination_effective_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True
    )

    # Gestion des incidents de paiement
    payment_failed_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True
    )
    first_rejection_notified_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True
    )
    blocked_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    expert: Mapped["Expert"] = relationship(back_populates="subscription")
