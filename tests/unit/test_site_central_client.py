"""Tests unitaires pour le client HTTP du Site Central.

Valide : Exigences 35.6, 35.7
"""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "local-site" / "web" / "backend"))

from services.site_central_client import (
    SiteCentralClient,
    SiteCentralError,
    is_within_business_hours,
    get_business_hours_message,
    _get_paris_now,
    BUSINESS_HOUR_START,
    BUSINESS_HOUR_END,
)


# ---------------------------------------------------------------------------
# Business hours tests
# ---------------------------------------------------------------------------


class TestBusinessHours:
    def test_within_business_hours_morning(self):
        """10h Paris time should be within business hours."""
        # 10h CET = 9h UTC (winter)
        mock_utc = datetime(2025, 1, 15, 9, 0, tzinfo=timezone.utc)
        with patch("services.site_central_client.datetime") as mock_dt:
            mock_dt.now.return_value = mock_utc
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            # Directly test with a known Paris time
            with patch("services.site_central_client._get_paris_now") as mock_paris:
                mock_paris.return_value = datetime(2025, 1, 15, 10, 0)
                assert is_within_business_hours() is True

    def test_outside_business_hours_night(self):
        """22h Paris time should be outside business hours."""
        with patch("services.site_central_client._get_paris_now") as mock_paris:
            mock_paris.return_value = datetime(2025, 1, 15, 22, 0)
            assert is_within_business_hours() is False

    def test_outside_business_hours_early_morning(self):
        """6h Paris time should be outside business hours."""
        with patch("services.site_central_client._get_paris_now") as mock_paris:
            mock_paris.return_value = datetime(2025, 1, 15, 6, 0)
            assert is_within_business_hours() is False

    def test_boundary_start(self):
        """8h Paris time should be within business hours."""
        with patch("services.site_central_client._get_paris_now") as mock_paris:
            mock_paris.return_value = datetime(2025, 1, 15, 8, 0)
            assert is_within_business_hours() is True

    def test_boundary_end(self):
        """20h Paris time should be outside business hours."""
        with patch("services.site_central_client._get_paris_now") as mock_paris:
            mock_paris.return_value = datetime(2025, 1, 15, 20, 0)
            assert is_within_business_hours() is False

    def test_business_hours_message_content(self):
        msg = get_business_hours_message()
        assert "8h" in msg
        assert "20h" in msg
        assert "Paris" in msg


class TestGetParisNow:
    def test_winter_time_cet(self):
        """In January, Paris should be UTC+1 (CET)."""
        mock_utc = datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)
        with patch("services.site_central_client.datetime") as mock_dt:
            mock_dt.now.return_value = mock_utc
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = _get_paris_now()
            assert result.hour == 13  # UTC+1

    def test_summer_time_cest(self):
        """In July, Paris should be UTC+2 (CEST)."""
        mock_utc = datetime(2025, 7, 15, 12, 0, tzinfo=timezone.utc)
        with patch("services.site_central_client.datetime") as mock_dt:
            mock_dt.now.return_value = mock_utc
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = _get_paris_now()
            assert result.hour == 14  # UTC+2


# ---------------------------------------------------------------------------
# SiteCentralClient tests
# ---------------------------------------------------------------------------


class TestSiteCentralClient:
    @pytest.mark.asyncio
    async def test_post_success(self):
        """Successful POST should return the response."""
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True}

        with patch("services.site_central_client.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            client = SiteCentralClient(base_url="http://test")
            resp = await client.post("/api/tickets/verify", json={"ticket_code": "ABC"})

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_success(self):
        """Successful GET should return the response."""
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"version": "1.0.0"}]

        with patch("services.site_central_client.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            client = SiteCentralClient(base_url="http://test")
            resp = await client.get("/api/corpus/psychologie/versions")

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_retry_on_connect_error(self):
        """Should retry on ConnectError and eventually raise SiteCentralError."""
        with patch("services.site_central_client.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("refused")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            with patch("services.site_central_client.asyncio.sleep", new_callable=AsyncMock):
                client = SiteCentralClient(base_url="http://test")
                with pytest.raises(SiteCentralError) as exc_info:
                    await client.post("/api/tickets/verify", json={"ticket_code": "X"})

        assert "connexion impossible" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self):
        """Should retry on TimeoutException and eventually raise SiteCentralError."""
        with patch("services.site_central_client.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.ReadTimeout("timeout")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            with patch("services.site_central_client.asyncio.sleep", new_callable=AsyncMock):
                client = SiteCentralClient(base_url="http://test")
                with pytest.raises(SiteCentralError) as exc_info:
                    await client.get("/api/corpus/psychologie/versions")

        assert "délai" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_retry_count(self):
        """Should retry exactly MAX_RETRIES times."""
        with patch("services.site_central_client.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("refused")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            with patch("services.site_central_client.asyncio.sleep", new_callable=AsyncMock):
                client = SiteCentralClient(base_url="http://test")
                with pytest.raises(SiteCentralError):
                    await client.post("/test", json={})

        # 3 retries = 3 calls
        assert mock_client.post.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_succeeds_on_second_attempt(self):
        """Should succeed if the second attempt works."""
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200

        with patch("services.site_central_client.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = [
                httpx.ConnectError("refused"),
                mock_resp,
            ]
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            with patch("services.site_central_client.asyncio.sleep", new_callable=AsyncMock):
                client = SiteCentralClient(base_url="http://test")
                resp = await client.post("/test", json={})

        assert resp.status_code == 200
        assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_error_message_includes_business_hours_when_outside(self):
        """Error message should mention business hours when outside 8h-20h."""
        with patch("services.site_central_client.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("refused")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            with patch("services.site_central_client.asyncio.sleep", new_callable=AsyncMock):
                with patch("services.site_central_client.is_within_business_hours", return_value=False):
                    client = SiteCentralClient(base_url="http://test")
                    with pytest.raises(SiteCentralError) as exc_info:
                        await client.post("/test", json={})

        assert "8h" in exc_info.value.message
        assert "20h" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_error_message_no_business_hours_when_within(self):
        """Error message should NOT mention business hours when within 8h-20h."""
        with patch("services.site_central_client.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("refused")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            with patch("services.site_central_client.asyncio.sleep", new_callable=AsyncMock):
                with patch("services.site_central_client.is_within_business_hours", return_value=True):
                    client = SiteCentralClient(base_url="http://test")
                    with pytest.raises(SiteCentralError) as exc_info:
                        await client.post("/test", json={})

        # Should not contain business hours message
        assert "8h à 20h" not in exc_info.value.message
