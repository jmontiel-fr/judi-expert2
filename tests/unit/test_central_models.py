"""Tests unitaires pour les modèles SQLAlchemy du Site Central."""

import sys
from decimal import Decimal
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Charger les modèles du Site Central en manipulant sys.path et sys.modules
# pour éviter les conflits avec le module 'models' de l'Application Locale.
_central_backend = str(Path(__file__).resolve().parents[2] / "site-central" / "aws" / "web" / "backend")

# Sauvegarder et nettoyer les modules 'models' existants
_saved_modules = {k: sys.modules.pop(k) for k in list(sys.modules) if k == "models" or k.startswith("models.")}
_saved_path = sys.path[:]
sys.path.insert(0, _central_backend)

import models as _central_models
import models.base
import models.expert
import models.ticket
import models.domaine
import models.corpus_version
import models.contact_message

Base = _central_models.Base
Expert = _central_models.Expert
Ticket = _central_models.Ticket
Domaine = _central_models.Domaine
CorpusVersion = _central_models.CorpusVersion
ContactMessage = _central_models.ContactMessage

# Sauvegarder les modules centraux sous des noms uniques et restaurer les originaux
_central_module_cache = {k: sys.modules.pop(k) for k in list(sys.modules) if k == "models" or k.startswith("models.")}
sys.modules.update(_saved_modules)
sys.path[:] = _saved_path


@pytest_asyncio.fixture
async def async_session():
    """Crée une session async avec une BD SQLite en mémoire."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_expert(async_session: AsyncSession):
    expert = Expert(
        cognito_sub="sub-123",
        email="test@example.com",
        nom="Dupont",
        prenom="Jean",
        adresse="1 rue de la Paix, Paris",
        domaine="psychologie",
    )
    async_session.add(expert)
    await async_session.commit()

    result = await async_session.execute(select(Expert))
    row = result.scalar_one()
    assert row.cognito_sub == "sub-123"
    assert row.email == "test@example.com"
    assert row.nom == "Dupont"
    assert row.prenom == "Jean"
    assert row.accept_newsletter is False


@pytest.mark.asyncio
async def test_expert_email_unique(async_session: AsyncSession):
    e1 = Expert(
        cognito_sub="sub-1", email="dup@example.com",
        nom="A", prenom="B", adresse="addr", domaine="psychologie",
    )
    async_session.add(e1)
    await async_session.commit()

    e2 = Expert(
        cognito_sub="sub-2", email="dup@example.com",
        nom="C", prenom="D", adresse="addr2", domaine="batiment",
    )
    async_session.add(e2)
    with pytest.raises(Exception):
        await async_session.commit()


@pytest.mark.asyncio
async def test_create_ticket_with_expert(async_session: AsyncSession):
    expert = Expert(
        cognito_sub="sub-t", email="ticket@example.com",
        nom="Martin", prenom="Luc", adresse="addr", domaine="psychologie",
    )
    async_session.add(expert)
    await async_session.flush()

    ticket = Ticket(
        ticket_code="TK-001",
        expert_id=expert.id,
        domaine="psychologie",
        montant=Decimal("49.99"),
        stripe_payment_id="pi_abc123",
    )
    async_session.add(ticket)
    await async_session.commit()

    result = await async_session.execute(select(Ticket))
    row = result.scalar_one()
    assert row.ticket_code == "TK-001"
    assert row.statut == "actif"
    assert row.montant == Decimal("49.99")
    assert row.used_at is None


@pytest.mark.asyncio
async def test_ticket_code_unique(async_session: AsyncSession):
    expert = Expert(
        cognito_sub="sub-u", email="uniq@example.com",
        nom="A", prenom="B", adresse="addr", domaine="psychologie",
    )
    async_session.add(expert)
    await async_session.flush()

    t1 = Ticket(
        ticket_code="SAME-CODE", expert_id=expert.id,
        domaine="psychologie", montant=Decimal("10.00"), stripe_payment_id="pi_1",
    )
    async_session.add(t1)
    await async_session.commit()

    t2 = Ticket(
        ticket_code="SAME-CODE", expert_id=expert.id,
        domaine="psychologie", montant=Decimal("10.00"), stripe_payment_id="pi_2",
    )
    async_session.add(t2)
    with pytest.raises(Exception):
        await async_session.commit()


@pytest.mark.asyncio
async def test_create_domaine_with_corpus_versions(async_session: AsyncSession):
    domaine = Domaine(nom="psychologie", repertoire="corpus/psychologie", actif=True)
    async_session.add(domaine)
    await async_session.flush()

    cv = CorpusVersion(
        domaine_id=domaine.id,
        version="1.0.0",
        description="Version initiale du corpus psychologie",
        ecr_image_uri="123456.dkr.ecr.eu-west-1.amazonaws.com/judi-rag-psychologie:1.0.0",
    )
    async_session.add(cv)
    await async_session.commit()

    result = await async_session.execute(select(CorpusVersion))
    row = result.scalar_one()
    assert row.version == "1.0.0"
    assert row.domaine_id == domaine.id


@pytest.mark.asyncio
async def test_domaine_nom_unique(async_session: AsyncSession):
    d1 = Domaine(nom="psychologie", repertoire="corpus/psychologie", actif=True)
    async_session.add(d1)
    await async_session.commit()

    d2 = Domaine(nom="psychologie", repertoire="corpus/psychologie2", actif=False)
    async_session.add(d2)
    with pytest.raises(Exception):
        await async_session.commit()


@pytest.mark.asyncio
async def test_create_contact_message_with_expert(async_session: AsyncSession):
    expert = Expert(
        cognito_sub="sub-c", email="contact@example.com",
        nom="Durand", prenom="Marie", adresse="addr", domaine="psychologie",
    )
    async_session.add(expert)
    await async_session.flush()

    msg = ContactMessage(
        expert_id=expert.id,
        domaine="psychologie",
        objet="Problème",
        message="J'ai un problème avec mon ticket.",
    )
    async_session.add(msg)
    await async_session.commit()

    result = await async_session.execute(select(ContactMessage))
    row = result.scalar_one()
    assert row.objet == "Problème"
    assert row.expert_id == expert.id


@pytest.mark.asyncio
async def test_create_contact_message_without_expert(async_session: AsyncSession):
    msg = ContactMessage(
        expert_id=None,
        domaine="général",
        objet="Autre",
        message="Question générale.",
    )
    async_session.add(msg)
    await async_session.commit()

    result = await async_session.execute(select(ContactMessage))
    row = result.scalar_one()
    assert row.expert_id is None
    assert row.domaine == "général"
