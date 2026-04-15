"""Modèle Expert — expert judiciaire inscrit sur le Site Central."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .contact_message import ContactMessage
    from .ticket import Ticket


class Expert(Base):
    __tablename__ = "experts"

    id: Mapped[int] = mapped_column(primary_key=True)
    cognito_sub: Mapped[str] = mapped_column(String(255), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    nom: Mapped[str] = mapped_column(String(100))
    prenom: Mapped[str] = mapped_column(String(100))
    adresse: Mapped[str] = mapped_column(Text)
    ville: Mapped[str] = mapped_column(String(100), default="")
    code_postal: Mapped[str] = mapped_column(String(10), default="")
    telephone: Mapped[str] = mapped_column(String(20), default="")
    domaine: Mapped[str] = mapped_column(String(100))
    accept_newsletter: Mapped[bool] = mapped_column(default=False)
    is_deleted: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    tickets: Mapped[list["Ticket"]] = relationship(back_populates="expert")
    contact_messages: Mapped[list["ContactMessage"]] = relationship(back_populates="expert")
