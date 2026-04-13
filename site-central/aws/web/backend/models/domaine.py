"""Modèle Domaine — domaine d'expertise disponible."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .corpus_version import CorpusVersion


class Domaine(Base):
    __tablename__ = "domaines"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(100), unique=True)
    repertoire: Mapped[str] = mapped_column(String(255))
    actif: Mapped[bool] = mapped_column(default=False)

    corpus_versions: Mapped[list["CorpusVersion"]] = relationship(back_populates="domaine")
