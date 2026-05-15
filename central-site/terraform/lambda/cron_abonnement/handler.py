"""Lambda handler — Cron de relance des abonnements.

Ce handler est déclenché quotidiennement par EventBridge. Il :
1. Récupère le token d'authentification depuis AWS Secrets Manager.
2. Appelle l'endpoint interne POST /api/internal/cron/subscription-check
   avec le header X-Cron-Token.
3. Gère les erreurs (timeout, réponse non-200, Secrets Manager).

Variables d'environnement requises :
    API_BASE_URL: URL de base de l'API (ex: https://api.judi-expert.fr)
    CRON_TOKEN_SECRET_NAME: Nom du secret dans Secrets Manager
    AWS_REGION: Région AWS (défaut: eu-west-1)
"""

import json
import logging
import os
from typing import Any

import boto3
import urllib3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configuration via variables d'environnement
API_BASE_URL = os.environ.get("API_BASE_URL", "")
CRON_TOKEN_SECRET_NAME = os.environ.get("CRON_TOKEN_SECRET_NAME", "")
AWS_REGION = os.environ.get("AWS_REGION", "eu-west-1")

# Timeout pour l'appel HTTP (en secondes)
HTTP_TIMEOUT = 30.0

# Client HTTP (réutilisé entre les invocations)
http = urllib3.PoolManager(
    timeout=urllib3.Timeout(connect=5.0, read=HTTP_TIMEOUT),
    retries=urllib3.Retry(total=1, backoff_factor=0.5),
)


def get_cron_token() -> str:
    """Récupère le token d'authentification depuis AWS Secrets Manager.

    Returns:
        Le token cron sous forme de chaîne.

    Raises:
        RuntimeError: Si le secret ne peut pas être récupéré.
    """
    if not CRON_TOKEN_SECRET_NAME:
        raise RuntimeError(
            "Variable d'environnement CRON_TOKEN_SECRET_NAME non configurée"
        )

    client = boto3.client("secretsmanager", region_name=AWS_REGION)

    try:
        response = client.get_secret_value(SecretId=CRON_TOKEN_SECRET_NAME)
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        logger.error(
            "Erreur Secrets Manager (%s) pour le secret '%s': %s",
            error_code,
            CRON_TOKEN_SECRET_NAME,
            str(e),
        )
        raise RuntimeError(
            f"Impossible de récupérer le secret '{CRON_TOKEN_SECRET_NAME}': {error_code}"
        ) from e

    # Le secret peut être une chaîne simple ou un JSON
    secret_value = response.get("SecretString", "")
    if not secret_value:
        raise RuntimeError(
            f"Le secret '{CRON_TOKEN_SECRET_NAME}' est vide"
        )

    # Si le secret est un JSON avec une clé "token", l'extraire
    try:
        secret_data = json.loads(secret_value)
        if isinstance(secret_data, dict) and "token" in secret_data:
            return secret_data["token"]
    except (json.JSONDecodeError, TypeError):
        pass

    # Sinon, utiliser la valeur brute
    return secret_value


def call_subscription_check(token: str) -> dict[str, Any]:
    """Appelle l'endpoint interne de vérification des abonnements.

    Args:
        token: Token d'authentification pour le header X-Cron-Token.

    Returns:
        Dictionnaire avec les résultats du traitement.

    Raises:
        RuntimeError: Si l'appel échoue (timeout, erreur réseau, non-200).
    """
    if not API_BASE_URL:
        raise RuntimeError(
            "Variable d'environnement API_BASE_URL non configurée"
        )

    url = f"{API_BASE_URL.rstrip('/')}/api/internal/cron/subscription-check"

    headers = {
        "X-Cron-Token": token,
        "Content-Type": "application/json",
    }

    logger.info("Appel de l'endpoint cron: POST %s", url)

    try:
        response = http.request(
            "POST",
            url,
            headers=headers,
            body=b"",
        )
    except urllib3.exceptions.TimeoutError as e:
        logger.error("Timeout lors de l'appel à %s: %s", url, str(e))
        raise RuntimeError(
            f"Timeout lors de l'appel à l'endpoint cron ({HTTP_TIMEOUT}s)"
        ) from e
    except urllib3.exceptions.HTTPError as e:
        logger.error("Erreur réseau lors de l'appel à %s: %s", url, str(e))
        raise RuntimeError(
            f"Erreur réseau lors de l'appel à l'endpoint cron: {str(e)}"
        ) from e

    if response.status != 200:
        body = response.data.decode("utf-8", errors="replace")
        logger.error(
            "Réponse non-200 de l'endpoint cron: status=%d, body=%s",
            response.status,
            body[:500],
        )
        raise RuntimeError(
            f"L'endpoint cron a retourné le statut {response.status}: {body[:200]}"
        )

    # Parser la réponse JSON
    try:
        result = json.loads(response.data.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error("Réponse non-JSON de l'endpoint cron: %s", str(e))
        raise RuntimeError(
            "L'endpoint cron a retourné une réponse non-JSON"
        ) from e

    return result


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Point d'entrée de la Lambda.

    Déclenché par EventBridge selon un schedule quotidien.
    Récupère le token depuis Secrets Manager, puis appelle l'endpoint
    interne de vérification des abonnements.

    Args:
        event: Événement EventBridge (non utilisé directement).
        context: Contexte Lambda AWS.

    Returns:
        Dictionnaire avec le statut et les résultats du traitement.
    """
    logger.info(
        "Démarrage du cron abonnement (request_id=%s)",
        getattr(context, "aws_request_id", "local"),
    )

    try:
        # Étape 1 : Récupérer le token depuis Secrets Manager
        token = get_cron_token()
        logger.info("Token récupéré depuis Secrets Manager")

        # Étape 2 : Appeler l'endpoint interne
        result = call_subscription_check(token)
        logger.info(
            "Cron terminé avec succès: processed=%s, emails_sent=%s, blocked=%s",
            result.get("processed", "?"),
            result.get("emails_sent", "?"),
            result.get("blocked", "?"),
        )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "success",
                "result": result,
            }),
        }

    except RuntimeError as e:
        logger.error("Erreur lors de l'exécution du cron: %s", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "error",
                "error": str(e),
            }),
        }
    except Exception as e:
        logger.error(
            "Erreur inattendue lors de l'exécution du cron: %s",
            str(e),
            exc_info=True,
        )
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "error",
                "error": f"Erreur inattendue: {str(e)}",
            }),
        }
