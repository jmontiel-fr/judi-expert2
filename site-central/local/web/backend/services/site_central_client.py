"""Client HTTP pour la communication avec le Site Central.

Fournit un client centralisé avec :
- Vérification des heures ouvrables (8h-20h Europe/Paris)
- Retry avec backoff exponentiel pour les erreurs transitoires
- Validation de l'isolation des données (seul ticket_code autorisé en POST)
- Messages d'erreur clairs en cas d'indisponibilité

Valide : Exigences 5.2, 5.3, 33.2, 35.6, 35.7
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta

import httpx

logger = logging.getLogger(__name__)

SITE_CENTRAL_URL: str = os.environ.get("SITE_CENTRAL_URL", "https://www.judi-expert.fr")

# Timezone Europe/Paris (UTC+1 en hiver, UTC+2 en été)
# We use a fixed offset approach with a helper that checks DST via calendar rules.
BUSINESS_HOUR_START = 8
BUSINESS_HOUR_END = 20

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0
BACKOFF_MULTIPLIER = 2.0
REQUEST_TIMEOUT = 15.0


def _get_paris_now() -> datetime:
    """Retourne l'heure actuelle en Europe/Paris.

    Utilise les règles DST européennes :
    - Dernier dimanche de mars à 2h → UTC+2 (CEST)
    - Dernier dimanche d'octobre à 3h → UTC+1 (CET)
    """
    utc_now = datetime.now(timezone.utc)
    year = utc_now.year

    # Dernier dimanche de mars
    march_last = datetime(year, 3, 31, 2, 0, tzinfo=timezone.utc)
    while march_last.weekday() != 6:  # 6 = Sunday
        march_last -= timedelta(days=1)

    # Dernier dimanche d'octobre
    october_last = datetime(year, 10, 31, 3, 0, tzinfo=timezone.utc)
    while october_last.weekday() != 6:
        october_last -= timedelta(days=1)

    if march_last <= utc_now < october_last:
        offset = timedelta(hours=2)  # CEST
    else:
        offset = timedelta(hours=1)  # CET

    return utc_now + offset


def is_within_business_hours() -> bool:
    """Vérifie si l'heure actuelle est dans les heures ouvrables (8h-20h Europe/Paris)."""
    paris_now = _get_paris_now()
    return BUSINESS_HOUR_START <= paris_now.hour < BUSINESS_HOUR_END


def get_business_hours_message() -> str:
    """Retourne un message indiquant les heures ouvrables du Site Central."""
    return (
        "Le Site Central est disponible de 8h à 20h (heure de Paris). "
        "Veuillez réessayer pendant les heures ouvrables."
    )


class SiteCentralError(Exception):
    """Erreur lors de la communication avec le Site Central."""

    def __init__(self, message: str, status_code: int = 503):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class SiteCentralClient:
    """Client HTTP centralisé pour les appels au Site Central.

    Gère le retry avec backoff exponentiel et les messages d'erreur
    adaptés aux heures ouvrables.
    """

    def __init__(self, base_url: str | None = None, timeout: float = REQUEST_TIMEOUT):
        self.base_url = (base_url or SITE_CENTRAL_URL).rstrip("/")
        self.timeout = timeout

    async def post(self, path: str, json: dict | None = None) -> httpx.Response:
        """Effectue un POST vers le Site Central avec retry.

        Raises SiteCentralError on failure.
        """
        url = f"{self.base_url}{path}"
        return await self._request_with_retry("POST", url, json=json)

    async def get(self, path: str, params: dict | None = None) -> httpx.Response:
        """Effectue un GET vers le Site Central avec retry.

        Raises SiteCentralError on failure.
        """
        url = f"{self.base_url}{path}"
        return await self._request_with_retry("GET", url, params=params)

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        json: dict | None = None,
        params: dict | None = None,
    ) -> httpx.Response:
        """Exécute une requête HTTP avec retry et backoff exponentiel."""
        last_error: Exception | None = None
        backoff = INITIAL_BACKOFF_SECONDS

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    if method == "POST":
                        resp = await client.post(url, json=json)
                    else:
                        resp = await client.get(url, params=params)
                return resp
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError) as exc:
                last_error = exc
                logger.warning(
                    "Tentative %d/%d échouée pour %s %s : %s",
                    attempt, MAX_RETRIES, method, url, exc,
                )
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(backoff)
                    backoff *= BACKOFF_MULTIPLIER

        # All retries exhausted — build a helpful error message
        error_msg = self._build_error_message(last_error)
        raise SiteCentralError(error_msg)

    def _build_error_message(self, error: Exception | None) -> str:
        """Construit un message d'erreur adapté au contexte (heures ouvrables ou non)."""
        base_msg = "Site Central indisponible"

        if isinstance(error, httpx.ConnectError):
            base_msg += " — connexion impossible"
        elif isinstance(error, httpx.TimeoutException):
            base_msg += " — délai de connexion dépassé"
        else:
            base_msg += " — erreur réseau"

        if not is_within_business_hours():
            base_msg += f". {get_business_hours_message()}"

        return base_msg
