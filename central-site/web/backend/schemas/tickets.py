"""Schémas Pydantic pour les tickets et paiements Stripe."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class PurchaseRequest(BaseModel):
    """Requête d'achat de ticket (le domaine vient du profil expert)."""

    pass


class PurchaseResponse(BaseModel):
    """Réponse contenant l'URL de la session Stripe Checkout."""

    checkout_url: str


class TicketResponse(BaseModel):
    """Détails d'un ticket."""

    id: int
    ticket_code: str
    ticket_token: Optional[str] = None
    domaine: str
    statut: str
    montant: Decimal
    created_at: datetime
    expires_at: Optional[datetime] = None
    used_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TicketVerifyRequest(BaseModel):
    """Requête de vérification d'un token ticket signé."""

    ticket_token: str


class TicketVerifyResponse(BaseModel):
    """Réponse de vérification d'un ticket."""

    success: bool
    ticket_code: str
    error: Optional[str] = None


class TicketPriceResponse(BaseModel):
    """Prix actuel du ticket (public)."""

    prix_ht: Decimal
    tva_rate: Decimal
    prix_ttc: Decimal


class TicketConfigUpdate(BaseModel):
    """Requête de mise à jour de la configuration du prix."""

    prix_ht: Optional[Decimal] = None
    tva_rate: Optional[Decimal] = None
