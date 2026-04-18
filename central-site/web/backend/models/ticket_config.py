"""Modèle TicketConfig — configuration du prix des tickets."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class TicketConfig(Base):
    """Configuration unique du prix des tickets d'expertise."""

    __tablename__ = "ticket_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    prix_ht: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("49.00")
    )
    tva_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("20.00")
    )
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())
