"""Tests unitaires pour le RevisionService.

Teste la construction du prompt, la séparation en paragraphes, le chunking
adaptatif, le fallback en cas de timeout LLM, la gestion des fichiers
corrompus, et la révision de texte brut (.txt/.md/copié-collé).

Valide : Exigences 4.1, 7.1, 7.4, 7.5
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Ajouter le backend au path
sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "local-site" / "web" / "backend")
)

from services.llm_service import LLMTimeoutError
from services.revision_models import DocumentParseError, ParagraphInfo
from services.revision_service import (
    CHARS_PER_TOKEN,
    CTX_USAGE_RATIO,
    PROMPT_REVISION,
    RevisionService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_para_info(index: int, text: str) -> ParagraphInfo:
    """Crée un ParagraphInfo léger pour les tests de chunking.

    Args:
        index: Index du paragraphe.
        text: Texte du paragraphe.

    Returns:
        ParagraphInfo avec les champs minimaux remplis.
    """
    return ParagraphInfo(
        index=index,
        runs=[],
        xml_element=None,
        properties=None,
        full_text=text,
    )


def _mock_llm_service() -> AsyncMock:
    """Crée un mock du LLMService avec la méthode chat en AsyncMock.

    Returns:
        Mock du LLMService.
    """
    mock = AsyncMock()
    mock.chat = AsyncMock()
    return mock


# ---------------------------------------------------------------------------
# Tests : Prompt construction
# ---------------------------------------------------------------------------


class TestPromptConstruction:
    """Vérifie que PROMPT_REVISION est utilisé comme prompt système."""

    @pytest.mark.asyncio
    async def test_prompt_revision_used_as_system_prompt(self):
        """Le PROMPT_REVISION est passé comme system_prompt au LLM."""
        mock_llm = _mock_llm_service()
        mock_llm.chat.return_value = "Texte corrigé"

        service = RevisionService(mock_llm)

        with patch(
            "services.revision_service.ActiveProfile.get_ctx_max",
            return_value=8192,
        ):
            await service.revise_text("Un paragraphe simple.")

        # Vérifier que chat a été appelé avec system_prompt=PROMPT_REVISION
        mock_llm.chat.assert_called()
        call_kwargs = mock_llm.chat.call_args
        assert call_kwargs.kwargs["system_prompt"] == PROMPT_REVISION


# ---------------------------------------------------------------------------
# Tests : Séparation en paragraphes
# ---------------------------------------------------------------------------


class TestParagraphSeparation:
    """Vérifie que _split_text_into_paragraphs sépare sur double newline."""

    def test_splits_on_double_newline(self):
        """Le texte est séparé par des doubles sauts de ligne."""
        text = "Premier paragraphe.\n\nDeuxième paragraphe.\n\nTroisième."
        result = RevisionService._split_text_into_paragraphs(text)
        assert result == [
            "Premier paragraphe.",
            "Deuxième paragraphe.",
            "Troisième.",
        ]

    def test_ignores_empty_paragraphs(self):
        """Les paragraphes vides (après strip) sont ignorés."""
        text = "Premier.\n\n\n\n\nDeuxième.\n\n   \n\nTroisième."
        result = RevisionService._split_text_into_paragraphs(text)
        assert result == ["Premier.", "Deuxième.", "Troisième."]

    def test_single_paragraph_no_split(self):
        """Un texte sans double newline reste un seul paragraphe."""
        text = "Un seul paragraphe sans saut de ligne double."
        result = RevisionService._split_text_into_paragraphs(text)
        assert result == ["Un seul paragraphe sans saut de ligne double."]

    def test_empty_text_returns_empty_list(self):
        """Un texte vide retourne une liste vide."""
        result = RevisionService._split_text_into_paragraphs("")
        assert result == []

    def test_whitespace_only_returns_empty_list(self):
        """Un texte ne contenant que des espaces retourne une liste vide."""
        result = RevisionService._split_text_into_paragraphs("   \n\n   ")
        assert result == []


# ---------------------------------------------------------------------------
# Tests : Chunking respecte les limites
# ---------------------------------------------------------------------------


class TestChunkingLimits:
    """Vérifie que _build_chunks respecte 60% de ctx_max."""

    def test_single_small_paragraph_one_chunk(self):
        """Un seul petit paragraphe produit un seul chunk."""
        service = RevisionService(_mock_llm_service())
        paragraphs = [_make_para_info(0, "Court texte.")]

        with patch(
            "services.revision_service.ActiveProfile.get_ctx_max",
            return_value=8192,
        ):
            chunks = service._build_chunks(paragraphs)

        assert len(chunks) == 1
        assert len(chunks[0]) == 1

    def test_multiple_paragraphs_fit_in_one_chunk(self):
        """Plusieurs petits paragraphes tiennent dans un seul chunk."""
        service = RevisionService(_mock_llm_service())
        # Avec ctx_max=8192, 60% = 4915 tokens, soit ~19660 chars
        paragraphs = [_make_para_info(i, f"Paragraphe {i}.") for i in range(5)]

        with patch(
            "services.revision_service.ActiveProfile.get_ctx_max",
            return_value=8192,
        ):
            chunks = service._build_chunks(paragraphs)

        assert len(chunks) == 1
        assert len(chunks[0]) == 5

    def test_large_paragraphs_split_into_multiple_chunks(self):
        """Des paragraphes volumineux sont répartis en plusieurs chunks."""
        service = RevisionService(_mock_llm_service())
        # ctx_max=8192, 60% = 4915 tokens, ~19660 chars
        # Chaque paragraphe fait ~10000 chars → ~2500 tokens
        # 2 paragraphes > 4915 tokens → doivent être dans des chunks séparés
        big_text = "A" * 10000
        paragraphs = [_make_para_info(i, big_text) for i in range(3)]

        with patch(
            "services.revision_service.ActiveProfile.get_ctx_max",
            return_value=8192,
        ):
            chunks = service._build_chunks(paragraphs)

        assert len(chunks) >= 2

    def test_chunk_token_count_respects_limit(self):
        """Chaque chunk ne dépasse pas 60% de ctx_max en tokens estimés."""
        service = RevisionService(_mock_llm_service())
        ctx_max = 8192
        max_tokens = int(ctx_max * CTX_USAGE_RATIO)

        # Créer des paragraphes de taille variée
        paragraphs = [_make_para_info(i, "Mot " * 200) for i in range(10)]

        with patch(
            "services.revision_service.ActiveProfile.get_ctx_max",
            return_value=ctx_max,
        ):
            chunks = service._build_chunks(paragraphs)

        for chunk in chunks:
            chunk_chars = sum(len(p.full_text) for p in chunk)
            chunk_tokens = chunk_chars // CHARS_PER_TOKEN
            # Un chunk peut dépasser si un seul paragraphe est trop gros
            if len(chunk) > 1:
                assert chunk_tokens <= max_tokens


# ---------------------------------------------------------------------------
# Tests : Pas de paragraphe coupé entre chunks
# ---------------------------------------------------------------------------


class TestNoParagraphSplitting:
    """Vérifie qu'un paragraphe n'est jamais coupé entre deux chunks."""

    def test_paragraph_never_split_across_chunks(self):
        """Un paragraphe apparaît dans un seul chunk, jamais partagé."""
        service = RevisionService(_mock_llm_service())
        paragraphs = [_make_para_info(i, f"Paragraphe numéro {i}. " * 50) for i in range(10)]

        with patch(
            "services.revision_service.ActiveProfile.get_ctx_max",
            return_value=8192,
        ):
            chunks = service._build_chunks(paragraphs)

        # Vérifier que chaque paragraphe apparaît exactement une fois
        all_indices = []
        for chunk in chunks:
            for para in chunk:
                all_indices.append(para.index)

        assert sorted(all_indices) == list(range(10))
        assert len(all_indices) == len(set(all_indices)), "Pas de doublon"

    def test_oversized_paragraph_gets_own_chunk(self):
        """Un paragraphe dépassant la limite forme son propre chunk."""
        service = RevisionService(_mock_llm_service())
        ctx_max = 4096
        # 60% de 4096 = 2457 tokens, soit ~9830 chars
        # Un paragraphe de 15000 chars dépasse la limite
        paragraphs = [
            _make_para_info(0, "Court."),
            _make_para_info(1, "X" * 15000),
            _make_para_info(2, "Court aussi."),
        ]

        with patch(
            "services.revision_service.ActiveProfile.get_ctx_max",
            return_value=ctx_max,
        ):
            chunks = service._build_chunks(paragraphs)

        # Le gros paragraphe doit être seul dans son chunk
        found_big = False
        for chunk in chunks:
            if any(p.index == 1 for p in chunk):
                assert len(chunk) == 1, "Le gros paragraphe doit être seul"
                found_big = True
        assert found_big


# ---------------------------------------------------------------------------
# Tests : LLM timeout → fallback
# ---------------------------------------------------------------------------


class TestLLMTimeoutFallback:
    """Vérifie que le timeout LLM retourne le texte original (fallback)."""

    @pytest.mark.asyncio
    async def test_timeout_returns_original_text(self):
        """En cas de timeout LLM, le texte original est retourné."""
        mock_llm = _mock_llm_service()
        mock_llm.chat.side_effect = LLMTimeoutError("Timeout")

        service = RevisionService(mock_llm)

        with patch(
            "services.revision_service.ActiveProfile.get_ctx_max",
            return_value=8192,
        ):
            result = await service.revise_text("Texte original à corriger.")

        # Le fallback retourne le texte original
        assert result == "Texte original à corriger."

    @pytest.mark.asyncio
    async def test_timeout_with_multiple_paragraphs_returns_all_original(self):
        """Timeout sur tous les chunks → tous les paragraphes originaux."""
        mock_llm = _mock_llm_service()
        mock_llm.chat.side_effect = LLMTimeoutError("Timeout")

        service = RevisionService(mock_llm)
        text = "Premier paragraphe.\n\nDeuxième paragraphe."

        with patch(
            "services.revision_service.ActiveProfile.get_ctx_max",
            return_value=8192,
        ):
            result = await service.revise_text(text)

        assert "Premier paragraphe." in result
        assert "Deuxième paragraphe." in result


# ---------------------------------------------------------------------------
# Tests : Fichier corrompu → erreur claire
# ---------------------------------------------------------------------------


class TestCorruptedFile:
    """Vérifie qu'un fichier corrompu lève DocumentParseError."""

    @pytest.mark.asyncio
    async def test_invalid_docx_bytes_raises_error(self):
        """Des bytes invalides en .docx lèvent DocumentParseError."""
        mock_llm = _mock_llm_service()
        service = RevisionService(mock_llm)

        with pytest.raises(DocumentParseError):
            with patch(
                "services.revision_service.ActiveProfile.get_ctx_max",
                return_value=8192,
            ):
                await service.revise_document(b"not a valid docx file", "docx")

    @pytest.mark.asyncio
    async def test_random_bytes_as_docx_raises_error(self):
        """Des bytes aléatoires en .docx lèvent DocumentParseError."""
        mock_llm = _mock_llm_service()
        service = RevisionService(mock_llm)

        import os
        random_bytes = os.urandom(1024)

        with pytest.raises(DocumentParseError):
            with patch(
                "services.revision_service.ActiveProfile.get_ctx_max",
                return_value=8192,
            ):
                await service.revise_document(random_bytes, "docx")


