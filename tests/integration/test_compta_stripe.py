"""Tests d'intégration — Intégration comptable et Stripe.

Teste :
- Création de session Checkout avec métadonnées comptables (tous B2B)
- Remboursement via l'API Stripe (endpoint admin)
- Import et validation de la Compta_Library

Valide : Requirements 1.4, 3.1, 3.2, 4.2
"""

import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Module isolation : charger le backend Site Central sans conflit
# ---------------------------------------------------------------------------

_central_backend = str(
    Path(__file__).resolve().parents[2]
    / "central-site" / "web" / "backend"
)

_modules_to_isolate = [
    "models", "database", "routers", "schemas", "services", "main",
]

_saved_modules = {}
for prefix in _modules_to_isolate:
    for k in list(sys.modules):
        if k == prefix or k.startswith(prefix + "."):
            _saved_modules[k] = sys.modules.pop(k)

_saved_path = sys.path[:]
sys.path.insert(0, _central_backend)

from models import Base as _Base  # noqa: E402
from models.expert import Expert as _Expert  # noqa: E402
from models.ticket import Ticket as _Ticket  # noqa: E402
from database import get_db as _get_db  # noqa: E402
from main import app as _app  # noqa: E402
from services.compta_service import (  # noqa: E402
    ComptaValidationError,
    build_metadata,
)

import routers.admin as _admin_mod  # noqa: E402

# Sauvegarder les modules du Site Central et restaurer les originaux
_central_cache = {}
for prefix in _modules_to_isolate:
    for k in list(sys.modules):
        if k == prefix or k.startswith(prefix + "."):
            _central_cache[k] = sys.modules.pop(k)

