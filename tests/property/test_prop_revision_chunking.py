"""Property-based tests — Document Revision Chunking.

Feature: document-revision

Property-based tests validating correctness properties of the
RevisionService chunking algorithm.

- Property 5: Respect de la limite de taille des chunks (Validates: Requirements 7.4)
"""

import sys
from pathlib import Path
from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

# Ajouter le backend au path pour importer les services
sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[2]
        / "local-site"
        / "web"
        / "backend"
    ),
)

from services.revision_models import ParagraphInfo
from services.revision_service import (
    CHARS_PER_TOKEN,
    CTX_USAGE_RATIO,
    RevisionService,
)


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------


@st.composite
def paragraph_lists(draw: st.DrawFn) -> list[ParagraphInfo]:
    """Génère des listes de ParagraphInfo avec des textes de longueurs variées.

    Produit entre 1 et 50 paragraphes, chacun contenant un texte de
    longueur variable (1 à 5000 caractères) pour tester le chunking
    dans des conditions variées.
    """
    n_paragraphs = draw(st.integers(min_value=1, max_value=50))
    paragraphs: list[ParagraphInfo] = []

    for i in range(n_paragraphs):
        text = draw(
            st.text(
                alphabet=st.characters(
                    whitelist_categories=("L", "N", "P", "Z"),
                    blacklist_characters="\x00",
                ),
                min_size=1,
                max_size=5000,
            )
        )
        para = ParagraphInfo(
            index=i,
            runs=[],
            xml_element=None,
            properties=None,
            full_text=text,
        )
        paragraphs.append(para)

    return paragraphs


# ---------------------------------------------------------------------------
# Propriété 5 — Respect de la limite de taille des chunks
# ---------------------------------------------------------------------------


@settings(max_examples=100, deadline=None)
@given(
    paragraphs=paragraph_lists(),
    ctx_max=st.integers(min_value=1024, max_value=131072),
)
def test_chunk_size_respects_context_window_limit(
    paragraphs: list[ParagraphInfo],
    ctx_max: int,
) -> None:
    """Pour tout document, le chunking produit des chunks dont le nombre
    estimé de tokens ne dépasse pas 60% de ctx_max.

    **Validates: Requirements 7.4**

    Vérifie que chaque chunk produit par _build_chunks() a un total de
    tokens estimés (len(text) // CHARS_PER_TOKEN) qui ne dépasse pas
    int(ctx_max * CTX_USAGE_RATIO), sauf dans le cas d'un paragraphe
    unique qui dépasse la limite à lui seul (il forme alors son propre
    chunk isolé).
    """
    max_tokens_per_chunk = int(ctx_max * CTX_USAGE_RATIO)

    # Mock ActiveProfile.get_ctx_max() pour retourner la valeur générée
    with patch(
        "services.revision_service.ActiveProfile.get_ctx_max",
        return_value=ctx_max,
    ):
        service = RevisionService.__new__(RevisionService)
        chunks = service._build_chunks(paragraphs)

    # Vérifier que chaque chunk respecte la limite
    for chunk_idx, chunk in enumerate(chunks):
        chunk_tokens = sum(
            max(1, len(p.full_text) // CHARS_PER_TOKEN) for p in chunk
        )

        # Un chunk avec un seul paragraphe qui dépasse la limite est acceptable
        # (le paragraphe ne peut pas être coupé)
        if len(chunk) == 1:
            single_para_tokens = max(
                1, len(chunk[0].full_text) // CHARS_PER_TOKEN
            )
            if single_para_tokens >= max_tokens_per_chunk:
                # Ce paragraphe dépasse la limite à lui seul — acceptable
                continue

        assert chunk_tokens <= max_tokens_per_chunk, (
            f"Chunk {chunk_idx} dépasse la limite de tokens : "
            f"{chunk_tokens} tokens > {max_tokens_per_chunk} "
            f"(ctx_max={ctx_max}, ratio={CTX_USAGE_RATIO}). "
            f"Chunk contient {len(chunk)} paragraphes."
        )
