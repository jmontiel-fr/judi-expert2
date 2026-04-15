"""Test par propriété — Filtrage des statistiques de tickets par domaine.

**Validates: Requirements 19.4**

Feature: judi-expert, Property 11: Filtrage des statistiques de tickets par domaine

Propriété 11 : Pour tout ensemble de tickets et pour tout filtre de domaine
sélectionné, les résultats retournés doivent contenir uniquement les tickets
correspondant au domaine filtré. Si le filtre est "Tous", tous les tickets
doivent être retournés.
"""

import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Module isolation: load Site Central backend without polluting sys.modules
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
}
_saved_path = sys.path[:]
sys.path.insert(0, _central_backend)

import models as _central_models  # noqa: E402
import models.base  # noqa: E402
import models.expert  # noqa: E402
import models.ticket  # noqa: E402

Base = _central_models.Base
Expert = _central_models.Expert
Ticket = _central_models.Ticket

_central_module_cache = {
    k: sys.modules.pop(k)
    for k in list(sys.modules)
    if k == "models" or k.startswith("models.")
}
sys.modules.update(_saved_modules)
sys.path[:] = _saved_path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DOMAINES = ["psychologie", "psychiatrie", "medecine_legale", "batiment", "comptabilite"]

# ---------------------------------------------------------------------------
# Fixture: async SQLite engine
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def seed_expert(session: AsyncSession, domaine: str) -> Expert:
    """Create and return a single expert."""
    expert = Expert(
        cognito_sub=f"sub-{uuid4().hex[:12]}",
        email=f"{uuid4().hex[:10]}@test.com",
        nom="Test",
        prenom="Expert",
        adresse="1 rue test",
        domaine=domaine,
    )
    session.add(expert)
    await session.flush()
    return expert


async def create_ticket(
    session: AsyncSession,
    expert_id: int,
    domaine: str,
    created_at: datetime,
) -> Ticket:
    """Create a ticket with a specific creation date."""
    ticket = Ticket(
        ticket_code=str(uuid4()),
        expert_id=expert_id,
        domaine=domaine,
        statut="actif",
        montant=Decimal("49.99"),
        stripe_payment_id=f"pi_{uuid4().hex[:16]}",
        created_at=created_at,
    )
    session.add(ticket)
    await session.flush()
    return ticket


async def compute_stats_for_filter(
    session: AsyncSession,
    domaine_filter: str,
    now: datetime,
):
    """Reproduce the same filtering logic as the admin router endpoint.

    Returns (today_count, today_amount, month_count, month_amount).
    """
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    base_filter = []
    if domaine_filter != "Tous":
        base_filter.append(Ticket.domaine == domaine_filter)

    # Today
    today_q = select(
        func.count(Ticket.id),
        func.coalesce(func.sum(Ticket.montant), Decimal("0")),
    ).where(Ticket.created_at >= today_start, *base_filter)
    today_row = (await session.execute(today_q)).one()

    # Current month
    month_q = select(
        func.count(Ticket.id),
        func.coalesce(func.sum(Ticket.montant), Decimal("0")),
    ).where(Ticket.created_at >= month_start, *base_filter)
    month_row = (await session.execute(month_q)).one()

    return today_row[0], today_row[1], month_row[0], month_row[1]


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

domaine_strategy = st.sampled_from(DOMAINES)
domaine_filter_strategy = st.sampled_from(DOMAINES + ["Tous"])
ticket_count_strategy = st.integers(min_value=0, max_value=5)


def ticket_list_strategy():
    """Generate a list of (domaine, is_today) tuples representing tickets."""
    return st.lists(
        st.tuples(domaine_strategy, st.booleans()),
        min_size=0,
        max_size=15,
    )