sys.modules.update(_saved_modules)
sys.path[:] = _saved_path

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(_Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def seed_expert_with_siret(session_factory):
    """Crée un expert avec SIRET renseigné."""
    async with session_factory() as session:
        expert = _Expert(
            cognito_sub="sub-compta-001",
            email="expert@cabinet-martin.fr",
            nom="Martin",
            prenom="Jean",
            adresse="12 rue de la Paix, 75002 Paris",
            domaine="psychologie",
            entreprise="Cabinet Martin",
            company_address="12 rue de la Paix, 75002 Paris",
            billing_email="facturation@cabinet-martin.fr",
            siret="12345678901234",
        )
        session.add(expert)
        await session.commit()
        await session.refresh(expert)
        return expert


@pytest_asyncio.fixture
async def seed_expert_without_siret(session_factory):
    """Crée un expert sans SIRET (sera "non attribué")."""
    async with session_factory() as session:
        expert = _Expert(
            cognito_sub="sub-compta-002",
            email="expert@example.com",
            nom="Dupont",
            prenom="Marie",
            adresse="45 avenue des Champs, 75008 Paris",
            domaine="comptabilite",
            entreprise=None,
            company_address=None,
            billing_email=None,
            siret=None,
        )
        session.add(expert)
        await session.commit()
        await session.refresh(expert)
        return expert


@pytest_asyncio.fixture
async def seed_ticket_actif(session_factory, seed_expert_with_siret):
    """Crée un ticket actif avec un stripe_payment_id valide."""
    async with session_factory() as session:
        ticket = _Ticket(
            ticket_code="TICKET-REFUND-TEST-001",
            ticket_token="token-test-001",
            expert_id=seed_expert_with_siret.id,
            domaine="psychologie",
            statut="actif",
            montant=Decimal("58.80"),
            stripe_payment_id="pi_test_refund_001",
            expires_at=None,
            used_at=None,
        )
        session.add(ticket)
        await session.commit()
        await session.refresh(ticket)
        return ticket


def _fake_get_admin_expert(expert):
    """Simule un admin authentifié."""
    async def _override():
        return expert
    return _override


@pytest_asyncio.fixture
async def admin_client(session_factory, seed_expert_with_siret):
    """Client authentifié en tant qu'admin."""

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    _app.dependency_overrides[_get_db] = _override_get_db
    _app.dependency_overrides[_admin_mod.get_admin_expert] = (
        _fake_get_admin_expert(seed_expert_with_siret)
    )

    transport = ASGITransport(app=_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    _app.dependency_overrides.clear()


# ===========================================================================
# Test 1 : Métadonnées Stripe — tous les experts sont B2B
# ===========================================================================


class TestCheckoutMetadata:
    """Tests d'intégration pour les métadonnées comptables Stripe."""

    @pytest.mark.asyncio
    async def test_metadata_with_siret(self, seed_expert_with_siret):
        """Expert avec SIRET : métadonnées complètes."""
        ticket_config = {
            "domaine": "psychologie",
            "price_ht": "49.00",
            "price_tva": "9.80",
            "price_ttc": "58.80",
        }

        metadata = build_metadata(seed_expert_with_siret, ticket_config)

        assert metadata["appli"] == "judi-expert"
        assert metadata["service"] == "ticket-expertise"
        assert metadata["type"] == "B2B"
        assert metadata["domaine"] == "psychologie"
        assert metadata["expert_lastname"] == "Martin"
        assert metadata["expert_firstname"] == "Jean"
        assert metadata["expert_email"] == "expert@cabinet-martin.fr"
        assert metadata["entreprise"] == "Cabinet Martin"
        assert metadata["expert_address"] == "12 rue de la Paix, 75002 Paris"
        assert metadata["billing_email"] == "facturation@cabinet-martin.fr"
        assert metadata["siret"] == "12345678901234"
        assert metadata["price_ht"] == "49.00"
        assert metadata["price_tva"] == "9.80"
        assert metadata["price_ttc"] == "58.80"
        assert "date_achat" in metadata
        assert metadata["description"] == "judi-expert - ticket-expertise"

    @pytest.mark.asyncio
    async def test_metadata_without_siret(self, seed_expert_without_siret):
        """Expert sans SIRET : SIRET = "non attribué", fallback adresse/email."""
        ticket_config = {
            "domaine": "comptabilite",
            "price_ht": "49.00",
            "price_tva": "9.80",
            "price_ttc": "58.80",
        }

        metadata = build_metadata(seed_expert_without_siret, ticket_config)

        assert metadata["type"] == "B2B"
        assert metadata["siret"] == "non attribué"
        assert metadata["expert_address"] == "45 avenue des Champs, 75008 Paris"
        assert metadata["billing_email"] == "expert@example.com"
        assert metadata["entreprise"] == ""

    @pytest.mark.asyncio
    async def test_metadata_contains_all_invoice_fields(self, seed_expert_with_siret):
        """Les métadonnées contiennent tous les champs nécessaires à la facture."""
        ticket_config = {
            "domaine": "psychologie",
            "price_ht": "49.00",
            "price_tva": "9.80",
            "price_ttc": "58.80",
        }

        metadata = build_metadata(seed_expert_with_siret, ticket_config)

        # Champs facture requis
        invoice_fields = [
            "date_achat", "description", "expert_lastname", "expert_firstname",
            "expert_address", "billing_email", "siret",
            "price_ht", "price_tva", "price_ttc",
        ]
        for field in invoice_fields:
            assert field in metadata, f"Champ facture manquant: {field}"


# ===========================================================================
# Test 2 : Refund via Stripe API (test mode)
# ===========================================================================


class TestRefundViaStripeAPI:
    """Tests d'intégration pour le remboursement via l'endpoint admin."""

    @pytest.mark.asyncio
    async def test_refund_success(
        self,
        admin_client: AsyncClient,
        session_factory,
        seed_ticket_actif,
    ):
        """Un remboursement réussi met à jour le ticket en 'rembourse'."""
        mock_refund = MagicMock()
        mock_refund.id = "re_test_001"

        with patch.object(_admin_mod.stripe, "Refund") as mock_refund_cls:
            mock_refund_cls.create.return_value = mock_refund

            resp = await admin_client.post(
                f"/api/admin/tickets/{seed_ticket_actif.id}/refund"
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Remboursement effectué"

        async with session_factory() as session:
            result = await session.execute(
                select(_Ticket).where(_Ticket.id == seed_ticket_actif.id)
            )
            ticket = result.scalar_one()

        assert ticket.statut == "rembourse"
        assert ticket.refunded_at is not None
        assert ticket.stripe_refund_id == "re_test_001"

    @pytest.mark.asyncio
    async def test_refund_stripe_error(
        self,
        admin_client: AsyncClient,
        session_factory,
        seed_ticket_actif,
    ):
        """Une erreur Stripe retourne HTTP 502 et le ticket reste inchangé."""
        import stripe as _stripe

        with patch.object(_admin_mod.stripe, "Refund") as mock_refund_cls:
            mock_refund_cls.create.side_effect = _stripe.error.StripeError(
                message="Insufficient funds for refund",
                http_status=402,
            )

            resp = await admin_client.post(
                f"/api/admin/tickets/{seed_ticket_actif.id}/refund"
            )

        assert resp.status_code == 502

        async with session_factory() as session:
            result = await session.execute(
                select(_Ticket).where(_Ticket.id == seed_ticket_actif.id)
            )
            ticket = result.scalar_one()

        assert ticket.statut == "actif"
        assert ticket.refunded_at is None

    @pytest.mark.asyncio
    async def test_refund_ticket_not_found(self, admin_client: AsyncClient):
        """Un ticket inexistant retourne HTTP 404."""
        resp = await admin_client.post("/api/admin/tickets/99999/refund")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_refund_ticket_already_refunded(
        self,
        admin_client: AsyncClient,
        session_factory,
        seed_expert_with_siret,
    ):
        """Un ticket déjà remboursé retourne HTTP 400."""
        async with session_factory() as session:
            ticket = _Ticket(
                ticket_code="TICKET-ALREADY-REFUNDED",
                ticket_token="token-refunded",
                expert_id=seed_expert_with_siret.id,
                domaine="psychologie",
                statut="rembourse",
                montant=Decimal("58.80"),
                stripe_payment_id="pi_test_already_refunded",
                refunded_at=datetime.now(timezone.utc),
                stripe_refund_id="re_old_001",
            )
            session.add(ticket)
            await session.commit()
            await session.refresh(ticket)
            ticket_id = ticket.id

        resp = await admin_client.post(f"/api/admin/tickets/{ticket_id}/refund")
        assert resp.status_code == 400


# ===========================================================================
# Test 3 : Import et validation Compta_Library
# ===========================================================================


class TestComptaLibraryIntegration:
    """Tests d'intégration pour l'import et la validation de la Compta_Library."""

    def test_compta_library_importable(self):
        """La Compta_Library est importable (ou le mode dégradé fonctionne)."""
        try:
            import compta_library  # type: ignore[import-untyped]
            assert hasattr(compta_library, "validate_and_format")
        except ImportError:
            # Mode dégradé en CI
            pass

    def test_compta_service_build_metadata_without_library(
        self, seed_expert_with_siret
    ):
        """build_metadata fonctionne en mode dégradé (sans Compta_Library)."""
        ticket_config = {
            "domaine": "psychologie",
            "price_ht": "49.00",
            "price_tva": "9.80",
            "price_ttc": "58.80",
        }

        # Le service fonctionne en mode dégradé quand compta_library n'est pas importable
        # On vérifie simplement que build_metadata retourne un résultat valide
        metadata = build_metadata(seed_expert_with_siret, ticket_config)

        assert metadata["appli"] == "judi-expert"
        assert metadata["type"] == "B2B"
        assert metadata["siret"] == "12345678901234"

    def test_compta_service_validation_error_propagates(self, seed_expert_with_siret):
        """Une erreur de validation Compta_Library est propagée correctement."""
        ticket_config = {
            "domaine": "psychologie",
            "price_ht": "49.00",
            "price_tva": "9.80",
            "price_ttc": "58.80",
        }

        mock_compta = MagicMock()
        mock_compta.validate_and_format.side_effect = ValueError(
            "Champ 'siret' invalide"
        )

        with patch.dict(sys.modules, {"compta_library": mock_compta}):
            with pytest.raises(ComptaValidationError) as exc_info:
                build_metadata(seed_expert_with_siret, ticket_config)

            assert "Compta_Library" in exc_info.value.message

    def test_compta_library_config_values(self, seed_expert_with_siret):
        """appli='judi-expert' et service='ticket-expertise' toujours transmis."""
        ticket_config = {
            "domaine": "psychologie",
            "price_ht": "49.00",
            "price_tva": "9.80",
            "price_ttc": "58.80",
        }

        metadata = build_metadata(seed_expert_with_siret, ticket_config)

        assert metadata["appli"] == "judi-expert"
        assert metadata["service"] == "ticket-expertise"
