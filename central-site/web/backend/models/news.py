"""Modèle News — actualités publiées par l'administrateur."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class News(Base):
    __tablename__ = "news"

    id: Mapped[int] = mapped_column(primary_key=True)
    titre: Mapped[str] = mapped_column(String(255))
    contenu: Mapped[str] = mapped_column(Text)
    visible: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )


class NewsRead(Base):
    """Trace de lecture d'une news par un expert."""

    __tablename__ = "news_reads"

    id: Mapped[int] = mapped_column(primary_key=True)
    news_id: Mapped[int] = mapped_column()
    expert_id: Mapped[int] = mapped_column()
    read_at: Mapped[datetime] = mapped_column(server_default=func.now())
