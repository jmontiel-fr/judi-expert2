"""Tests unitaires pour le handler Lambda cron_abonnement.

Vérifie le comportement du handler dans différents scénarios :
- Succès complet (token récupéré, endpoint appelé avec succès)
- Erreur Secrets Manager (secret introuvable, vide)
- Erreur réseau (timeout, erreur HTTP)
- Réponse non-200 de l'endpoint
- Variables d'environnement manquantes
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ajouter le répertoire du handler au path
sys.path.insert(
    0,
    str(
        Path(__file__).parent.parent.parent
        / "central-site"
        / "terraform"
        / "lambda"
        / "cron_abonnement"
    ),
)

import handler as lambda_handler


class FakeLambdaContext:
    """Contexte Lambda simulé pour les tests."""

    aws_request_id = "test-request-id-123"
    function_name = "cron_abonnement"
    memory_limit_in_mb = 128
    invoked_function_arn = "arn:aws:lambda:eu-west-1:123456789:function:cron_abonnement"


@pytest.fixture
def lambda_context():
    """Fixture fournissant un contexte Lambda simulé."""
    return FakeLambdaContext()


@pytest.fixture
def env_vars(monkeypatch):
    """Fixture configurant les variables d'environnement requises."""
    monkeypatch.setattr(lambda_handler, "API_BASE_URL", "https://api.judi-expert.fr")
    monkeypatch.setattr(
        lambda_handler, "CRON_TOKEN_SECRET_NAME", "judi-expert/cron-token"
    )
    monkeypatch.setattr(lambda_handler, "AWS_REGION", "eu-west-1")


class TestGetCronToken:
    """Tests pour la récupération du token depuis Secrets Manager."""

    def test_secret_name_not_configured(self, monkeypatch):
        """Erreur si CRON_TOKEN_SECRET_NAME est vide."""
        monkeypatch.setattr(lambda_handler, "CRON_TOKEN_SECRET_NAME", "")

        with pytest.raises(RuntimeError, match="CRON_TOKEN_SECRET_NAME non configurée"):
            lambda_handler.get_cron_token()

    @patch("handler.boto3.client")
    def test_secret_string_plain(self, mock_boto_client, env_vars):
        """Récupère un token en texte brut."""
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {"SecretString": "my-secret-token"}
        mock_boto_client.return_value = mock_sm

        token = lambda_handler.get_cron_token()

        assert token == "my-secret-token"
        mock_sm.get_secret_value.assert_called_once_with(
            SecretId="judi-expert/cron-token"
        )

    @patch("handler.boto3.client")
    def test_secret_string_json_with_token_key(self, mock_boto_client, env_vars):
        """Récupère un token depuis un secret JSON avec clé 'token'."""
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            "SecretString": json.dumps({"token": "json-token-value"})
        }
        mock_boto_client.return_value = mock_sm

        token = lambda_handler.get_cron_token()

        assert token == "json-token-value"

    @patch("handler.boto3.client")
    def test_secret_empty(self, mock_boto_client, env_vars):
        """Erreur si le secret est vide."""
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {"SecretString": ""}
        mock_boto_client.return_value = mock_sm

        with pytest.raises(RuntimeError, match="est vide"):
            lambda_handler.get_cron_token()

    @patch("handler.boto3.client")
    def test_secrets_manager_client_error(self, mock_boto_client, env_vars):
        """Erreur si Secrets Manager retourne une erreur."""
        from botocore.exceptions import ClientError

        mock_sm = MagicMock()
        mock_sm.get_secret_value.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Not found"}},
            "GetSecretValue",
        )
        mock_boto_client.return_value = mock_sm

        with pytest.raises(RuntimeError, match="ResourceNotFoundException"):
            lambda_handler.get_cron_token()


