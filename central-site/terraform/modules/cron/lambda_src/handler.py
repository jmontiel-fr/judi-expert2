"""
Lambda handler — Cron Abonnement.

Invoqué quotidiennement par EventBridge pour vérifier les incidents
de paiement d'abonnement via POST /api/internal/cron/subscription-check.
"""

import json
import logging
import os
from urllib import request, error

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_cron_token() -> str:
    """Récupère le token d'authentification depuis AWS Secrets Manager."""
    secret_name = os.environ["SECRET_NAME"]
    region = os.environ.get("AWS_REGION_NAME", "eu-west-1")

    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_name)
    secret = json.loads(response["SecretString"])
    return secret["token"]


def lambda_handler(event, context):
    """Handler principal de la Lambda cron abonnement."""
    api_base_url = os.environ["API_BASE_URL"]
    endpoint = f"{api_base_url}/api/internal/cron/subscription-check"

    logger.info("Démarrage du cron abonnement — endpoint: %s", endpoint)

    try:
        token = get_cron_token()
    except Exception as exc:
        logger.error("Impossible de récupérer le token cron: %s", exc)
        raise

    headers = {
        "X-Cron-Token": token,
        "Content-Type": "application/json",
    }

    req = request.Request(
        url=endpoint,
        method="POST",
        headers=headers,
        data=b"{}",
    )

    try:
        with request.urlopen(req, timeout=50) as resp:
            status_code = resp.status
            body = json.loads(resp.read().decode("utf-8"))

        logger.info(
            "Cron abonnement terminé — status=%d, processed=%s, blocked=%s",
            status_code,
            body.get("processed"),
            body.get("blocked"),
        )

        return {
            "statusCode": status_code,
            "body": body,
        }

    except error.HTTPError as exc:
        logger.error(
            "Erreur HTTP lors de l'appel au cron endpoint: %d %s",
            exc.code,
            exc.reason,
        )
        raise

    except error.URLError as exc:
        logger.error("Erreur réseau lors de l'appel au cron endpoint: %s", exc.reason)
        raise

    except Exception as exc:
        logger.error("Erreur inattendue: %s", exc)
        raise
