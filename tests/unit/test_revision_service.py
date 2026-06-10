"""Tests unitaires pour le RevisionService (révision linguistique PRE → PREF)."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "local-site" / "web" / "backend")
)

from services.llm_service import LLMTimeoutError
from services.revision_service import RevisionService


class TestRevise:
    """Vérifie revise() avec LLM mocké."""

    @pytest.mark.asyncio
    async def test_revise_returns_corrected_text(self):
        service = RevisionService()
        with patch("services.llm_service.LLMService") as mock_cls:
            mock_llm = AsyncMock()
            mock_llm.reviser_texte = AsyncMock(return_value="Texte corrigé par le LLM.")
            mock_cls.return_value = mock_llm

            result = await service.revise("Un paragraphe à corriger.")

        assert result.corrected_text == "Texte corrigé par le LLM."
        mock_llm.reviser_texte.assert_called_once()

    @pytest.mark.asyncio
    async def test_revise_preserves_verbatim(self):
        service = RevisionService()
        original = 'Le patient dit "je souffre" depuis longtemps.'

        with patch("services.llm_service.LLMService") as mock_cls:
            mock_llm = AsyncMock()
            mock_llm.reviser_texte = AsyncMock(
                return_value='Le patient déclare __VERBATIM_001__ depuis longtemps.'
            )
            mock_cls.return_value = mock_llm

            result = await service.revise(original)

        assert '"je souffre"' in result.corrected_text
        assert result.verbatim_count == 1

    @pytest.mark.asyncio
    async def test_revise_llm_error_returns_original(self):
        service = RevisionService()
        original = "Texte original inchangé."

        with patch("services.llm_service.LLMService") as mock_cls:
            mock_llm = AsyncMock()
            mock_llm.reviser_texte = AsyncMock(side_effect=LLMTimeoutError("timeout"))
            mock_cls.return_value = mock_llm

            result = await service.revise(original)

        assert result.corrected_text == original
        assert result.corrections == []