# ---------------------------------------------------------------------------
# Tests : Révision de texte (revise_text) avec mock LLM
# ---------------------------------------------------------------------------


class TestReviseText:
    """Vérifie revise_text avec un LLM mocké."""

    @pytest.mark.asyncio
    async def test_revise_text_returns_corrected_text(self):
        """revise_text retourne le texte corrigé par le LLM."""
        mock_llm = _mock_llm_service()
        mock_llm.chat.return_value = "Texte corrigé par le LLM."

        service = RevisionService(mock_llm)

        with patch(
            "services.revision_service.ActiveProfile.get_ctx_max",
            return_value=8192,
        ):
            result = await service.revise_text("Texte avec des fotes.")

        assert result == "Texte corrigé par le LLM."

    @pytest.mark.asyncio
    async def test_revise_text_multiple_paragraphs(self):
        """revise_text gère correctement plusieurs paragraphes."""
        mock_llm = _mock_llm_service()
        mock_llm.chat.return_value = "Premier corrigé.\n\nDeuxième corrigé."

        service = RevisionService(mock_llm)
        text = "Premier original.\n\nDeuxième original."

        with patch(
            "services.revision_service.ActiveProfile.get_ctx_max",
            return_value=8192,
        ):
            result = await service.revise_text(text)

        assert "Premier corrigé." in result
        assert "Deuxième corrigé." in result

    @pytest.mark.asyncio
    async def test_revise_empty_text_returns_original(self):
        """revise_text avec texte vide retourne le texte original."""
        mock_llm = _mock_llm_service()
        service = RevisionService(mock_llm)

        with patch(
            "services.revision_service.ActiveProfile.get_ctx_max",
            return_value=8192,
        ):
            result = await service.revise_text("")

        assert result == ""
        mock_llm.chat.assert_not_called()


