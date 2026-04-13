"""Tests unitaires pour le router ChatBot.

Valide : Exigences 11.1, 11.2, 11.3
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Backend sur le path
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[2] / "site-central" / "local" / "web" / "backend"),
)

from database import get_db
from main import app
from models import Base, LocalConfig, ChatMessage
from routers.auth import _create_access_token, get_current_user


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def client(session_factory):
    async def _override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_token():
    return _create_access_token({"sub": "local_admin", "domaine": "psychologie"})


@pytest_asyncio.fixture
async def configured_db(session_factory):
    """Seed the DB with a LocalConfig so the chatbot can read the domain."""
    async with session_factory() as session:
        config = LocalConfig(
            password_hash="fakehash",
            domaine="psychologie",
            is_configured=True,
        )
        session.add(config)
        await session.commit()


# ---------------------------------------------------------------------------
# POST /api/chatbot/message
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_message_requires_auth(client: AsyncClient):
    resp = await client.post("/api/chatbot/message", json={"message": "Bonjour"})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_send_message_no_config(client: AsyncClient, auth_token: str):
    resp = await client.post(
        "/api/chatbot/message",
        json={"message": "Bonjour"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
@patch("routers.chatbot.LLMService")
@patch("routers.chatbot.RAGService")
async def test_send_message_success(
    mock_rag_cls, mock_llm_cls,
    client: AsyncClient, auth_token: str, configured_db,
):
    mock_rag = AsyncMock()
    mock_rag.search.return_value = []
    mock_rag_cls.return_value = mock_rag

    mock_llm = AsyncMock()
    mock_llm.chatbot.return_value = "Bonjour, comment puis-je vous aider ?"
    mock_llm_cls.return_value = mock_llm

    resp = await client.post(
        "/api/chatbot/message",
        json={"message": "Bonjour"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["response"] == "Bonjour, comment puis-je vous aider ?"

    mock_llm.chatbot.assert_called_once()
    call_args = mock_llm.chatbot.call_args
    messages = call_args[0][0]
    assert messages[-1] == {"role": "user", "content": "Bonjour"}


@pytest.mark.asyncio
@patch("routers.chatbot.LLMService")
@patch("routers.chatbot.RAGService")
async def test_send_message_stores_history(
    mock_rag_cls, mock_llm_cls,
    client: AsyncClient, auth_token: str, configured_db, session_factory,
):
    mock_rag = AsyncMock()
    mock_rag.search.return_value = []
    mock_rag_cls.return_value = mock_rag

    mock_llm = AsyncMock()
    mock_llm.chatbot.return_value = "Réponse du bot"
    mock_llm_cls.return_value = mock_llm

    await client.post(
        "/api/chatbot/message",
        json={"message": "Test", "session_id": 42},
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    from sqlalchemy import select

    async with session_factory() as session:
        result = await session.execute(
            select(ChatMessage).where(ChatMessage.session_id == 42)
        )
        msgs = result.scalars().all()
        assert len(msgs) == 2
        assert msgs[0].role == "user"
        assert msgs[0].content == "Test"
        assert msgs[1].role == "assistant"
        assert msgs[1].content == "Réponse du bot"


@pytest.mark.asyncio
@patch("routers.chatbot.LLMService")
@patch("routers.chatbot.RAGService")
async def test_send_message_llm_unavailable(
    mock_rag_cls, mock_llm_cls,
    client: AsyncClient, auth_token: str, configured_db,
):
    from services.llm_service import LLMConnectionError

    mock_rag = AsyncMock()
    mock_rag.search.return_value = []
    mock_rag_cls.return_value = mock_rag

    mock_llm = AsyncMock()
    mock_llm.chatbot.side_effect = LLMConnectionError("LLM down")
    mock_llm_cls.return_value = mock_llm

    resp = await client.post(
        "/api/chatbot/message",
        json={"message": "Bonjour"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 503
    assert "indisponible" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# GET /api/chatbot/history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_history_requires_auth(client: AsyncClient):
    resp = await client.get("/api/chatbot/history")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_history_empty(client: AsyncClient, auth_token: str):
    resp = await client.get(
        "/api/chatbot/history",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_history_returns_messages(
    client: AsyncClient, auth_token: str, session_factory,
):
    async with session_factory() as session:
        session.add(ChatMessage(session_id=1, role="user", content="Hello"))
        session.add(ChatMessage(session_id=1, role="assistant", content="Hi there"))
        session.add(ChatMessage(session_id=2, role="user", content="Other session"))
        await session.commit()

    resp = await client.get(
        "/api/chatbot/history?session_id=1",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["role"] == "user"
    assert data[0]["content"] == "Hello"
    assert data[1]["role"] == "assistant"
    assert data[1]["content"] == "Hi there"
    assert "created_at" in data[0]
