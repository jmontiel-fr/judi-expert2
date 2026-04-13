"""Modèle LocalConfig — configuration locale de l'Application."""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class LocalConfig(Base):
    __tablename__ = "local_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    domaine: Mapped[str] = mapped_column(String(100))
    rag_version: Mapped[Optional[str]] = mapped_column(String(50))
    is_configured: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