# ---------------------------------------------------------------------------
# Tests : Révision de fichier .txt
# ---------------------------------------------------------------------------


class TestTxtFileRevision:
    """Vérifie que la révision d'un fichier .txt retourne un str corrigé."""

    @pytest.mark.asyncio
    async def test_txt_file_returns_corrected_string(self):
        """Un fichier .txt valide retourne un str corrigé."""
        mock_llm = _mock_llm_service()
        mock_llm.chat.return_value = "Contenu corrigé du fichier texte."

        service = RevisionService(mock_llm)
        file_bytes = "Contenu original du fichier texte.".encode("utf-8")

        with patch(
            "services.revision_service.ActiveProfile.get_ctx_max",
            return_value=8192,
        ):
            result = await service.revise_document(file_bytes, "txt")

        assert isinstance(result, str)
        assert result == "Contenu corrigé du fichier texte."


# ---------------------------------------------------------------------------
# Tests : Révision de fichier .md
# ---------------------------------------------------------------------------


class TestMdFileRevision:
    """Vérifie que la révision d'un fichier .md retourne un str corrigé."""

    @pytest.mark.asyncio
    async def test_md_file_returns_corrected_string(self):
        """Un fichier .md valide retourne un str corrigé."""
        mock_llm = _mock_llm_service()
        mock_llm.chat.return_value = "# Titre corrigé\n\nContenu corrigé."

        service = RevisionService(mock_llm)
        file_bytes = "# Titre original\n\nContenu original.".encode("utf-8")

        with patch(
            "services.revision_service.ActiveProfile.get_ctx_max",
            return_value=8192,
        ):
            result = await service.revise_document(file_bytes, "md")

        assert isinstance(result, str)
        assert "Titre corrigé" in result
        assert "Contenu corrigé" in result


