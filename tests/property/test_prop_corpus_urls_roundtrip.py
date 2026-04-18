"""Test par propriété — Aller-retour de parsing du urls.yaml.

Feature: admin-corpus-management
Property 2: urls.yaml round-trip

**Valide : Exigence 1.2**

Propriété 2 : Pour tout ensemble valide d'entrées URL, sérialiser en YAML
sous la clé 'urls' puis appeler load_urls() doit retourner les mêmes
entrées avec les mêmes valeurs de champs.
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

# URLs valides
url_strategy = st.from_regex(
    r"https?://[a-z][a-z0-9]{1,20}\.[a-z]{2,6}(/[a-z0-9_-]{1,20}){0,3}",
    fullmatch=True,
)

# Types valides dans urls.yaml
url_types = st.sampled_from([
    "institutionnel", "juridique", "academique", "pdf_externe", "site_web",
])

# Dates au format ISO
dates = st.dates().map(lambda d: d.isoformat())

# Stratégie pour une entrée URL
url_item_strategy = st.fixed_dictionaries({
    "nom": safe_text,
    "url": url_strategy,
    "description": safe_text,
    "type": url_types,
    "date_ajout": dates,
})

# Liste d'entrées URL
url_list_strategy = st.lists(url_item_strategy, min_size=1, max_size=10)


# ---------------------------------------------------------------------------
# Propriété 2 — Round-trip sérialisation → load_urls()
# ---------------------------------------------------------------------------


@settings(max_examples=50, deadline=None)
@given(items=url_list_strategy)
def test_urls_yaml_roundtrip(items: list[dict]):
    """Sérialiser en YAML puis load_urls() retourne les mêmes entrées.

    Pour tout ensemble valide d'entrées URL :
    1. Sérialiser sous la clé 'urls' en YAML
    2. Écrire dans un fichier temporaire
    3. Appeler load_urls() via CorpusContentService
    4. Vérifier que la liste retournée est identique
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        corpus_base = Path(tmp_dir)
        domaine = "test_domaine"
        urls_dir = corpus_base / domaine / "urls"
        urls_dir.mkdir(parents=True)

        # Sérialiser en YAML
        urls_path = urls_dir / "urls.yaml"
        with open(urls_path, "w", encoding="utf-8") as f:
            yaml.dump(
                {"urls": items},
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        # Charger via le service
        service = CorpusContentService(corpus_base_path=corpus_base)
        result = service.load_urls(domaine)

        # Vérifier le round-trip
        assert len(result) == len(items)
        for original, loaded in zip(items, result):
            assert loaded["nom"] == original["nom"]
            assert loaded["url"] == original["url"]
            assert loaded["description"] == original["description"]
            assert loaded["type"] == original["type"]
            assert loaded["date_ajout"] == original["date_ajout"]


@settings(max_examples=50, deadline=None)
@given(items=url_list_strategy)
def test_urls_yaml_double_roundtrip_idempotent(items: list[dict]):
    """Un double round-trip (write → load → write → load) est idempotent."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        corpus_base = Path(tmp_dir)
        domaine = "test_domaine"
        urls_dir = corpus_base / domaine / "urls"
        urls_dir.mkdir(parents=True)

        urls_path = urls_dir / "urls.yaml"

        # Premier round-trip
        with open(urls_path, "w", encoding="utf-8") as f:
            yaml.dump(
                {"urls": items},
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        service = CorpusContentService(corpus_base_path=corpus_base)
        result_1 = service.load_urls(domaine)

        # Deuxième round-trip
        with open(urls_path, "w", encoding="utf-8") as f:
            yaml.dump(
                {"urls": result_1},
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        result_2 = service.load_urls(domaine)

        assert result_1 == result_2


def test_urls_empty_file_returns_empty_list():
    """Un fichier urls.yaml absent retourne une liste vide."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        corpus_base = Path(tmp_dir)
        service = CorpusContentService(corpus_base_path=corpus_base)
        result = service.load_urls("domaine_inexistant")
        assert result == []
