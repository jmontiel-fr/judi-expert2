"""Tests unitaires pour les services d'intégration comptable.

Couvre :
- compta_service.build_metadata() : tous les experts sont B2B
- subscription_service.process_payment_failures() : pas d'échec, déjà bloqué
- Endpoint refund admin : erreur Stripe mockée, ticket déjà remboursé

Exigences validées : 1.1, 1.2, 1.3, 4.3, 4.4, 5.2, 5.3
"""

import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Module isolation: load Site Central backend without polluting sys.modules
# ---------------------------------------------------------------------------
_central_backend = str(
    Path(__file__).resolve().parents[2] / "central-site" / "web" / "backend"
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
from models.subscription import Subscription as _Subscription  # noqa: E402
from models.subscription_log import SubscriptionLog as _SubscriptionLog  # noqa: E402
from database import get_db as _get_db  # noqa: E402
from main import app as _app  # noqa: E402
from services.compta_service import (  # noqa: E402
    build_metadata,
    APPLI,
    SERVICE,
)

import routers.admin as _admin_mod  # noqa: E402
import services.subscription_service as _sub_service_mod  # noqa: E402

# Cache central modules, then restore originals
_central_cache = {}
for prefix in _modules_to_isolate:
    for k in list(sys.modules):
        if k == prefix or k.startswith(prefix + "."):
            _central_cache[k] = sys.modules.pop(k)

sys.modules.update(_saved_modules)
sys.path[:] = _saved_path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_ADMIN_EMAIL = "admin@judi-expert.fr"


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
async def client(session_factory):
    """AsyncClient wired to the FastAPI app with an in-memory DB."""

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    _app.dependency_overrides[_get_db] = _override_get_db
    transport = ASGITransport(app=_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    _app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_expert_with_siret() -> _Expert:
    """Crée un Expert avec SIRET renseigné."""
    return _Expert(
        id=1,
        cognito_sub="sub-001",
        email="expert@example.com",
        nom="Durand",
        prenom="Marie",
        adresse="10 avenue des Champs, 75008 Paris",
        ville="Paris",
        code_postal="75008",
        telephone="0612345678",
        domaine="psychologie",
        accept_newsletter=False,
        is_deleted=False,
        entreprise="Cabinet Durand",
        company_address="15 rue de la Société, 75009 Paris",
        billing_email="facturation@cabinet-durand.fr",
        siret="12345678901234",
    )


def _make_expert_without_siret() -> _Expert:
    """Crée un Expert sans SIRET (sera "non attribué")."""
    return _Expert(
        id=2,
        cognito_sub="sub-002",
        email="expert2@example.com",
        nom="Martin",
        prenom="Pierre",
        adresse="5 rue du Particulier, 69001 Lyon",
        ville="Lyon",
        code_postal="69001",
        telephone="0698765432",
        domaine="psychiatrie",
        accept_newsletter=True,
        is_deleted=False,
        entreprise=None,
        company_address=None,
        billing_email=None,
        siret=None,
    )


def _make_admin_expert() -> _Expert:
    """Crée un Expert administrateur."""
    return _Expert(
        id=10,
        cognito_sub="admin-sub-001",
        email=_ADMIN_EMAIL,
        nom="Admin",
        prenom="Super",
        adresse="1 rue Admin, 75001 Paris",
        ville="Paris",
        code_postal="75001",
        telephone="0100000000",
        domaine="psychologie",
        accept_newsletter=False,
        is_deleted=False,
    )


# ===========================================================================
# Tests : compta_service.build_metadata() — tous les experts sont B2B
# ===========================================================================


class TestBuildMetadataWithSiret:
    """Tests pour build_metadata() avec un expert ayant un SIRET."""

    def test_contains_common_fields(self):
        """Les métadonnées contiennent les champs communs obligatoires."""
        expert = _make_expert_with_siret()
        config = {"domaine": "psychologie", "price_ht": "49.00", "price_tva": "9.80", "price_ttc": "58.80"}

        metadata = build_metadata(expert, config)

        assert metadata["appli"] == APPLI
        assert metadata["service"] == SERVICE
        assert metadata["type"] == "B2B"
        assert metadata["domaine"] == "psychologie"

    def test_contains_expert_info(self):
        """Les métadonnées contiennent les informations de l'expert."""
        expert = _make_expert_with_siret()
        config = {"domaine": "psychologie", "price_ht": "49.00", "price_tva": "9.80", "price_ttc": "58.80"}

        metadata = build_metadata(expert, config)

        assert metadata["expert_lastname"] == "Durand"
        assert metadata["expert_firstname"] == "Marie"
        assert metadata["expert_email"] == "expert@example.com"
        assert metadata["entreprise"] == "Cabinet Durand"
        assert metadata["expert_address"] == "15 rue de la Société, 75009 Paris"
        assert metadata["billing_email"] == "facturation@cabinet-durand.fr"
        assert metadata["siret"] == "12345678901234"

    def test_contains_purchase_info(self):
        """Les métadonnées contiennent les informations d'achat."""
        expert = _make_expert_with_siret()
        config = {
            "domaine": "psychologie",
            "price_ht": "49.00",
            "price_tva": "9.80",
            "price_ttc": "58.80",
            "service_type": "ticket-expertise",
            "abonnement": "non",
            "recurrence": "ponctuel",
        }

        metadata = build_metadata(expert, config)

        assert metadata["price_ht"] == "49.00"
        assert metadata["price_tva"] == "9.80"
        assert metadata["price_ttc"] == "58.80"
        assert metadata["service_type"] == "ticket-expertise"
        assert metadata["abonnement"] == "non"
        assert metadata["recurrence"] == "ponctuel"
        assert "date_achat" in metadata
        assert metadata["description"] == "judi-expert - ticket-expertise"

    def test_uses_config_domaine_over_expert(self):
        """Le domaine du ticket_config prime sur celui de l'expert."""
        expert = _make_expert_with_siret()
        config = {"domaine": "comptabilite", "price_ht": "59.00", "price_tva": "11.80", "price_ttc": "70.80"}

        metadata = build_metadata(expert, config)

        assert metadata["domaine"] == "comptabilite"


class TestBuildMetadataWithoutSiret:
    """Tests pour build_metadata() avec un expert sans SIRET."""

    def test_siret_non_attribue(self):
        """Sans SIRET, la valeur est 'non attribué'."""
        expert = _make_expert_without_siret()
        config = {"domaine": "psychiatrie", "price_ht": "49.00", "price_tva": "9.80", "price_ttc": "58.80"}

        metadata = build_metadata(expert, config)

        assert metadata["siret"] == "non attribué"

    def test_fallback_address_to_expert_adresse(self):
        """Sans company_address, l'adresse personnelle est utilisée."""
        expert = _make_expert_without_siret()
        config = {"domaine": "psychiatrie", "price_ht": "49.00", "price_tva": "9.80", "price_ttc": "58.80"}

        metadata = build_metadata(expert, config)

        assert metadata["expert_address"] == "5 rue du Particulier, 69001 Lyon"

    def test_fallback_billing_email_to_expert_email(self):
        """Sans billing_email, l'email principal est utilisé."""
        expert = _make_expert_without_siret()
        config = {"domaine": "psychiatrie", "price_ht": "49.00", "price_tva": "9.80", "price_ttc": "58.80"}

        metadata = build_metadata(expert, config)

        assert metadata["billing_email"] == "expert2@example.com"

    def test_type_always_b2b(self):
        """Le type est toujours B2B, même sans SIRET."""
        expert = _make_expert_without_siret()
        config = {"domaine": "psychiatrie", "price_ht": "49.00", "price_tva": "9.80", "price_ttc": "58.80"}

        metadata = build_metadata(expert, config)

        assert metadata["type"] == "B2B"

    def test_entreprise_empty_when_not_set(self):
        """Sans entreprise, le champ est une chaîne vide."""
        expert = _make_expert_without_siret()
        config = {"domaine": "psychiatrie", "price_ht": "49.00", "price_tva": "9.80", "price_ttc": "58.80"}

        metadata = build_metadata(expert, config)

        assert metadata["entreprise"] == ""


# ===========================================================================
# Tests : subscription_service.process_payment_failures()
# ===========================================================================


class TestProcessPaymentFailuresNoFailures:
    """Tests pour process_payment_failures() quand il n'y a pas d'échec."""

    @pytest.mark.asyncio
    async def test_no_failed_subscriptions_returns_zero_counters(
        self, session_factory
    ):
        """Sans abonnement en échec, les compteurs sont tous à zéro."""
        async with session_factory() as session:
            expert = _make_expert_without_siret()
            session.add(expert)
            await session.flush()

            sub = _Subscription(
                expert_id=expert.id,
                stripe_subscription_id="sub_active_001",
                status="active",
                current_period_end=datetime(2025, 2, 28, tzinfo=timezone.utc),
                payment_failed_at=None,
            )
            session.add(sub)
            await session.commit()

        async with session_factory() as session:
            with patch.object(
                _sub_service_mod, "_send_relance_email", return_value=None
            ), patch.object(
                _sub_service_mod, "_send_suspension_email", return_value=None
            ):
                result = await _sub_service_mod.process_payment_failures(session)

        assert result["processed"] == 0
        assert result["emails_sent"] == 0
        assert result["blocked"] == 0

    @pytest.mark.asyncio
    async def test_no_subscriptions_at_all(self, session_factory):
        """Sans aucun abonnement en base, les compteurs sont à zéro."""
        async with session_factory() as session:
            with patch.object(
                _sub_service_mod, "_send_relance_email", return_value=None
            ), patch.object(
                _sub_service_mod, "_send_suspension_email", return_value=None
            ):
                result = await _sub_service_mod.process_payment_failures(session)

        assert result["processed"] == 0
        assert result["emails_sent"] == 0
        assert result["blocked"] == 0


class TestProcessPaymentFailuresAlreadyBlocked:
    """Tests pour process_payment_failures() avec abonnement déjà bloqué."""

    @pytest.mark.asyncio
    async def test_already_blocked_subscription_is_not_processed(
        self, session_factory
    ):
        """Un abonnement déjà bloqué n'est pas retraité par le cron."""
        now = datetime.now(timezone.utc)

        async with session_factory() as session:
            expert = _make_expert_without_siret()
            session.add(expert)
            await session.flush()

            sub = _Subscription(
                expert_id=expert.id,
                stripe_subscription_id="sub_blocked_001",
                status="blocked",
                current_period_end=datetime(2025, 2, 28, tzinfo=timezone.utc),
                payment_failed_at=now - timedelta(days=10),
                first_rejection_notified_at=now - timedelta(days=8),
                blocked_at=now - timedelta(days=3),
            )
            session.add(sub)
            await session.commit()

        async with session_factory() as session:
            with patch.object(
                _sub_service_mod, "_send_relance_email", return_value=None
            ), patch.object(
                _sub_service_mod, "_send_suspension_email", return_value=None
            ):
                result = await _sub_service_mod.process_payment_failures(session)

        assert result["processed"] == 0
        assert result["emails_sent"] == 0
        assert result["blocked"] == 0

    @pytest.mark.asyncio
    async def test_already_blocked_no_new_logs_created(self, session_factory):
        """Un abonnement déjà bloqué ne génère pas de nouveaux logs."""
        now = datetime.now(timezone.utc)

        async with session_factory() as session:
            expert = _make_expert_without_siret()
            session.add(expert)
            await session.flush()

            sub = _Subscription(
                expert_id=expert.id,
                stripe_subscription_id="sub_blocked_002",
                status="blocked",
                current_period_end=datetime(2025, 2, 28, tzinfo=timezone.utc),
                payment_failed_at=now - timedelta(days=10),
                first_rejection_notified_at=now - timedelta(days=8),
                blocked_at=now - timedelta(days=3),
            )
            session.add(sub)
            await session.commit()

        async with session_factory() as session:
            with patch.object(
                _sub_service_mod, "_send_relance_email", return_value=None
            ), patch.object(
                _sub_service_mod, "_send_suspension_email", return_value=None
            ):
                await _sub_service_mod.process_payment_failures(session)

        async with session_factory() as session:
            result = await session.execute(select(_SubscriptionLog))
            logs = result.scalars().all()
            assert len(logs) == 0


# ===========================================================================
# Tests : Endpoint refund admin
# ===========================================================================


class TestRefundEndpointStripeError:
    """Tests pour l'endpoint refund quand Stripe renvoie une erreur."""

    @pytest.mark.asyncio
    async def test_stripe_error_returns_502_with_description(
        self, client: AsyncClient, session_factory
    ):
        """Une erreur Stripe retourne HTTP 502 avec la description de l'erreur."""
        import stripe as _stripe

        async with session_factory() as session:
            admin = _make_admin_expert()
            session.add(admin)
            await session.flush()

            ticket = _Ticket(
                id=100,
                ticket_code="TK-STRIPE-ERR",
                expert_id=admin.id,
                domaine="psychologie",
                statut="actif",
                montant=Decimal("58.80"),
                stripe_payment_id="pi_stripe_error_test",
                created_at=datetime(2025, 1, 15, tzinfo=timezone.utc),
            )
            session.add(ticket)
            await session.commit()

        async def _override_admin():
            return admin

        _app.dependency_overrides[_admin_mod.get_admin_expert] = _override_admin
        try:
            mock_error = _stripe.error.StripeError(
                "Votre carte a été refusée"
            )
            with patch.object(
                _stripe.Refund, "create", side_effect=mock_error
            ):
                resp = await client.post("/api/admin/tickets/100/refund")
        finally:
            _app.dependency_overrides.pop(_admin_mod.get_admin_expert, None)

        assert resp.status_code == 502
        data = resp.json()
        assert "stripe" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_stripe_error_ticket_status_unchanged(
        self, client: AsyncClient, session_factory
    ):
        """Après une erreur Stripe, le statut du ticket reste 'actif'."""
        import stripe as _stripe

        async with session_factory() as session:
            admin = _make_admin_expert()
            session.add(admin)
            await session.flush()

            ticket = _Ticket(
                id=101,
                ticket_code="TK-STRIPE-ERR2",
                expert_id=admin.id,
                domaine="psychologie",
                statut="actif",
                montant=Decimal("58.80"),
                stripe_payment_id="pi_stripe_error_test2",
                created_at=datetime(2025, 1, 15, tzinfo=timezone.utc),
            )
            session.add(ticket)
            await session.commit()

        async def _override_admin():
            return admin

        _app.dependency_overrides[_admin_mod.get_admin_expert] = _override_admin
        try:
            mock_error = _stripe.error.StripeError("Insufficient funds")
            with patch.object(
                _stripe.Refund, "create", side_effect=mock_error
            ):
                await client.post("/api/admin/tickets/101/refund")
        finally:
            _app.dependency_overrides.pop(_admin_mod.get_admin_expert, None)

        async with session_factory() as session:
            result = await session.execute(
                select(_Ticket).where(_Ticket.id == 101)
            )
            ticket = result.scalar_one()
            assert ticket.statut == "actif"
            assert ticket.refunded_at is None


class TestRefundEndpointAlreadyRefunded:
    """Tests pour l'endpoint refund quand le ticket est déjà remboursé."""

    @pytest.mark.asyncio
    async def test_already_refunded_ticket_returns_400(
        self, client: AsyncClient, session_factory
    ):
        """Un ticket déjà remboursé (statut 'rembourse') retourne HTTP 400."""
        async with session_factory() as session:
            admin = _make_admin_expert()
            session.add(admin)
            await session.flush()

            ticket = _Ticket(
                id=200,
                ticket_code="TK-REFUNDED-001",
                expert_id=admin.id,
                domaine="psychologie",
                statut="rembourse",
                montant=Decimal("58.80"),
                stripe_payment_id="pi_already_refunded",
                created_at=datetime(2025, 1, 10, tzinfo=timezone.utc),
                refunded_at=datetime(2025, 1, 12, tzinfo=timezone.utc),
                stripe_refund_id="re_existing_refund",
            )
            session.add(ticket)
            await session.commit()

        async def _override_admin():
            return admin

        _app.dependency_overrides[_admin_mod.get_admin_expert] = _override_admin
        try:
            resp = await client.post("/api/admin/tickets/200/refund")
        finally:
            _app.dependency_overrides.pop(_admin_mod.get_admin_expert, None)

        assert resp.status_code == 400
        data = resp.json()
        assert "rembourse" in data["detail"].lower() or "non remboursable" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_already_refunded_ticket_not_sent_to_stripe(
        self, client: AsyncClient, session_factory
    ):
        """Un ticket déjà remboursé ne déclenche pas d'appel Stripe."""
        import stripe as _stripe

        async with session_factory() as session:
            admin = _make_admin_expert()
            session.add(admin)
            await session.flush()

            ticket = _Ticket(
                id=201,
                ticket_code="TK-REFUNDED-002",
                expert_id=admin.id,
                domaine="psychologie",
                statut="rembourse",
                montant=Decimal("58.80"),
                stripe_payment_id="pi_already_refunded_2",
                created_at=datetime(2025, 1, 10, tzinfo=timezone.utc),
                refunded_at=datetime(2025, 1, 12, tzinfo=timezone.utc),
                stripe_refund_id="re_existing_refund_2",
            )
            session.add(ticket)
            await session.commit()

        async def _override_admin():
            return admin

        _app.dependency_overrides[_admin_mod.get_admin_expert] = _override_admin
        try:
            with patch.object(
                _stripe.Refund, "create"
            ) as mock_refund_create:
                await client.post("/api/admin/tickets/201/refund")
        finally:
            _app.dependency_overrides.pop(_admin_mod.get_admin_expert, None)

        mock_refund_create.assert_not_called()
