"""Test par propriété — Validation du formulaire d'inscription.

**Validates: Requirements 13.3, 13.4, 13.5**

Feature: judi-expert, Property 8: Validation du formulaire d'inscription

Propriété 8 : Pour toute combinaison de champs du formulaire d'inscription et
de cases à cocher, l'inscription doit réussir si et seulement si tous les champs
obligatoires (Nom, Prénom, adresse, Domaine) sont remplis ET toutes les cases
obligatoires (Mentions légales, CGU, engagement protection données) sont cochées.
La case newsletter optionnelle ne doit pas affecter la validité de l'inscription.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Import des modules du Site Central avec isolation de modules
# (même technique que test_prop_ticket_generation.py)
# ---------------------------------------------------------------------------

_central_backend = str(
    Path(__file__).resolve().parents[2]
    / "central-site"
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

import models as _central_models  # noqa: E402
import models.base  # noqa: E402
import models.expert  # noqa: E402
from schemas.auth import RegisterRequest  # noqa: E402

Base = _central_models.Base

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
# Stratégies Hypothesis
# ---------------------------------------------------------------------------

# Champs texte non-vides (valides)
non_empty_text = st.text(min_size=1, max_size=50).filter(lambda s: s.strip() != "")

# Champs texte vides ou blancs (invalides)
blank_text = st.sampled_from(["", " ", "  ", "\t", "\n"])

# Domaines valides
domaines = st.sampled_from([
    "psychologie",
    "psychiatrie",
    "medecine_legale",
    "batiment",
    "comptabilite",
])

# Emails valides
valid_emails = st.builds(
    lambda local: f"{local}@example.com",
    st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789"),
        min_size=3,
        max_size=15,
    ),
)

# Mots de passe valides (>= 8 caractères)
valid_passwords = st.text(
    alphabet=st.sampled_from(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%"
    ),
    min_size=8,
    max_size=30,
)

# Newsletter : True ou False
newsletter_flag = st.booleans()


# ---------------------------------------------------------------------------
# Propriété 8a — Formulaire valide : inscription réussit quel que soit newsletter
# ---------------------------------------------------------------------------

@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    nom=non_empty_text,
    prenom=non_empty_text,
    adresse=non_empty_text,
    ville=non_empty_text,
    code_postal=non_empty_text,
    telephone=non_empty_text,
    domaine=domaines,
    email=valid_emails,
    password=valid_passwords,
    newsletter=newsletter_flag,
)
def test_valid_form_succeeds_regardless_of_newsletter(
    nom: str,
    prenom: str,
    adresse: str,
    ville: str,
    code_postal: str,
    telephone: str,
    domaine: str,
    email: str,
    password: str,
    newsletter: bool,
):
    """Pour tout formulaire valide (tous les champs obligatoires non-vides,
    toutes les cases obligatoires cochées), la validation réussit
    indépendamment de la valeur de la case newsletter."""
    req = RegisterRequest(
        email=email,
        password=password,
        nom=nom,
        prenom=prenom,
        adresse=adresse,
        ville=ville,
        code_postal=code_postal,
        telephone=telephone,
        domaine=domaine,
        accept_mentions_legales=True,
        accept_cgu=True,
        accept_protection_donnees=True,
        accept_newsletter=newsletter,
    )
    # La validation Pydantic a réussi — vérifier les champs
    assert req.nom == nom.strip()
    assert req.prenom == prenom.strip()
    assert req.adresse == adresse.strip()
    assert req.ville == ville.strip()
    assert req.code_postal == code_postal.strip()
    assert req.telephone == telephone.strip()
    assert req.domaine == domaine.strip()
    assert req.accept_mentions_legales is True
    assert req.accept_cgu is True
    assert req.accept_protection_donnees is True
    assert req.accept_newsletter is newsletter


# ---------------------------------------------------------------------------
# Propriété 8b — Au moins un champ obligatoire vide : inscription échoue
# ---------------------------------------------------------------------------

@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    nom=non_empty_text,
    prenom=non_empty_text,
    adresse=non_empty_text,
    ville=non_empty_text,
    code_postal=non_empty_text,
    telephone=non_empty_text,
    domaine=domaines,
    email=valid_emails,
    password=valid_passwords,
    field_to_blank=st.sampled_from(["nom", "prenom", "adresse", "ville", "code_postal", "telephone", "domaine"]),
    blank_value=blank_text,
)
def test_missing_required_field_fails(
    nom: str,
    prenom: str,
    adresse: str,
    ville: str,
    code_postal: str,
    telephone: str,
    domaine: str,
    email: str,
    password: str,
    field_to_blank: str,
    blank_value: str,
):
    """Pour tout formulaire avec au moins un champ obligatoire vide ou blanc,
    la validation échoue avec une erreur 422."""
    fields = {
        "email": email,
        "password": password,
        "nom": nom,
        "prenom": prenom,
        "adresse": adresse,
        "ville": ville,
        "code_postal": code_postal,
        "telephone": telephone,
        "domaine": domaine,
        "accept_mentions_legales": True,
        "accept_cgu": True,
        "accept_protection_donnees": True,
        "accept_newsletter": False,
    }
    fields[field_to_blank] = blank_value

    with pytest.raises(ValidationError):
        RegisterRequest(**fields)


# ---------------------------------------------------------------------------
# Propriété 8c — Au moins une case obligatoire décochée : inscription échoue
# ---------------------------------------------------------------------------

@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    nom=non_empty_text,
    prenom=non_empty_text,
    adresse=non_empty_text,
    ville=non_empty_text,
    code_postal=non_empty_text,
    telephone=non_empty_text,
    domaine=domaines,
    email=valid_emails,
    password=valid_passwords,
    checkbox_to_uncheck=st.sampled_from([
        "accept_mentions_legales",
        "accept_cgu",
        "accept_protection_donnees",
    ]),
)
def test_unchecked_required_checkbox_fails(
    nom: str,
    prenom: str,
    adresse: str,
    ville: str,
    code_postal: str,
    telephone: str,
    domaine: str,
    email: str,
    password: str,
    checkbox_to_uncheck: str,
):
    """Pour tout formulaire avec au moins une case obligatoire décochée,
    la validation échoue avec une erreur 422."""
    fields = {
        "email": email,
        "password": password,
        "nom": nom,
        "prenom": prenom,
        "adresse": adresse,
        "ville": ville,
        "code_postal": code_postal,
        "telephone": telephone,
        "domaine": domaine,
        "accept_mentions_legales": True,
        "accept_cgu": True,
        "accept_protection_donnees": True,
        "accept_newsletter": False,
    }
    fields[checkbox_to_uncheck] = False

    with pytest.raises(ValidationError):
        RegisterRequest(**fields)


# ---------------------------------------------------------------------------
# Propriété 8d — Newsletter n'affecte pas la validité (test HTTP API)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def async_engine():
    """Crée un moteur SQLite en mémoire et initialise le schéma."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_app(async_engine):
    """Crée une application FastAPI de test avec la DB en mémoire et cognito mocké."""
    # Re-import dans le contexte du test pour construire l'app
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
        import database as _db_mod
        import main as _main_mod
        import services.cognito_service as _cognito_mod

        # Override la session factory pour utiliser SQLite en mémoire
        factory = async_sessionmaker(async_engine, expire_on_commit=False)

        async def _override_get_db():
            async with factory() as session:
                yield session

        _main_mod.app.dependency_overrides[_db_mod.get_db] = _override_get_db

        # Mock cognito_service.register_user pour éviter les appels AWS
        _cognito_mod.register_user = lambda **kwargs: {
            "UserSub": f"sub-{uuid4().hex[:12]}",
            "UserConfirmed": False,
        }

        yield _main_mod.app

        _main_mod.app.dependency_overrides.clear()
    finally:
        # Restaurer les modules
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


