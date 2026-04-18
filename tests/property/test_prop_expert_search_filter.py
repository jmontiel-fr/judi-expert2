"""Test par propriété — Filtrage des experts par recherche.

**Validates: Requirements 3.6, 3.7**

Feature: admin-corpus-management, Property 3: expert search filtering

Propriété 3 : Pour toute liste d'experts et pour toute chaîne de recherche
non vide, le filtrage côté client doit retourner exactement les experts dont
le ``nom``, le ``prenom`` ou l'``email`` contient la chaîne de recherche
(insensible à la casse). Aucun expert correspondant ne doit être exclu, et
aucun expert non correspondant ne doit être inclus.
"""

from __future__ import annotations

from typing import TypedDict

from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class ExpertDict(TypedDict):
    """Représentation minimale d'un expert pour le filtrage."""

    nom: str
    prenom: str
    email: str


# ---------------------------------------------------------------------------
# Pure filtering function (mirrors frontend ExpertsTab logic)
# ---------------------------------------------------------------------------


def filter_experts(experts: list[ExpertDict], query: str) -> list[ExpertDict]:
    """Filtre les experts par nom, prénom ou email (insensible à la casse).

    Réplique exacte de la logique du composant ``ExpertsTab`` côté frontend :

    .. code-block:: typescript

        const q = searchQuery.toLowerCase();
        experts.filter(e =>
            e.nom.toLowerCase().includes(q) ||
            e.prenom.toLowerCase().includes(q) ||
            e.email.toLowerCase().includes(q)
        );

    Args:
        experts: Liste de dictionnaires expert avec clés nom, prenom, email.
        query: Chaîne de recherche saisie par l'administrateur.

    Returns:
        Sous-liste des experts correspondant à la recherche.
    """
    q = query.lower()
    return [
        e
        for e in experts
        if q in e["nom"].lower()
        or q in e["prenom"].lower()
        or q in e["email"].lower()
    ]


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Alphabet restreint : lettres, chiffres, tirets (pas de caractères spéciaux
# qui pourraient rendre les tests fragiles sans raison).
_name_alphabet = st.characters(whitelist_categories=("L", "N", "Pd"))

_name_strategy = st.text(min_size=1, max_size=50, alphabet=_name_alphabet)

_email_strategy = st.builds(
    lambda local, domain: f"{local}@{domain}.com",
    local=st.text(min_size=1, max_size=20, alphabet=_name_alphabet),
    domain=st.text(min_size=1, max_size=15, alphabet=_name_alphabet),
)

expert_strategy: st.SearchStrategy[ExpertDict] = st.fixed_dictionaries(
    {
        "nom": _name_strategy,
        "prenom": _name_strategy,
        "email": _email_strategy,
    }
)

experts_list_strategy = st.lists(expert_strategy, min_size=0, max_size=20)

search_query_strategy = st.text(min_size=1, max_size=30, alphabet=_name_alphabet)


# ---------------------------------------------------------------------------
# Property 3a — Non-empty query returns exactly matching experts
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(experts=experts_list_strategy, query=search_query_strategy)
def test_filter_returns_exactly_matching_experts(
    experts: list[ExpertDict],
    query: str,
) -> None:
    """**Validates: Requirements 3.6, 3.7**

    Property 3a: For any list of experts and any non-empty search query,
    ``filter_experts`` returns exactly the experts whose nom, prenom, or
    email contains the query (case-insensitive).

    No matching expert is excluded; no non-matching expert is included.
    """
    result = filter_experts(experts, query)
    q = query.lower()

    # Build expected set by index to handle duplicates correctly.
    expected_indices = {
        i
        for i, e in enumerate(experts)
        if q in e["nom"].lower()
        or q in e["prenom"].lower()
        or q in e["email"].lower()
    }
    result_indices = {
        i for i, e in enumerate(experts) if e in result
    }

    # Completeness: no matching expert excluded.
    missing = expected_indices - result_indices
    assert not missing, (
        f"Matching experts excluded: indices {missing}, query={query!r}"
    )

    # Soundness: no non-matching expert included.
    extra = result_indices - expected_indices
    assert not extra, (
        f"Non-matching experts included: indices {extra}, query={query!r}"
    )

    # Length must match (guards against duplicated entries in result).
    assert len(result) == len(expected_indices), (
        f"Expected {len(expected_indices)} results, got {len(result)}"
    )


# ---------------------------------------------------------------------------
# Property 3b — Empty query returns all experts
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(experts=experts_list_strategy)
def test_empty_query_returns_all_experts(
    experts: list[ExpertDict],
) -> None:
    """**Validates: Requirements 3.6, 3.7**

    Property 3b: For any list of experts, an empty search query returns
    all experts unchanged (the empty string is contained in every string).
    """
    result = filter_experts(experts, "")
    assert result == experts, (
        f"Empty query should return all {len(experts)} experts, "
        f"got {len(result)}"
    )
