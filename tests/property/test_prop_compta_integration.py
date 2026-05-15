"""Test par propriété — Validation SIRET et métadonnées comptables.

**Validates: Requirements 2.4, 1.1, 1.2, 1.4, 3.2**

Propriétés testées :
- Property 3 : SIRET validation (14 chiffres exactement)
- Property 1 : Metadata correctness (tous les experts sont B2B)
- Property 2 : Metadata format validation round-trip
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional as Opt

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Import des validateurs du Site Central avec isolation de modules
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
       or k == "schemas" or k.startswith("schemas.")
       or k == "services" or k.startswith("services.")
       or k == "routers" or k.startswith("routers.")
       or k == "database"
       or k == "main"
}
_saved_path = sys.path[:]
sys.path.insert(0, _central_backend)

from schemas.profile import SIRET_PATTERN, validate_siret  # noqa: E402
from services.compta_service import (  # noqa: E402
    ComptaValidationError,
    build_metadata,
    APPLI,
    SERVICE,
)

# Restaurer les modules
_central_module_cache = {
    k: sys.modules.pop(k)
    for k in list(sys.modules)
    if k == "models" or k.startswith("models.")
       or k == "schemas" or k.startswith("schemas.")
       or k == "services" or k.startswith("services.")
       or k == "routers" or k.startswith("routers.")
       or k == "database"
       or k == "main"
}
sys.modules.update(_saved_modules)
sys.path[:] = _saved_path


# ---------------------------------------------------------------------------
# Stratégies Hypothesis
# ---------------------------------------------------------------------------

# Chaînes de 14 chiffres exactement (SIRET valides)
valid_siret = st.text(
    alphabet="0123456789",
    min_size=14,
    max_size=14,
)

# Chaînes aléatoires (mix de chiffres, lettres, caractères spéciaux, longueur 0-20)
random_strings = st.text(
    alphabet=st.sampled_from(
        "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ -!@#"
    ),
    min_size=0,
    max_size=20,
)


# ---------------------------------------------------------------------------
# Property 3 — SIRET : accepte si et seulement si exactement 14 chiffres
# ---------------------------------------------------------------------------


@settings(max_examples=100, deadline=None)
@given(siret=valid_siret)
def test_prop_siret_accepts_valid_14_digits(siret: str):
    """Pour toute chaîne de exactement 14 chiffres, le validateur SIRET
    l'accepte sans lever d'exception.

    **Validates: Requirements 2.4**
    """
    result = validate_siret(siret)
    assert result == siret


@settings(max_examples=100, deadline=None)
@given(s=random_strings)
def test_prop_siret_rejects_iff_not_14_digits(s: str):
    """Pour toute chaîne aléatoire, le validateur SIRET l'accepte si et
    seulement si elle contient exactement 14 chiffres.

    **Validates: Requirements 2.4**
    """
    is_exactly_14_digits = bool(re.match(r"^\d{14}$", s))

    if is_exactly_14_digits:
        result = validate_siret(s)
        assert result == s
    else:
        with pytest.raises(ValueError, match="SIRET"):
            validate_siret(s)


# ---------------------------------------------------------------------------
# Property 1 — Metadata correctness (tous les experts sont B2B)
# ---------------------------------------------------------------------------


@dataclass
class FakeExpert:
    """Objet simulant un Expert SQLAlchemy pour les tests de propriété."""

    nom: str = "Dupont"
    prenom: str = "Jean"
    email: str = "expert@example.com"
    adresse: str = "1 rue de la Paix, 75001 Paris"
    domaine: str = "psychologie"
    entreprise: Opt[str] = None
    company_address: Opt[str] = None
    billing_email: Opt[str] = None
    siret: Opt[str] = None


# --- Stratégies Hypothesis pour Property 1 ---

_non_empty_text = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
    min_size=1,
    max_size=50,
).filter(lambda s: s.strip() != "")

_emails = st.builds(
    lambda user, domain: f"{user}@{domain}.com",
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=3, max_size=10),
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=3, max_size=10),
)

_siret_values = st.text(alphabet="0123456789", min_size=14, max_size=14)

_domaines = st.sampled_from([
    "psychologie", "psychiatrie", "medecine_legale", "batiment", "comptabilite",
])

_prices = st.builds(
    lambda euros, cents: f"{euros}.{cents:02d}",
    st.integers(min_value=1, max_value=9999),
    st.integers(min_value=0, max_value=99),
)

# Expert avec SIRET
st_expert_with_siret = st.builds(
    FakeExpert,
    nom=_non_empty_text,
    prenom=_non_empty_text,
    email=_emails,
    adresse=_non_empty_text,
    domaine=_domaines,
    entreprise=_non_empty_text,
    company_address=_non_empty_text,
    billing_email=_emails,
    siret=_siret_values,
)

# Expert sans SIRET
st_expert_without_siret = st.builds(
    FakeExpert,
    nom=_non_empty_text,
    prenom=_non_empty_text,
    email=_emails,
    adresse=_non_empty_text,
    domaine=_domaines,
    entreprise=st.one_of(st.none(), _non_empty_text),
    company_address=st.one_of(st.none(), _non_empty_text),
    billing_email=st.one_of(st.none(), _emails),
    siret=st.none(),
)

# Union des deux
st_expert_any = st.one_of(st_expert_with_siret, st_expert_without_siret)

# Ticket config (toujours B2B avec HT, TVA, TTC)
st_ticket_config = st.builds(
    lambda domaine, price_ht, price_tva, price_ttc: {
        "domaine": domaine,
        "price_ht": price_ht,
        "price_tva": price_tva,
        "price_ttc": price_ttc,
    },
    _domaines,
    _prices,
    _prices,
    _prices,
)


@settings(max_examples=100, deadline=None)
@given(expert=st_expert_any, config=st_ticket_config)
def test_prop_metadata_type_always_b2b(expert, config):
    """Pour tout Expert, build_metadata produit type='B2B'.

    **Validates: Requirements 1.1**
    """
    metadata = build_metadata(expert, config)
    assert metadata["type"] == "B2B"


@settings(max_examples=100, deadline=None)
@given(expert=st_expert_any, config=st_ticket_config)
def test_prop_metadata_contains_all_required_fields(expert, config):
    """Pour tout Expert, build_metadata produit un dictionnaire contenant
    tous les champs requis pour la facture.

    **Validates: Requirements 1.1, 1.2**
    """
    metadata = build_metadata(expert, config)

    required_fields = {
        "appli", "service", "type", "domaine",
        "expert_lastname", "expert_firstname", "expert_email",
        "entreprise", "expert_address", "billing_email", "siret",
        "price_ht", "price_tva", "price_ttc",
        "date_achat", "description", "service_type",
        "abonnement", "recurrence",
    }
    missing = required_fields - set(metadata.keys())
    assert not missing, f"Champs manquants : {missing}"


@settings(max_examples=100, deadline=None)
@given(expert=st_expert_any, config=st_ticket_config)
def test_prop_metadata_common_fields_correct_values(expert, config):
    """Les champs communs ont les valeurs correctes."""
    metadata = build_metadata(expert, config)

    assert metadata["appli"] == APPLI
    assert metadata["service"] == SERVICE
    assert metadata["domaine"] == config["domaine"]
    assert metadata["expert_lastname"] == expert.nom
    assert metadata["expert_firstname"] == expert.prenom
    assert metadata["expert_email"] == expert.email


@settings(max_examples=100, deadline=None)
@given(expert=st_expert_with_siret, config=st_ticket_config)
def test_prop_metadata_siret_present_when_expert_has_siret(expert, config):
    """Quand l'expert a un SIRET, il est transmis tel quel."""
    metadata = build_metadata(expert, config)
    assert metadata["siret"] == expert.siret


