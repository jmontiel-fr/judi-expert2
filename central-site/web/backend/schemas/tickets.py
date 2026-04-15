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
    domaine: str
    statut: str
    montant: Decimal
    created_at: datetime
    used_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TicketVerifyRequest(BaseModel):
    """Requête de vérification d'un ticket."""

    ticket_code: str


class TicketVerifyResponse(BaseModel):
    """Réponse de vérification d'un ticket."""

    success: bool
    ticket_code: str
    error: Optional[str] = None
