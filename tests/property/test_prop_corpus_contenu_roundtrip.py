"""Test par propriété — Aller-retour de parsing du contenu.yaml.

Feature: admin-corpus-management
Property 1: contenu.yaml round-trip

**Valide : Exigence 1.1**

Propriété 1 : Pour tout ensemble valide d'éléments de contenu, sérialiser
en YAML sous la clé 'contenu' puis appeler load_contenu() doit retourner
les mêmes éléments avec les mêmes valeurs de champs.
"""

import sys
import tempfile
from pathlib import Path

import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Module isolation: load Site Central backend without conflicts
# ---------------------------------------------------------------------------
_central_backend = str(
    Path(__file__).resolve().parents[2] / "central-site" / "web" / "backend"
)

_modules_to_isolate = [
    "models", "database", "routers", "schemas", "services", "main",
]

_saved_modules = {}
for _prefix in _modules_to_isolate:
    for _k in list(sys.modules):
        if _k == _prefix or _k.startswith(_prefix + "."):
            _saved_modules[_k] = sys.modules.pop(_k)

_saved_path = sys.path[:]
sys.path.insert(0, _central_backend)

from services.corpus_content_service import CorpusContentService  # noqa: E402

_central_cache = {}
for _prefix in _modules_to_isolate:
    for _k in list(sys.modules):
        if _k == _prefix or _k.startswith(_prefix + "."):
            _central_cache[_k] = sys.modules.pop(_k)

sys.modules.update(_saved_modules)
sys.path[:] = _saved_path


# ---------------------------------------------------------------------------
# Stratégies Hypothesis
# ---------------------------------------------------------------------------

# Texte simple sans caractères problématiques pour YAML
safe_text = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "Z"),
        blacklist_characters="\x00\r",
    ),
    min_size=1,
    max_size=100,
)

# Types valides dans contenu.yaml
contenu_types = st.sampled_from(["template", "document", "url"])

# Dates au format ISO
dates = st.dates().map(lambda d: d.isoformat())

# Stratégie pour un élément de contenu
contenu_item_strategy = st.fixed_dictionaries({
    "nom": safe_text,
    "description": safe_text,
    "type": contenu_types,
    "date_ajout": dates,
})

# Liste d'éléments de contenu
contenu_list_strategy = st.lists(contenu_item_strategy, min_size=1, max_size=10)


# ---------------------------------------------------------------------------
# Propriété 1 — Round-trip sérialisation → load_contenu()
# ---------------------------------------------------------------------------


@settings(max_examples=50, deadline=None)
@given(items=contenu_list_strategy)
def test_contenu_yaml_roundtrip(items: list[dict]):
    """Sérialiser en YAML puis load_contenu() retourne les mêmes éléments.

    Pour tout ensemble valide d'éléments de contenu :
    1. Sérialiser sous la clé 'contenu' en YAML
    2. Écrire dans un fichier temporaire
    3. Appeler load_contenu() via CorpusContentService
    4. Vérifier que la liste retournée est identique
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        corpus_base = Path(tmp_dir)
        domaine = "test_domaine"
        domaine_dir = corpus_base / domaine
        domaine_dir.mkdir()

        # Sérialiser en YAML
        contenu_path = domaine_dir / "contenu.yaml"
        with open(contenu_path, "w", encoding="utf-8") as f:
            yaml.dump(
                {"contenu": items},
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        # Charger via le service
        service = CorpusContentService(corpus_base_path=corpus_base)
        result = service.load_contenu(domaine)

        # Vérifier le round-trip
        assert len(result) == len(items)
        for original, loaded in zip(items, result):
            assert loaded["nom"] == original["nom"]
            assert loaded["description"] == original["description"]
            assert loaded["type"] == original["type"]
            assert loaded["date_ajout"] == original["date_ajout"]


@settings(max_examples=50, deadline=None)
@given(items=contenu_list_strategy)
def test_contenu_yaml_double_roundtrip_idempotent(items: list[dict]):
    """Un double round-trip (write → load → write → load) est idempotent."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        corpus_base = Path(tmp_dir)
        domaine = "test_domaine"
        domaine_dir = corpus_base / domaine
        domaine_dir.mkdir()

        contenu_path = domaine_dir / "contenu.yaml"

        # Premier round-trip
        with open(contenu_path, "w", encoding="utf-8") as f:
            yaml.dump(
                {"contenu": items},
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        service = CorpusContentService(corpus_base_path=corpus_base)
        result_1 = service.load_contenu(domaine)

        # Deuxième round-trip
        with open(contenu_path, "w", encoding="utf-8") as f:
            yaml.dump(
                {"contenu": result_1},
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        result_2 = service.load_contenu(domaine)

        assert result_1 == result_2


def test_contenu_empty_file_returns_empty_list():
    """Un fichier contenu.yaml absent retourne une liste vide."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        corpus_base = Path(tmp_dir)
        service = CorpusContentService(corpus_base_path=corpus_base)
        result = service.load_contenu("domaine_inexistant")
        assert result == []