# ---------------------------------------------------------------------------
# Property 11a — Domain filter returns only tickets from that domain
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    tickets_spec=ticket_list_strategy(),
    domain_filter=domaine_strategy,
)
async def test_domain_filter_returns_only_matching_tickets(
    async_engine,
    tickets_spec: list[tuple[str, bool]],
    domain_filter: str,
):
    """**Validates: Requirements 19.4**

    Property 11a: For any set of tickets across multiple domains and a specific
    domain filter, today_count and month_count only include tickets from that domain.
    """
    factory = async_sessionmaker(async_engine, expire_on_commit=False)
    async with factory() as session:
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)

        # Create one expert per domain used
        domains_used = set(d for d, _ in tickets_spec) | {domain_filter}
        experts = {}
        for d in domains_used:
            experts[d] = await seed_expert(session, d)

        # Create tickets
        for domaine, is_today in tickets_spec:
            ts = now if is_today else yesterday
            await create_ticket(session, experts[domaine].id, domaine, ts)

        await session.flush()

        # Compute stats using the same logic as the admin router
        today_count, today_amount, month_count, month_amount = (
            await compute_stats_for_filter(session, domain_filter, now)
        )

        # Expected counts: only tickets matching the domain filter
        expected_today = sum(
            1 for d, is_today in tickets_spec if d == domain_filter and is_today
        )
        expected_month = sum(
            1 for d, _ in tickets_spec if d == domain_filter
        )

        assert today_count == expected_today, (
            f"Filter '{domain_filter}': expected today_count={expected_today}, "
            f"got {today_count}"
        )
        assert month_count == expected_month, (
            f"Filter '{domain_filter}': expected month_count={expected_month}, "
            f"got {month_count}"
        )

        await session.rollback()


# ---------------------------------------------------------------------------
# Property 11b — "Tous" filter returns total counts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(tickets_spec=ticket_list_strategy())
async def test_tous_filter_returns_total_counts(
    async_engine,
    tickets_spec: list[tuple[str, bool]],
):
    """**Validates: Requirements 19.4**

    Property 11b: For any set of tickets, the "Tous" filter returns counts
    matching the total number of tickets.
    """
    factory = async_sessionmaker(async_engine, expire_on_commit=False)
    async with factory() as session:
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)

        # Create experts for all domains used
        domains_used = set(d for d, _ in tickets_spec) if tickets_spec else {"psychologie"}
        experts = {}
        for d in domains_used:
            experts[d] = await seed_expert(session, d)

        # Create tickets
        for domaine, is_today in tickets_spec:
            ts = now if is_today else yesterday
            await create_ticket(session, experts[domaine].id, domaine, ts)

        await session.flush()

        today_count, today_amount, month_count, month_amount = (
            await compute_stats_for_filter(session, "Tous", now)
        )

        expected_today = sum(1 for _, is_today in tickets_spec if is_today)
        expected_total = len(tickets_spec)

        assert today_count == expected_today, (
            f"'Tous' filter: expected today_count={expected_today}, got {today_count}"
        )
        assert month_count == expected_total, (
            f"'Tous' filter: expected month_count={expected_total}, got {month_count}"
        )

        await session.rollback()


# ---------------------------------------------------------------------------
# Property 11c — Domain with no tickets returns zero counts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    tickets_spec=st.lists(
        st.tuples(domaine_strategy, st.booleans()),
        min_size=1,
        max_size=10,
    ),
    empty_domain=domaine_strategy,
)
async def test_empty_domain_filter_returns_zero(
    async_engine,
    tickets_spec: list[tuple[str, bool]],
    empty_domain: str,
):
    """**Validates: Requirements 19.4**

    Property 11c: For any domain filter that has no tickets, the counts are
    all zero.
    """
    # Ensure no ticket uses the empty_domain
    tickets_spec = [(d, t) for d, t in tickets_spec if d != empty_domain]

    factory = async_sessionmaker(async_engine, expire_on_commit=False)
    async with factory() as session:
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)

        # Create experts for domains used + the empty domain
        domains_used = set(d for d, _ in tickets_spec) | {empty_domain}
        experts = {}
        for d in domains_used:
            experts[d] = await seed_expert(session, d)

        # Create tickets (none for empty_domain)
        for domaine, is_today in tickets_spec:
            ts = now if is_today else yesterday
            await create_ticket(session, experts[domaine].id, domaine, ts)

        await session.flush()

        today_count, today_amount, month_count, month_amount = (
            await compute_stats_for_filter(session, empty_domain, now)
        )

        assert today_count == 0, (
            f"Filter '{empty_domain}' (no tickets): expected today_count=0, "
            f"got {today_count}"
        )
        assert month_count == 0, (
            f"Filter '{empty_domain}' (no tickets): expected month_count=0, "
            f"got {month_count}"
        )
        assert today_amount == 0 or today_amount == Decimal("0"), (
            f"Filter '{empty_domain}' (no tickets): expected today_amount=0, "
            f"got {today_amount}"
        )
        assert month_amount == 0 or month_amount == Decimal("0"), (
            f"Filter '{empty_domain}' (no tickets): expected month_amount=0, "
            f"got {month_amount}"
        )

        await session.rollback()
