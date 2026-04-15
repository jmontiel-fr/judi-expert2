"""Modèle ContactMessage — message de contact envoyé par un expert."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .expert import Expert


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    expert_id: Mapped[Optional[int]] = mapped_column(ForeignKey("experts.id"))
    domaine: Mapped[str] = mapped_column(String(100))
    objet: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text)
    bloquant: Mapped[bool] = mapped_column(default=False)
    urgent: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    expert: Mapped[Optional["Expert"]] = relationship(back_populates="contact_messages")
