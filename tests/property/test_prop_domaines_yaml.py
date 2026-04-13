"""Test par propriété — Parsing round-trip du fichier domaines.yaml.

**Validates: Requirements 22.1, 22.2**

Propriété 12 : Pour toute configuration de domaines valide, la sérialisation
en YAML puis le parsing du fichier résultant doit produire une structure de
données équivalente à l'originale, préservant le nom, le répertoire,
l'indicateur actif et les chemins du corpus de chaque domaine.
"""

import sys
import tempfile
from pathlib import Path

import pytest
import yaml
from hypothesis import HealthCheck, given, settings, assume
from hypothesis import strategies as st

# Ajouter le backend au path
sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[2]
        / "site-central"
        / "local"
        / "web"
        / "backend"
    ),
)


# ---------------------------------------------------------------------------
# Stratégies Hypothesis pour les domaines
# ---------------------------------------------------------------------------

# Noms de domaine valides (alphanumériques + underscore, non-vide)
domaine_names = st.from_regex(r"[a-z][a-z0-9_]{1,30}", fullmatch=True)

# Chemins de répertoire valides
dir_paths = st.from_regex(r"corpus/[a-z][a-z0-9_]{1,20}", fullmatch=True)

# Stratégie pour un corpus
corpus_strategy = st.fixed_dictionaries({
    "documents": st.from_regex(r"corpus/[a-z_]+/documents/", fullmatch=True),
    "urls": st.from_regex(r"corpus/[a-z_]+/urls/urls\.yaml", fullmatch=True),
})

# Stratégie pour un domaine complet
domaine_strategy = st.fixed_dictionaries({
    "nom": domaine_names,
    "repertoire": dir_paths,
    "actif": st.booleans(),
    "corpus": corpus_strategy,
}).flatmap(
    lambda d: st.fixed_dictionaries({
        "nom": st.just(d["nom"]),
        "repertoire": st.just(d["repertoire"]),
        "actif": st.just(d["actif"]),
        "corpus": st.just(d["corpus"]),
        # contenu est optionnel
        "contenu": st.one_of(
            st.none(),
            st.from_regex(r"corpus/[a-z_]+/contenu\.yaml", fullmatch=True),
        ),
    })
)

# Stratégie pour la configuration complète
domaines_config_strategy = st.fixed_dictionaries({
    "domaines": st.lists(domaine_strategy, min_size=1, max_size=10),
})


# ---------------------------------------------------------------------------
# Helpers : sérialisation / parsing
# ---------------------------------------------------------------------------


def serialize_domaines(config: dict) -> str:
    """Sérialise une configuration de domaines en YAML."""
    # Nettoyer les clés None (contenu optionnel)
    cleaned = {"domaines": []}
    for domaine in config["domaines"]:
        d = {
            "nom": domaine["nom"],
            "repertoire": domaine["repertoire"],
            "actif": domaine["actif"],
            "corpus": domaine["corpus"],
        }
        if domaine.get("contenu") is not None:
            d["contenu"] = domaine["contenu"]
        cleaned["domaines"].append(d)
    return yaml.dump(cleaned, default_flow_style=False, allow_unicode=True)


def parse_domaines(yaml_str: str) -> dict:
    """Parse une chaîne YAML en configuration de domaines."""
    return yaml.safe_load(yaml_str)


def normalize_domaine(domaine: dict) -> dict:
    """Normalise un domaine pour la comparaison (supprime les clés None)."""
    result = {
        "nom": domaine["nom"],
        "repertoire": domaine["repertoire"],
        "actif": domaine["actif"],
        "corpus": domaine["corpus"],
    }
    if domaine.get("contenu") is not None:
        result["contenu"] = domaine["contenu"]
    return result


# ---------------------------------------------------------------------------
# Propriété 12 — Round-trip sérialisation → parsing
# ---------------------------------------------------------------------------