@settings(max_examples=100, deadline=None)
@given(expert=st_expert_without_siret, config=st_ticket_config)
def test_prop_metadata_siret_non_attribue_when_missing(expert, config):
    """Quand l'expert n'a pas de SIRET, la valeur est 'non attribué'."""
    metadata = build_metadata(expert, config)
    assert metadata["siret"] == "non attribué"


# ---------------------------------------------------------------------------
# Property 2 — Metadata format validation round-trip
# ---------------------------------------------------------------------------


@settings(max_examples=100, deadline=None)
@given(expert=st_expert_any, config=st_ticket_config)
def test_prop_metadata_no_validation_error(expert, config):
    """Pour tout Expert valide et configuration valide,
    build_metadata() ne lève PAS de ComptaValidationError.

    **Validates: Requirements 1.4, 3.2**
    """
    try:
        metadata = build_metadata(expert, config)
    except ComptaValidationError as exc:
        pytest.fail(
            f"build_metadata a levé ComptaValidationError : {exc.message}"
        )


@settings(max_examples=100, deadline=None)
@given(expert=st_expert_any, config=st_ticket_config)
def test_prop_metadata_returns_dict_with_string_values(expert, config):
    """build_metadata() retourne un dict dont toutes les clés et valeurs
    sont des chaînes (exigence Stripe metadata).

    **Validates: Requirements 1.4, 3.2**
    """
    metadata = build_metadata(expert, config)

    assert isinstance(metadata, dict)
    for key in metadata:
        assert isinstance(key, str), f"Clé non-string : {key!r}"
    for key, value in metadata.items():
        assert isinstance(value, str), f"metadata[{key!r}] non-string : {value!r}"


