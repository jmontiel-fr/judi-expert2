"""Modèle AppVersion — versions publiées de l'Application Locale."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AppVersion(Base):
    __tablename__ = "app_version"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    download_url: Mapped[str] = mapped_column(String(500), nullable=False)
    mandatory: Mapped[bool] = mapped_column(default=True)
    release_notes: Mapped[Optional[str]] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(server_default=func.now())
