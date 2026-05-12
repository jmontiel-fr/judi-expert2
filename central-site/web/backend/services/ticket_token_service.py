"""Service de génération et vérification de tokens ticket signés HMAC-SHA256.

Le token ticket est une chaîne non falsifiable au format :
    JE-{base64url(payload)}.{hmac_signature}

Le payload JSON contient :
    - ticket_code : identifiant unique UUID
    - email : email de l'expert acheteur
    - created_at : date d'achat ISO 8601
    - expires_at : date d'expiration ISO 8601 (+48h)

La signature HMAC-SHA256 garantit l'intégrité et l'authenticité.
Seul le backend central possède la clé secrète.
"""

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone

TICKET_SECRET = os.environ.get("TICKET_SECRET", "judi-ticket-secret-change-me-in-prod")
TICKET_VALIDITY_HOURS = int(os.environ.get("TICKET_VALIDITY_HOURS", "48"))


def generate_ticket_token(
    ticket_code: str,
    email: str,
    created_at: datetime | None = None,
) -> str:
    """Génère un token ticket signé.

    Args:
        ticket_code: Identifiant unique du ticket (UUID).
        email: Email de l'expert acheteur.
        created_at: Date de création (défaut: maintenant UTC).

    Returns:
        Token au format JE-{base64url_payload}.{signature}
    """
    if created_at is None:
        created_at = datetime.now(timezone.utc)

    expires_at = created_at + timedelta(hours=TICKET_VALIDITY_HOURS)

    payload = {
        "ticket_code": ticket_code,
        "email": email,
        "created_at": created_at.isoformat(),
        "expires_at": expires_at.isoformat(),
    }

    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip("=")

    signature = _sign(payload_b64)

    return f"JE-{payload_b64}.{signature}"


def verify_ticket_token(token: str) -> dict:
    """Vérifie un token ticket et retourne le payload décodé.

    Args:
        token: Token au format JE-{payload}.{signature}

    Returns:
        Dict avec les clés :
            - valid (bool)
            - error (str | None) : "invalide", "périmé", "format_invalide"
            - payload (dict | None) : payload décodé si valide

    Ne vérifie PAS le statut en base de données (utilisé/actif).
    Cette vérification est faite par le router.
    """
    if not token or not token.startswith("JE-"):
        return {"valid": False, "error": "format_invalide", "payload": None}

    token_body = token[3:]  # Remove "JE-" prefix
    parts = token_body.rsplit(".", 1)
    if len(parts) != 2:
        return {"valid": False, "error": "format_invalide", "payload": None}

    payload_b64, signature = parts

    # Verify signature
    expected_sig = _sign(payload_b64)
    if not hmac.compare_digest(signature, expected_sig):
        return {"valid": False, "error": "invalide", "payload": None}

    # Decode payload
    try:
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload_json = base64.urlsafe_b64decode(payload_b64).decode()
        payload = json.loads(payload_json)
    except Exception:
        return {"valid": False, "error": "invalide", "payload": None}

    # Check expiration
    try:
        expires_at = datetime.fromisoformat(payload["expires_at"])
        if datetime.now(timezone.utc) > expires_at:
            return {"valid": False, "error": "périmé", "payload": payload}
    except (KeyError, ValueError):
        return {"valid": False, "error": "invalide", "payload": None}

    return {"valid": True, "error": None, "payload": payload}


def _sign(data: str) -> str:
    """Calcule la signature HMAC-SHA256 en base64url."""
    sig_bytes = hmac.HMAC(
        TICKET_SECRET.encode(),
        data.encode(),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(sig_bytes).decode().rstrip("=")