class TestCallSubscriptionCheck:
    """Tests pour l'appel à l'endpoint interne."""

    def test_api_base_url_not_configured(self, monkeypatch):
        """Erreur si API_BASE_URL est vide."""
        monkeypatch.setattr(lambda_handler, "API_BASE_URL", "")

        with pytest.raises(RuntimeError, match="API_BASE_URL non configurée"):
            lambda_handler.call_subscription_check("token")

    @patch("handler.http")
    def test_successful_call(self, mock_http, env_vars):
        """Appel réussi avec réponse 200."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = json.dumps(
            {"processed": 5, "emails_sent": 3, "blocked": 1}
        ).encode("utf-8")
        mock_http.request.return_value = mock_response

        result = lambda_handler.call_subscription_check("my-token")

        assert result == {"processed": 5, "emails_sent": 3, "blocked": 1}
        mock_http.request.assert_called_once_with(
            "POST",
            "https://api.judi-expert.fr/api/internal/cron/subscription-check",
            headers={
                "X-Cron-Token": "my-token",
                "Content-Type": "application/json",
            },
            body=b"",
        )

    @patch("handler.http")
    def test_timeout_error(self, mock_http, env_vars):
        """Erreur de timeout lors de l'appel."""
        import urllib3

        mock_http.request.side_effect = urllib3.exceptions.TimeoutError()

        with pytest.raises(RuntimeError, match="Timeout"):
            lambda_handler.call_subscription_check("my-token")

    @patch("handler.http")
    def test_http_error(self, mock_http, env_vars):
        """Erreur réseau lors de l'appel."""
        import urllib3

        mock_http.request.side_effect = urllib3.exceptions.HTTPError("Connection refused")

        with pytest.raises(RuntimeError, match="Erreur réseau"):
            lambda_handler.call_subscription_check("my-token")

    @patch("handler.http")
    def test_non_200_response(self, mock_http, env_vars):
        """Erreur si la réponse n'est pas 200."""
        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.data = b'{"detail": "Token invalide"}'
        mock_http.request.return_value = mock_response

        with pytest.raises(RuntimeError, match="statut 401"):
            lambda_handler.call_subscription_check("my-token")

    @patch("handler.http")
    def test_non_json_response(self, mock_http, env_vars):
        """Erreur si la réponse 200 n'est pas du JSON valide."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b"not json"
        mock_http.request.return_value = mock_response

        with pytest.raises(RuntimeError, match="non-JSON"):
            lambda_handler.call_subscription_check("my-token")

    @patch("handler.http")
    def test_trailing_slash_in_base_url(self, mock_http, monkeypatch):
        """L'URL de base avec un slash final est gérée correctement."""
        monkeypatch.setattr(
            lambda_handler, "API_BASE_URL", "https://api.judi-expert.fr/"
        )
        monkeypatch.setattr(
            lambda_handler, "CRON_TOKEN_SECRET_NAME", "judi-expert/cron-token"
        )

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = json.dumps(
            {"processed": 0, "emails_sent": 0, "blocked": 0}
        ).encode("utf-8")
        mock_http.request.return_value = mock_response

        lambda_handler.call_subscription_check("token")

        call_args = mock_http.request.call_args
        assert (
            call_args[0][1]
            == "https://api.judi-expert.fr/api/internal/cron/subscription-check"
        )


class TestHandler:
    """Tests pour le handler Lambda principal."""

    @patch("handler.call_subscription_check")
    @patch("handler.get_cron_token")
    def test_success(self, mock_get_token, mock_call, lambda_context, env_vars):
        """Handler retourne succès quand tout fonctionne."""
        mock_get_token.return_value = "my-token"
        mock_call.return_value = {"processed": 3, "emails_sent": 2, "blocked": 1}

        result = lambda_handler.handler({}, lambda_context)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "success"
        assert body["result"]["processed"] == 3
        assert body["result"]["emails_sent"] == 2
        assert body["result"]["blocked"] == 1

    @patch("handler.get_cron_token")
    def test_secrets_manager_error(self, mock_get_token, lambda_context, env_vars):
        """Handler retourne erreur si Secrets Manager échoue."""
        mock_get_token.side_effect = RuntimeError("Secret introuvable")

        result = lambda_handler.handler({}, lambda_context)

        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert body["status"] == "error"
        assert "Secret introuvable" in body["error"]

    @patch("handler.call_subscription_check")
    @patch("handler.get_cron_token")
    def test_endpoint_error(
        self, mock_get_token, mock_call, lambda_context, env_vars
    ):
        """Handler retourne erreur si l'endpoint échoue."""
        mock_get_token.return_value = "my-token"
        mock_call.side_effect = RuntimeError("Timeout lors de l'appel")

        result = lambda_handler.handler({}, lambda_context)

        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert body["status"] == "error"
        assert "Timeout" in body["error"]

    @patch("handler.get_cron_token")
    def test_unexpected_error(self, mock_get_token, lambda_context, env_vars):
        """Handler gère les erreurs inattendues."""
        mock_get_token.side_effect = ValueError("Erreur inattendue")

        result = lambda_handler.handler({}, lambda_context)

        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert body["status"] == "error"
        assert "inattendue" in body["error"]
