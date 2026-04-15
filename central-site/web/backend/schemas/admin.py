"""Schémas Pydantic pour l'administration du Site Central."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class ExpertListResponse(BaseModel):
    """Détails d'un expert pour la liste d'administration."""

    id: int
    email: str
    nom: str
    prenom: str
    domaine: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MonthStats(BaseModel):
    """Statistiques d'un mois passé."""

    month: str
    count: int
    amount: Decimal


class TicketStatsResponse(BaseModel):
    """Statistiques des tickets avec filtrage par domaine."""

    today_count: int
    today_amount: Decimal
    month_count: int
    month_amount: Decimal
    past_months: list[MonthStats]