@pytest.mark.asyncio
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    nom=non_empty_text,
    prenom=non_empty_text,
    adresse=non_empty_text,
    ville=non_empty_text,
    code_postal=non_empty_text,
    telephone=non_empty_text,
    domaine=domaines,
    password=valid_passwords,
    newsletter=newsletter_flag,
)
async def test_newsletter_does_not_affect_registration_via_api(
    test_app,
    async_engine,
    nom: str,
    prenom: str,
    adresse: str,
    ville: str,
    code_postal: str,
    telephone: str,
    domaine: str,
    password: str,
    newsletter: bool,
):
    """La case newsletter (True ou False) ne doit pas affecter le résultat
    de l'inscription quand tous les autres champs sont valides.
    Test via l'endpoint HTTP /api/auth/register."""
    unique_email = f"{uuid4().hex[:12]}@example.com"

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/register",
            json={
                "email": unique_email,
                "password": password,
                "nom": nom,
                "prenom": prenom,
                "adresse": adresse,
                "ville": ville,
                "code_postal": code_postal,
                "telephone": telephone,
                "domaine": domaine,
                "accept_mentions_legales": True,
                "accept_cgu": True,
                "accept_protection_donnees": True,
                "accept_newsletter": newsletter,
            },
        )

    assert response.status_code == 201, (
        f"Inscription devrait réussir avec newsletter={newsletter}, "
        f"mais status={response.status_code}, body={response.text}"
    )
    data = response.json()
    assert "cognito_sub" in data
    assert data["message"] == "Inscription réussie"
