"""Schémas Pydantic pour la gestion des abonnements et résiliations."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SubscriptionStatus(str, Enum):
    """Statuts possibles d'un abonnement expert.

    Valeurs :
        active : abonnement en cours, paiement à jour
        blocked : paiement en échec depuis plus de 5 jours, accès suspendu
        terminating : résiliation programmée, accès maintenu jusqu'à fin de période
        terminated : abonnement résilié effectivement
    """

    active = "active"
    blocked = "blocked"
    terminating = "terminating"
    terminated = "terminated"


class SubscriptionResponse(BaseModel):
    """Réponse contenant le statut de l'abonnement d'un expert.

    Utilisé par GET /api/subscription/status.
    """

    status: SubscriptionStatus
    termination_date: Optional[datetime] = Field(
        default=None,
        description="Date effective de résiliation (si programmée)",
    )
    current_period_end: datetime = Field(
        description="Fin de la période de facturation en cours",
    )

    model_config = {"from_attributes": True}


class TerminationRequest(BaseModel):
    """Requête de résiliation d'abonnement par l'expert.

    Le corps est vide : l'identité de l'expert est déduite du token JWT.
    """

    pass


class TerminationResponse(BaseModel):
    """Réponse après programmation d'une résiliation.

    Utilisé par POST /api/subscription/terminate.
    """

    termination_date: datetime = Field(
        description="Date effective de fin d'abonnement (fin du mois de facturation)",
    )
    message: str = Field(
        description="Message de confirmation de la résiliation",
    )


class CronCheckResponse(BaseModel):
    """Réponse du cron de vérification des abonnements.

    Utilisé par POST /api/internal/cron/subscription-check.
    """

    processed: int = Field(
        description="Nombre d'abonnements en échec traités",
    )
    emails_sent: int = Field(
        description="Nombre d'emails envoyés (relance + suspension)",
    )
    blocked: int = Field(
        description="Nombre d'abonnements bloqués lors de cette exécution",
    )
