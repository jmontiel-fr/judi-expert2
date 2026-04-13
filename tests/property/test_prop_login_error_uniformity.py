"""Test par propriété — Uniformité du message d'erreur de connexion.

**Validates: Requirements 14.3**

Feature: judi-expert, Property 9: Uniformité du message d'erreur de connexion

Propriété 9 : Pour toute combinaison d'identifiants invalides (email incorrect,
mot de passe incorrect, ou les deux), le message d'erreur retourné doit être
identique, ne révélant pas si c'est l'email ou le mot de passe qui est incorrect.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# Import des modules du Site Central avec isolation de modules
# (même technique que test_prop_registration_validation.py)
# ---------------------------------------------------------------------------

_central_backend = str(
    Path(__file__).resolve().parents[2]
    / "site-central"
    / "aws"
    / "web"
    / "backend"
)

_saved_modules = {
    k: sys.modules.pop(k)
    for k in list(sys.modules)
    if k == "models" or k.startswith("models.")
       or k == "schemas" or k.startswith("schemas.")
       or k == "services" or k.startswith("services.")
       or k == "routers" or k.startswith("routers.")
       or k == "database"
       or k == "main"
}
_saved_path = sys.path[:]
sys.path.insert(0, _central_backend)

from routers.auth import UNIFORM_LOGIN_ERROR  # noqa: E402

# Sauvegarder les modules centraux et restaurer les originaux
_central_module_cache = {
    k: sys.modules.pop(k)
    for k in list(sys.modules)
    if k == "models" or k.startswith("models.")
       or k == "schemas" or k.startswith("schemas.")
       or k == "services" or k.startswith("services.")
       or k == "routers" or k.startswith("routers.")
       or k == "database"
       or k == "main"
}
sys.modules.update(_saved_modules)
sys.path[:] = _saved_path


# ---------------------------------------------------------------------------
# Helper : construire une ClientError botocore
# ---------------------------------------------------------------------------

def _make_client_error(error_code: str, message: str = "mocked") -> Exception:
    """Construit une botocore.exceptions.ClientError avec le code donné."""
    from botocore.exceptions import ClientError

    return ClientError(
        error_response={"Error": {"Code": error_code, "Message": message}},
        operation_name="InitiateAuth",
    )


# ---------------------------------------------------------------------------
# Stratégies Hypothesis
# ---------------------------------------------------------------------------

# Emails aléatoires valides
random_emails = st.builds(
    lambda local: f"{local}@example.com",
    st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789"),
        min_size=3,
        max_size=15,
    ),
)

# Mots de passe aléatoires
random_passwords = st.text(
    alphabet=st.sampled_from(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%"
    ),
    min_size=1,
    max_size=30,
)

# Tokens captcha non-vides
captcha_tokens = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789"),
    min_size=5,
    max_size=20,
)


# ---------------------------------------------------------------------------
# Fixture : application FastAPI de test avec mocks
# ---------------------------------------------------------------------------

@pytest.fixture
def test_app():
    """Crée une application FastAPI de test avec captcha et cognito mockés."""
    saved = {
        k: sys.modules.pop(k)
        for k in list(sys.modules)
        if k == "models" or k.startswith("models.")
           or k == "schemas" or k.startswith("schemas.")
           or k == "services" or k.startswith("services.")
           or k == "routers" or k.startswith("routers.")
           or k == "database"
           or k == "main"
    }
    saved_path = sys.path[:]
    sys.path.insert(0, _central_backend)

    try:
        import main as _main_mod
        yield _main_mod.app
    finally:
        for k in list(sys.modules):
            if (k == "models" or k.startswith("models.")
                    or k == "schemas" or k.startswith("schemas.")
                    or k == "services" or k.startswith("services.")
                    or k == "routers" or k.startswith("routers.")
                    or k == "database"
                    or k == "main"):
                sys.modules.pop(k, None)
        sys.modules.update(saved)
        sys.path[:] = saved_path


# ---------------------------------------------------------------------------
# Propriété 9a — Email incorrect → message uniforme "Identifiants invalides"
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    email=random_emails,
    password=random_passwords,
    captcha=captcha_tokens,
)
async def test_wrong_email_returns_uniform_error(
    test_app,
    email: str,
    password: str,
    captcha: str,
):
    """Pour tout email inconnu (UserNotFoundException), le message d'erreur
    est exactement 'Identifiants invalides' avec status 401."""
    with patch(
        "routers.auth.captcha_service.verify_captcha",
        new_callable=AsyncMock,
        return_value=True,
    ), patch(
        "routers.auth.cognito_service.login_user",
        side_effect=_make_client_error("UserNotFoundException"),
    ):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/auth/login",
                json={
                    "email": email,
                    "password": password,
                    "captcha_token": captcha,
                },
            )

    assert response.status_code == 401
    assert response.json()["detail"] == UNIFORM_LOGIN_ERROR


# ---------------------------------------------------------------------------
# Propriété 9b — Mot de passe incorrect → message uniforme
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    email=random_emails,
    password=random_passwords,
    captcha=captcha_tokens,
)
async def test_wrong_password_returns_uniform_error(
    test_app,
    email: str,
    password: str,
    captcha: str,
):
    """Pour tout mot de passe incorrect (NotAuthorizedException), le message
    d'erreur est exactement 'Identifiants invalides' avec status 401."""
    with patch(
        "routers.auth.captcha_service.verify_captcha",
        new_callable=AsyncMock,
        return_value=True,
    ), patch(
        "routers.auth.cognito_service.login_user",
        side_effect=_make_client_error("NotAuthorizedException"),
    ):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/auth/login",
                json={
                    "email": email,
                    "password": password,
                    "captcha_token": captcha,
                },
            )

    assert response.status_code == 401
    assert response.json()["detail"] == UNIFORM_LOGIN_ERROR


