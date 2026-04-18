"""Test par propriété — Upload PDF persiste le fichier et met à jour contenu.yaml.

Feature: admin-corpus-management
Property 4: PDF upload round-trip

**Valide : Exigence 5.3**

Propriété 4 : Pour tout nom de fichier PDF valide et contenu binaire non vide,
save_pdf() doit créer le fichier et ajouter l'entrée dans contenu.yaml.
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

# Noms de fichiers PDF valides (alphanumériques, tirets, underscores)
pdf_filename_strategy = st.from_regex(
    r"[a-zA-Z0-9_-]{1,30}\.pdf", fullmatch=True
)

# Contenu binaire non vide
binary_content_strategy = st.binary(min_size=1, max_size=1000)


# ---------------------------------------------------------------------------
# Propriété 4 — Upload PDF persiste le fichier et met à jour contenu.yaml
# ---------------------------------------------------------------------------


@settings(max_examples=50, deadline=None)
@given(filename=pdf_filename_strategy, content=binary_content_strategy)
def test_save_pdf_persists_file_and_updates_contenu(
    filename: str, content: bytes
):
    """**Validates: Requirements 5.3**

    Pour tout nom de fichier PDF valide et contenu binaire non vide :
    1. Appeler save_pdf() sur un CorpusContentService frais
    2. Vérifier que le fichier existe dans corpus/{domaine}/documents/
    3. Vérifier que le contenu du fichier correspond à l'entrée
    4. Vérifier que contenu.yaml contient l'entrée avec nom, type et date
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        corpus_base = Path(tmp_dir)
        domaine = "test_domaine"

        service = CorpusContentService(corpus_base_path=corpus_base)
        entry = service.save_pdf(domaine, filename, content)

        # 1. Le fichier existe sur disque
        file_path = corpus_base / domaine / "documents" / filename
        assert file_path.exists(), f"Le fichier {file_path} devrait exister"

        # 2. Le contenu du fichier correspond
        assert file_path.read_bytes() == content

        # 3. contenu.yaml contient l'entrée correcte
        contenu_path = corpus_base / domaine / "contenu.yaml"
        assert contenu_path.exists(), "contenu.yaml devrait exister"

        with open(contenu_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        items = data["contenu"]
        assert len(items) == 1

        item = items[0]
        assert item["nom"] == f"documents/{filename}"
        assert item["type"] == "document"
        assert item["date_ajout"] == date.today().isoformat()

        # 4. L'entrée retournée correspond aussi
        assert entry["nom"] == f"documents/{filename}"
        assert entry["type"] == "document"
        assert entry["date_ajout"] == date.today().isoformat()


# ---------------------------------------------------------------------------
# Test example-based — FileExistsError si doublon
# ---------------------------------------------------------------------------


def test_save_pdf_raises_file_exists_error_on_duplicate():
    """save_pdf() lève FileExistsError si un fichier du même nom existe déjà."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        corpus_base = Path(tmp_dir)
        domaine = "test_domaine"

        service = CorpusContentService(corpus_base_path=corpus_base)

        # Premier upload réussit
        service.save_pdf(domaine, "rapport.pdf", b"contenu initial")

        # Deuxième upload avec le même nom lève FileExistsError
        try:
            service.save_pdf(domaine, "rapport.pdf", b"autre contenu")
            assert False, "FileExistsError aurait dû être levée"
        except FileExistsError:
            pass
