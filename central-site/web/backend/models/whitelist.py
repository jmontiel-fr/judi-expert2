"""Modèle WhitelistEntry — emails autorisés à obtenir des tickets sans paiement."""

from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class WhitelistEntry(Base):
    """Email autorisé à obtenir des tickets gratuitement (sans passer par Stripe)."""

    __tablename__ = "whitelist_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    note: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