# ---------------------------------------------------------------------------
# Propriété 9c — Email ET mot de passe incorrects → message uniforme
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    email=random_emails,
    password=random_passwords,
    captcha=captcha_tokens,
    error_code=st.sampled_from(["UserNotFoundException", "NotAuthorizedException"]),
)
async def test_wrong_email_and_password_returns_uniform_error(
    test_app,
    email: str,
    password: str,
    captcha: str,
    error_code: str,
):
    """Pour toute combinaison d'email ET mot de passe incorrects (Cognito
    lève UserNotFoundException ou NotAuthorizedException), le message
    d'erreur est exactement 'Identifiants invalides' avec status 401."""
    with patch(
        "routers.auth.captcha_service.verify_captcha",
        new_callable=AsyncMock,
        return_value=True,
    ), patch(
        "routers.auth.cognito_service.login_user",
        side_effect=_make_client_error(error_code),
    ):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/auth/login",
                json={
                    "email": email,
                    "password": password,
                    "captcha_token": captcha,
                },
            )

    assert response.status_code == 401
    assert response.json()["detail"] == UNIFORM_LOGIN_ERROR


# ---------------------------------------------------------------------------
# Propriété 9d — Les trois scénarios produisent la MÊME réponse d'erreur
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    email=random_emails,
    password=random_passwords,
    captcha=captcha_tokens,
)
async def test_all_error_scenarios_produce_same_response(
    test_app,
    email: str,
    password: str,
    captcha: str,
):
    """Les trois scénarios d'erreur (email inconnu, mot de passe incorrect,
    autre ClientError) produisent exactement la même réponse HTTP
    (même status code et même message)."""
    error_codes = [
        "UserNotFoundException",
        "NotAuthorizedException",
        "UserNotConfirmedException",
    ]
    responses = []

    for code in error_codes:
        with patch(
            "routers.auth.captcha_service.verify_captcha",
            new_callable=AsyncMock,
            return_value=True,
        ), patch(
            "routers.auth.cognito_service.login_user",
            side_effect=_make_client_error(code),
        ):
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/auth/login",
                    json={
                        "email": email,
                        "password": password,
                        "captcha_token": captcha,
                    },
                )
            responses.append((resp.status_code, resp.json()["detail"]))

    # Toutes les réponses doivent être identiques
    first = responses[0]
    for i, resp in enumerate(responses[1:], start=1):
        assert resp == first, (
            f"Scénario {error_codes[i]} a produit {resp}, "
            f"mais {error_codes[0]} a produit {first}"
        )

    # Et elles doivent toutes être 401 + message uniforme
    assert first == (401, UNIFORM_LOGIN_ERROR)
