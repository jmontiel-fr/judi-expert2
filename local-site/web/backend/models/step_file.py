"""Modèle StepFile — fichier associé à une étape."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .step import Step


class StepFile(Base):
    __tablename__ = "step_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    step_id: Mapped[int] = mapped_column(ForeignKey("steps.id"))
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    file_type: Mapped[str] = mapped_column(String(50))
    file_size: Mapped[int] = mapped_column()
    doc_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    doc_format: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    # Versioning fields
    is_modified: Mapped[bool] = mapped_column(default=False)
    original_file_path: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    step: Mapped["Step"] = relationship(back_populates="files")
