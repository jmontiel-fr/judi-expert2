"""Modèle Expert — expert judiciaire inscrit sur le Site Central."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .contact_message import ContactMessage
    from .subscription import Subscription
    from .ticket import Ticket


class Expert(Base):
    """Expert judiciaire inscrit sur le Site Central.

    Attributes:
        entreprise: Nom de l'entreprise (optionnel).
        company_address: Adresse de l'entreprise (optionnel).
        billing_email: Email de facturation (optionnel).
        siret: Numéro SIRET à 14 chiffres (optionnel, "non attribué" si absent).
    """

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

    # Profil facturation (tous les experts sont B2B dans les metadata Stripe)
    entreprise: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    billing_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    siret: Mapped[Optional[str]] = mapped_column(String(14), nullable=True)

    # Relations
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="expert")
    contact_messages: Mapped[list["ContactMessage"]] = relationship(
        back_populates="expert"
    )
    subscription: Mapped[Optional["Subscription"]] = relationship(
        back_populates="expert"
    )
