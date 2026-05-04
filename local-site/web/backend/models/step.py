"""Modèle Step — étape d'un dossier d'expertise."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .dossier import Dossier
    from .step_file import StepFile


class Step(Base):
    __tablename__ = "steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    dossier_id: Mapped[int] = mapped_column(ForeignKey("dossiers.id"))
    step_number: Mapped[int] = mapped_column()  # 1, 2, 3, 4, 5
    statut: Mapped[str] = mapped_column(String(20), default="initial")
    executed_at: Mapped[Optional[datetime]] = mapped_column()
    validated_at: Mapped[Optional[datetime]] = mapped_column()

    dossier: Mapped["Dossier"] = relationship(back_populates="steps")
    files: Mapped[list["StepFile"]] = relationship(back_populates="step")