# ---------------------------------------------------------------------------
# Tests : Fichier .txt non-UTF-8 → DocumentParseError
# ---------------------------------------------------------------------------


class TestNonUtf8TxtFile:
    """Vérifie qu'un fichier .txt non-UTF-8 lève DocumentParseError."""

    @pytest.mark.asyncio
    async def test_non_utf8_txt_raises_document_parse_error(self):
        """Un fichier .txt encodé en latin-1 lève DocumentParseError."""
        mock_llm = _mock_llm_service()
        service = RevisionService(mock_llm)

        # Bytes non-UTF-8 (latin-1 avec caractères accentués)
        non_utf8_bytes = "Résumé avec accents spéciaux".encode("latin-1")
        # Ajouter des bytes invalides en UTF-8
        non_utf8_bytes = b"\xff\xfe" + non_utf8_bytes

        with pytest.raises(DocumentParseError):
            with patch(
                "services.revision_service.ActiveProfile.get_ctx_max",
                return_value=8192,
            ):
                await service.revise_document(non_utf8_bytes, "txt")

    @pytest.mark.asyncio
    async def test_non_utf8_md_raises_document_parse_error(self):
        """Un fichier .md non-UTF-8 lève aussi DocumentParseError."""
        mock_llm = _mock_llm_service()
        service = RevisionService(mock_llm)

        # Bytes invalides en UTF-8
        non_utf8_bytes = b"\x80\x81\x82\x83\x84\x85"

        with pytest.raises(DocumentParseError):
            with patch(
                "services.revision_service.ActiveProfile.get_ctx_max",
                return_value=8192,
            ):
                await service.revise_document(non_utf8_bytes, "md")
