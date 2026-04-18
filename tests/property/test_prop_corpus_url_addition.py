"""Test par propriété — Ajout d'URL persiste l'entrée dans urls.yaml.

Feature: admin-corpus-management
Property 5: URL addition round-trip

**Valide : Exigences 6.3, 7.3**
"""

import sys
import tempfile
from datetime import date
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

# Types valides pour l'ajout d'URL (pdf_externe ou site_web)
url_types = st.sampled_from(["pdf_externe", "site_web"])

# Description (peut être vide)
description_strategy = safe_text


# ---------------------------------------------------------------------------
# Propriété 5 — Ajout d'URL persiste l'entrée dans urls.yaml
# ---------------------------------------------------------------------------


@settings(max_examples=50, deadline=None)
@given(
    nom=safe_text,
    url=url_strategy,
    description=description_strategy,
    url_type=url_types,
)
def test_add_url_persists_entry_in_urls_yaml(
    nom: str, url: str, description: str, url_type: str
):
    """**Validates: Requirements 6.3, 7.3**

    Pour toute entrée URL valide :
    1. Appeler add_url() sur un CorpusContentService frais
    2. Vérifier que urls/urls.yaml existe dans le répertoire du domaine
    3. Vérifier que le YAML contient l'entrée avec tous les champs préservés
    4. Vérifier que date_ajout est la date du jour (ISO)
    5. Vérifier que le dict retourné correspond à l'entrée avec date_ajout
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        corpus_base = Path(tmp_dir)
        domaine = "test_domaine"

        entry = {
            "nom": nom,
            "url": url,
            "description": description,
            "type": url_type,
        }

        service = CorpusContentService(corpus_base_path=corpus_base)
        result = service.add_url(domaine, entry)

        # 1. Le fichier urls/urls.yaml existe
        urls_path = corpus_base / domaine / "urls" / "urls.yaml"
        assert urls_path.exists(), "urls/urls.yaml devrait exister"

        # 2. Le YAML contient l'entrée avec tous les champs préservés
        with open(urls_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        items = data["urls"]
        assert len(items) == 1

        item = items[0]
        assert item["nom"] == nom
        assert item["url"] == url
        assert item["description"] == description
        assert item["type"] == url_type

        # 3. date_ajout est la date du jour
        assert item["date_ajout"] == date.today().isoformat()

        # 4. Le dict retourné correspond
        assert result["nom"] == nom
        assert result["url"] == url
        assert result["description"] == description
        assert result["type"] == url_type
        assert result["date_ajout"] == date.today().isoformat()


# ---------------------------------------------------------------------------
# Propriété complémentaire — Accumulation d'entrées
# ---------------------------------------------------------------------------


@settings(max_examples=50, deadline=None)
@given(
    entries=st.lists(
        st.fixed_dictionaries({
            "nom": safe_text,
            "url": url_strategy,
            "description": safe_text,
            "type": url_types,
        }),
        min_size=1,
        max_size=10,
    )
)
def test_add_url_accumulates_entries(entries: list[dict]):
    """**Validates: Requirements 6.3, 7.3**

    Appeler add_url() N fois doit résulter en N entrées dans urls.yaml.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        corpus_base = Path(tmp_dir)
        domaine = "test_domaine"

        service = CorpusContentService(corpus_base_path=corpus_base)

        for entry in entries:
            service.add_url(domaine, entry)

        # Vérifier que urls.yaml contient exactement N entrées
        urls_path = corpus_base / domaine / "urls" / "urls.yaml"
        assert urls_path.exists()

        with open(urls_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        items = data["urls"]
        assert len(items) == len(entries)

        # Vérifier que chaque entrée a ses champs préservés
        for original, stored in zip(entries, items):
            assert stored["nom"] == original["nom"]
            assert stored["url"] == original["url"]
            assert stored["description"] == original["description"]
            assert stored["type"] == original["type"]
            assert stored["date_ajout"] == date.today().isoformat()
