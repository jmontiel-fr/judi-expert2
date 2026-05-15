"""Modèle Ticket — ticket d'expertise à usage unique."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .expert import Expert


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_code: Mapped[str] = mapped_column(String(255), unique=True)
    ticket_token: Mapped[Optional[str]] = mapped_column(String(500))
    expert_id: Mapped[int] = mapped_column(ForeignKey("experts.id"))
    domaine: Mapped[str] = mapped_column(String(100))
    statut: Mapped[str] = mapped_column(String(20), default="actif")
    montant: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    stripe_payment_id: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    expires_at: Mapped[Optional[datetime]] = mapped_column()
    used_at: Mapped[Optional[datetime]] = mapped_column()

    # Remboursement
    refunded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    stripe_refund_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    expert: Mapped["Expert"] = relationship(back_populates="tickets")
