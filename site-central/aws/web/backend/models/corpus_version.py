"""Modèle CorpusVersion — version d'un corpus de domaine."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .domaine import Domaine


class CorpusVersion(Base):
    __tablename__ = "corpus_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    domaine_id: Mapped[int] = mapped_column(ForeignKey("domaines.id"))
    version: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text)
    ecr_image_uri: Mapped[str] = mapped_column(String(500))
    published_at: Mapped[datetime] = mapped_column(server_default=func.now())

    domaine: Mapped["Domaine"] = relationship(back_populates="corpus_versions")