@settings(
    max_examples=50,
    deadline=None,
)
@given(config=domaines_config_strategy)
def test_yaml_roundtrip_preserves_structure(config: dict):
    """La sérialisation en YAML puis le parsing produit une structure équivalente.

    Pour toute configuration de domaines valide :
    1. Sérialiser en YAML
    2. Parser le YAML résultant
    3. Vérifier que la structure est identique à l'originale
    """
    yaml_str = serialize_domaines(config)
    parsed = parse_domaines(yaml_str)

    assert "domaines" in parsed
    assert len(parsed["domaines"]) == len(config["domaines"])

    for original, restored in zip(config["domaines"], parsed["domaines"]):
        orig_norm = normalize_domaine(original)
        rest_norm = normalize_domaine(restored)

        # Nom préservé
        assert rest_norm["nom"] == orig_norm["nom"]
        # Répertoire préservé
        assert rest_norm["repertoire"] == orig_norm["repertoire"]
        # Indicateur actif préservé
        assert rest_norm["actif"] == orig_norm["actif"]
        # Corpus préservé
        assert rest_norm["corpus"] == orig_norm["corpus"]
        # Contenu préservé (si présent)
        assert rest_norm.get("contenu") == orig_norm.get("contenu")


@settings(
    max_examples=50,
    deadline=None,
)
@given(config=domaines_config_strategy)
def test_yaml_roundtrip_via_file(config: dict):
    """Le round-trip via fichier (écriture + lecture) préserve la structure."""
    yaml_str = serialize_domaines(config)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        f.write(yaml_str)
        tmp_path = f.name

    try:
        with open(tmp_path, "r", encoding="utf-8") as f:
            parsed = yaml.safe_load(f)

        assert len(parsed["domaines"]) == len(config["domaines"])

        for original, restored in zip(config["domaines"], parsed["domaines"]):
            orig_norm = normalize_domaine(original)
            rest_norm = normalize_domaine(restored)
            assert rest_norm == orig_norm
    finally:
        import os
        os.unlink(tmp_path)


@settings(
    max_examples=30,
    deadline=None,
)
@given(config=domaines_config_strategy)
def test_yaml_double_roundtrip_idempotent(config: dict):
    """Un double round-trip (serialize → parse → serialize → parse) est idempotent."""
    yaml_str_1 = serialize_domaines(config)
    parsed_1 = parse_domaines(yaml_str_1)
    yaml_str_2 = serialize_domaines(parsed_1)
    parsed_2 = parse_domaines(yaml_str_2)

    assert parsed_1 == parsed_2


# ---------------------------------------------------------------------------
# Test avec le fichier domaines.yaml réel du projet
# ---------------------------------------------------------------------------


def test_real_domaines_yaml_roundtrip():
    """Le fichier domaines.yaml réel du projet survit au round-trip."""
    real_path = Path(__file__).resolve().parents[2] / "domaines" / "domaines.yaml"
    if not real_path.exists():
        pytest.skip("Fichier domaines/domaines.yaml non trouvé")

    with open(real_path, "r", encoding="utf-8") as f:
        original_str = f.read()

    original = yaml.safe_load(original_str)

    # Round-trip
    reserialized = yaml.dump(original, default_flow_style=False, allow_unicode=True)
    reparsed = yaml.safe_load(reserialized)

    assert reparsed == original

    # Vérifications structurelles spécifiques au projet
    assert "domaines" in original
    domaines = original["domaines"]
    assert len(domaines) == 5

    noms = {d["nom"] for d in domaines}
    assert noms == {"psychologie", "psychiatrie", "medecine_legale", "batiment", "comptabilite"}

    # Seul psychologie est actif
    actifs = [d for d in domaines if d["actif"]]
    assert len(actifs) == 1
    assert actifs[0]["nom"] == "psychologie"

    # Chaque domaine a un répertoire et un corpus
    for d in domaines:
        assert "repertoire" in d
        assert "corpus" in d
        assert "documents" in d["corpus"]
        assert "urls" in d["corpus"]
