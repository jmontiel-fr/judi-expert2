"""Middleware d'isolation des données d'expertise.

Filet de sécurité qui vérifie que les requêtes sortantes vers le Site Central
ne contiennent que des données de ticket (ticket_code) pour les POST.
Les requêtes GET (sans body) sont autorisées (ex: récupération versions RAG).
Aucune donnée d'expertise (dossiers, fichiers, markdown, rapports) ne doit transiter.

Valide : Exigences 32.1, 32.2
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

SITE_CENTRAL_URL: str = os.environ.get(
    "SITE_CENTRAL_URL", "https://www.judi-expert.fr"
)

# Seuls ces champs sont autorisés dans le body des requêtes POST vers le Site Central
ALLOWED_OUTBOUND_FIELDS = frozenset({"ticket_code"})


def validate_outbound_payload(payload: dict | None, destination_url: str) -> bool:
    """Vérifie qu'un payload sortant vers le Site Central ne contient que des champs autorisés.

    Parameters
    ----------
    payload:
        Corps JSON de la requête sortante. None pour les requêtes GET.
    destination_url:
        URL de destination de la requête.

    Returns
    -------
    bool
        True si le payload est conforme, False sinon.
    """
    if payload is None:
        return True

    # Ne vérifier que les requêtes vers le Site Central
    if not destination_url.startswith(SITE_CENTRAL_URL):
        return True

    extra_fields = set(payload.keys()) - ALLOWED_OUTBOUND_FIELDS
    if extra_fields:
        logger.warning(
            "ALERTE ISOLATION DONNÉES : requête vers %s contient des champs "
            "non autorisés : %s. Seul 'ticket_code' est autorisé.",
            destination_url,
            extra_fields,
        )
        return False

    return True
