"""Modèle Dossier — dossier d'expertise."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .step import Step


class Dossier(Base):
    __tablename__ = "dossiers"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(255))
    ticket_id: Mapped[str] = mapped_column(String(255), unique=True)
    domaine: Mapped[str] = mapped_column(String(100))
    statut: Mapped[str] = mapped_column(String(20), default="actif")
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    steps: Mapped[list["Step"]] = relationship(back_populates="dossier")