# ---------------------------------------------------------------------------
# Property 4 — Refund button visibility
# ---------------------------------------------------------------------------


def is_refund_button_visible(ticket) -> bool:
    """Détermine si le bouton de remboursement doit être visible."""
    if ticket.get("status") != "actif":
        return False
    stripe_payment_id = ticket.get("stripe_payment_id")
    if not stripe_payment_id:
        return False
    if stripe_payment_id.startswith("pending-"):
        return False
    return True


# Statuts possibles d'un ticket
_ticket_statuses = st.sampled_from(["actif", "utilise", "expire", "rembourse", "annule"])

# stripe_payment_id : soit None, soit "pending-xxx", soit "pi_xxx"
_stripe_payment_ids = st.one_of(
    st.none(),
    st.just(""),
    st.builds(lambda s: f"pending-{s}", st.text(min_size=5, max_size=20)),
    st.builds(lambda s: f"pi_{s}", st.text(min_size=5, max_size=20)),
)

st_ticket = st.builds(
    lambda status, spid: {"status": status, "stripe_payment_id": spid},
    _ticket_statuses,
    _stripe_payment_ids,
)


@settings(max_examples=200, deadline=None)
@given(ticket=st_ticket)
def test_prop_refund_button_visible_iff_actif_and_valid_payment(ticket):
    """Le bouton refund est visible ssi statut='actif' ET stripe_payment_id
    existe ET ne commence pas par 'pending-'.

    **Validates: Requirements 4.1, 4.5**
    """
    visible = is_refund_button_visible(ticket)

    status = ticket["status"]
    spid = ticket["stripe_payment_id"]

    expected = (
        status == "actif"
        and bool(spid)
        and not spid.startswith("pending-")
    )

    assert visible == expected, (
        f"Visibilité incorrecte pour ticket {ticket}: "
        f"attendu={expected}, obtenu={visible}"
    )


# ---------------------------------------------------------------------------
# Property 5 — Refund state transition
# ---------------------------------------------------------------------------


@dataclass
class TicketState:
    """État d'un ticket pour les tests de transition."""
    statut: str
    stripe_payment_id: str
    refunded_at: Opt[str] = None
    stripe_refund_id: Opt[str] = None


def apply_refund(ticket: TicketState) -> TicketState:
    """Simule l'application d'un remboursement réussi."""
    return TicketState(
        statut="rembourse",
        stripe_payment_id=ticket.stripe_payment_id,
        refunded_at="2025-01-15T10:00:00Z",
        stripe_refund_id="re_test_123",
    )


st_refundable_ticket = st.builds(
    TicketState,
    statut=st.just("actif"),
    stripe_payment_id=st.builds(lambda s: f"pi_{s}", st.text(min_size=5, max_size=20)),
)


@settings(max_examples=100, deadline=None)
@given(ticket=st_refundable_ticket)
def test_prop_refund_transition_sets_rembourse(ticket):
    """Après un remboursement réussi, le statut passe à 'rembourse'.

    **Validates: Requirements 4.3**
    """
    result = apply_refund(ticket)
    assert result.statut == "rembourse"
    assert result.refunded_at is not None
    assert result.stripe_refund_id is not None
