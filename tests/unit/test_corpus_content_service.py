"""Tests unitaires pour le service corpus_content_service.

Teste la lecture/écriture des fichiers YAML (contenu.yaml, urls.yaml),
la gestion des fichiers PDF, et la résolution des chemins.

Exigences validées : 1.1, 1.2, 1.4, 5.3, 6.3, 7.3
"""

import sys
import tempfile
from datetime import date
from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Module isolation: load Site Central backend
# ---------------------------------------------------------------------------
_central_backend = str(
    Path(__file__).resolve().parents[2] / "central-site" / "web" / "backend"
)

_modules_to_isolate = [
    "models", "database", "routers", "schemas", "services", "main",
]

_saved_modules = {}
for prefix in _modules_to_isolate:
    for k in list(sys.modules):
        if k == prefix or k.startswith(prefix + "."):
            _saved_modules[k] = sys.modules.pop(k)

_saved_path = sys.path[:]
sys.path.insert(0, _central_backend)

from services.corpus_content_service import CorpusContentService  # noqa: E402

# Cache central modules, then restore originals
_central_cache = {}
for prefix in _modules_to_isolate:
    for k in list(sys.modules):
        if k == prefix or k.startswith(prefix + "."):
            _central_cache[k] = sys.modules.pop(k)

sys.modules.update(_saved_modules)
sys.path[:] = _saved_path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def corpus_dir(tmp_path: Path) -> Path:
    """Crée un répertoire corpus temporaire."""
    return tmp_path


@pytest.fixture
def service(corpus_dir: Path) -> CorpusContentService:
    """Instance du service pointant vers le répertoire temporaire."""
    return CorpusContentService(corpus_base_path=corpus_dir)


# ---------------------------------------------------------------------------
# _resolve_contenu_path / _resolve_urls_path
# ---------------------------------------------------------------------------


class TestResolvePaths:
    """Vérifie que les chemins sont résolus correctement."""

    def test_resolve_contenu_path(self, service: CorpusContentService, corpus_dir: Path):
        result = service._resolve_contenu_path("psychologie")
        assert result == corpus_dir / "psychologie" / "contenu.yaml"

    def test_resolve_urls_path(self, service: CorpusContentService, corpus_dir: Path):
        result = service._resolve_urls_path("psychologie")
        assert result == corpus_dir / "psychologie" / "urls" / "urls.yaml"

    def test_resolve_paths_different_domaines(
        self, service: CorpusContentService, corpus_dir: Path
    ):
        for domaine in ("psychiatrie", "batiment", "comptabilite"):
            assert service._resolve_contenu_path(domaine) == (
                corpus_dir / domaine / "contenu.yaml"
            )
            assert service._resolve_urls_path(domaine) == (
                corpus_dir / domaine / "urls" / "urls.yaml"
            )


# ---------------------------------------------------------------------------
# load_contenu
# ---------------------------------------------------------------------------


class TestLoadContenu:
    """Tests pour la lecture de contenu.yaml."""

    def test_fichier_absent_retourne_liste_vide(self, service: CorpusContentService):
        """Si contenu.yaml n'existe pas, retourne []."""
        result = service.load_contenu("psychologie")
        assert result == []

    def test_fichier_vide_retourne_liste_vide(
        self, service: CorpusContentService, corpus_dir: Path
    ):
        """Un fichier YAML vide (None) retourne []."""
        contenu_path = corpus_dir / "psychologie" / "contenu.yaml"
        contenu_path.parent.mkdir(parents=True)
        contenu_path.write_text("", encoding="utf-8")

        result = service.load_contenu("psychologie")
        assert result == []

    def test_cle_contenu_null_retourne_liste_vide(
        self, service: CorpusContentService, corpus_dir: Path
    ):
        """contenu: null retourne []."""
        contenu_path = corpus_dir / "psychologie" / "contenu.yaml"
        contenu_path.parent.mkdir(parents=True)
        contenu_path.write_text("contenu:\n", encoding="utf-8")

        result = service.load_contenu("psychologie")
        assert result == []

    def test_lecture_correcte(
        self, service: CorpusContentService, corpus_dir: Path
    ):
        """Lecture d'un contenu.yaml valide avec plusieurs entrées."""
        items = [
            {
                "nom": "documents/rapport.pdf",
                "description": "Rapport annuel",
                "type": "document",
                "date_ajout": "2025-07-14",
            },
            {
                "nom": "documents/guide.pdf",
                "description": "Guide pratique",
                "type": "template",
                "date_ajout": "2025-06-01",
            },
        ]
        contenu_path = corpus_dir / "psychologie" / "contenu.yaml"
        contenu_path.parent.mkdir(parents=True)
        with open(contenu_path, "w", encoding="utf-8") as f:
            yaml.dump({"contenu": items}, f, allow_unicode=True)

        result = service.load_contenu("psychologie")
        assert len(result) == 2
        assert result[0]["nom"] == "documents/rapport.pdf"
        assert result[1]["type"] == "template"

    def test_yaml_malformed_leve_valueerror(
        self, service: CorpusContentService, corpus_dir: Path
    ):
        """Un YAML malformé lève ValueError."""
        contenu_path = corpus_dir / "psychologie" / "contenu.yaml"
        contenu_path.parent.mkdir(parents=True)
        contenu_path.write_text("contenu:\n  - [invalid yaml\n    broken", encoding="utf-8")

        with pytest.raises(ValueError, match="Erreur de parsing YAML"):
            service.load_contenu("psychologie")

    def test_cle_contenu_absente_leve_valueerror(
        self, service: CorpusContentService, corpus_dir: Path
    ):
        """Un YAML sans clé 'contenu' lève ValueError."""
        contenu_path = corpus_dir / "psychologie" / "contenu.yaml"
        contenu_path.parent.mkdir(parents=True)
        contenu_path.write_text("autre_cle: valeur\n", encoding="utf-8")

        with pytest.raises(ValueError, match="clé 'contenu'"):
            service.load_contenu("psychologie")

    def test_cle_contenu_pas_une_liste_leve_valueerror(
        self, service: CorpusContentService, corpus_dir: Path
    ):
        """contenu: 'string' lève ValueError."""
        contenu_path = corpus_dir / "psychologie" / "contenu.yaml"
        contenu_path.parent.mkdir(parents=True)
        contenu_path.write_text("contenu: pas_une_liste\n", encoding="utf-8")

        with pytest.raises(ValueError, match="doit contenir une liste"):
            service.load_contenu("psychologie")


# ---------------------------------------------------------------------------
# load_urls
# ---------------------------------------------------------------------------


class TestLoadUrls:
    """Tests pour la lecture de urls/urls.yaml."""

    def test_fichier_absent_retourne_liste_vide(self, service: CorpusContentService):
        """Si urls.yaml n'existe pas, retourne []."""
        result = service.load_urls("psychologie")
        assert result == []

    def test_fichier_vide_retourne_liste_vide(
        self, service: CorpusContentService, corpus_dir: Path
    ):
        """Un fichier YAML vide retourne []."""
        urls_path = corpus_dir / "psychologie" / "urls" / "urls.yaml"
        urls_path.parent.mkdir(parents=True)
        urls_path.write_text("", encoding="utf-8")

        result = service.load_urls("psychologie")
        assert result == []

    def test_cle_urls_null_retourne_liste_vide(
        self, service: CorpusContentService, corpus_dir: Path
    ):
        """urls: null retourne []."""
        urls_path = corpus_dir / "psychologie" / "urls" / "urls.yaml"
        urls_path.parent.mkdir(parents=True)
        urls_path.write_text("urls:\n", encoding="utf-8")

        result = service.load_urls("psychologie")
        assert result == []

    def test_lecture_correcte(
        self, service: CorpusContentService, corpus_dir: Path
    ):
        """Lecture d'un urls.yaml valide avec plusieurs entrées."""
        items = [
            {
                "nom": "Legifrance",
                "url": "https://www.legifrance.gouv.fr",
                "description": "Portail juridique",
                "type": "institutionnel",
                "date_ajout": "2025-07-14",
            },
            {
                "nom": "Guide PDF",
                "url": "https://example.com/guide.pdf",
                "description": "Guide externe",
                "type": "pdf_externe",
                "date_ajout": "2025-06-01",
            },
        ]
        urls_path = corpus_dir / "psychologie" / "urls" / "urls.yaml"
        urls_path.parent.mkdir(parents=True)
        with open(urls_path, "w", encoding="utf-8") as f:
            yaml.dump({"urls": items}, f, allow_unicode=True)

        result = service.load_urls("psychologie")
        assert len(result) == 2
        assert result[0]["nom"] == "Legifrance"
        assert result[1]["type"] == "pdf_externe"

    def test_yaml_malformed_leve_valueerror(
        self, service: CorpusContentService, corpus_dir: Path
    ):
        """Un YAML malformé lève ValueError."""
        urls_path = corpus_dir / "psychologie" / "urls" / "urls.yaml"
        urls_path.parent.mkdir(parents=True)
        urls_path.write_text("urls:\n  - [invalid yaml\n    broken", encoding="utf-8")

        with pytest.raises(ValueError, match="Erreur de parsing YAML"):
            service.load_urls("psychologie")

    def test_cle_urls_absente_leve_valueerror(
        self, service: CorpusContentService, corpus_dir: Path
    ):
        """Un YAML sans clé 'urls' lève ValueError."""
        urls_path = corpus_dir / "psychologie" / "urls" / "urls.yaml"
        urls_path.parent.mkdir(parents=True)
        urls_path.write_text("autre_cle: valeur\n", encoding="utf-8")

        with pytest.raises(ValueError, match="clé 'urls'"):
            service.load_urls("psychologie")

    def test_cle_urls_pas_une_liste_leve_valueerror(
        self, service: CorpusContentService, corpus_dir: Path
    ):
        """urls: 'string' lève ValueError."""
        urls_path = corpus_dir / "psychologie" / "urls" / "urls.yaml"
        urls_path.parent.mkdir(parents=True)
        urls_path.write_text("urls: pas_une_liste\n", encoding="utf-8")

        with pytest.raises(ValueError, match="doit contenir une liste"):
            service.load_urls("psychologie")


# ---------------------------------------------------------------------------
# save_pdf
# ---------------------------------------------------------------------------


class TestSavePdf:
    """Tests pour l'enregistrement de fichiers PDF."""

    def test_save_pdf_cree_fichier_et_met_a_jour_yaml(
        self, service: CorpusContentService, corpus_dir: Path
    ):
        """save_pdf crée le fichier sur disque et ajoute l'entrée dans contenu.yaml."""
        content = b"%PDF-1.4 fake content"
        result = service.save_pdf("psychologie", "rapport.pdf", content)

        # Fichier PDF créé
        pdf_path = corpus_dir / "psychologie" / "documents" / "rapport.pdf"
        assert pdf_path.exists()
        assert pdf_path.read_bytes() == content

        # Entrée retournée correcte
        assert result["nom"] == "documents/rapport.pdf"
        assert result["type"] == "document"
        assert result["date_ajout"] == date.today().isoformat()

        # contenu.yaml mis à jour
        contenu_path = corpus_dir / "psychologie" / "contenu.yaml"
        assert contenu_path.exists()
        with open(contenu_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert len(data["contenu"]) == 1
        assert data["contenu"][0]["nom"] == "documents/rapport.pdf"

    def test_save_pdf_doublon_leve_fileexistserror(
        self, service: CorpusContentService, corpus_dir: Path
    ):
        """save_pdf lève FileExistsError si le fichier existe déjà."""
        docs_dir = corpus_dir / "psychologie" / "documents"
        docs_dir.mkdir(parents=True)
        (docs_dir / "existing.pdf").write_bytes(b"%PDF-1.4 old")

        with pytest.raises(FileExistsError, match="existe déjà"):
            service.save_pdf("psychologie", "existing.pdf", b"%PDF-1.4 new")

    def test_save_pdf_cree_repertoire_documents(
        self, service: CorpusContentService, corpus_dir: Path
    ):
        """save_pdf crée le répertoire documents/ s'il n'existe pas."""
        docs_dir = corpus_dir / "psychologie" / "documents"
        assert not docs_dir.exists()

        service.save_pdf("psychologie", "test.pdf", b"%PDF-1.4")

        assert docs_dir.exists()
        assert (docs_dir / "test.pdf").exists()

    def test_save_pdf_preserve_contenu_existant(
        self, service: CorpusContentService, corpus_dir: Path
    ):
        """save_pdf préserve les entrées existantes dans contenu.yaml."""
        existing_items = [
            {
                "nom": "documents/ancien.pdf",
                "description": "Ancien doc",
                "type": "document",
                "date_ajout": "2025-01-01",
            }
        ]
        contenu_path = corpus_dir / "psychologie" / "contenu.yaml"
        contenu_path.parent.mkdir(parents=True)
        with open(contenu_path, "w", encoding="utf-8") as f:
            yaml.dump({"contenu": existing_items}, f, allow_unicode=True)

        service.save_pdf("psychologie", "nouveau.pdf", b"%PDF-1.4")

        with open(contenu_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert len(data["contenu"]) == 2
        assert data["contenu"][0]["nom"] == "documents/ancien.pdf"
        assert data["contenu"][1]["nom"] == "documents/nouveau.pdf"

    def test_save_pdf_contenu_yaml_malformed_leve_valueerror(
        self, service: CorpusContentService, corpus_dir: Path
    ):
        """save_pdf lève ValueError si contenu.yaml existant est malformé."""
        contenu_path = corpus_dir / "psychologie" / "contenu.yaml"
        contenu_path.parent.mkdir(parents=True)
        contenu_path.write_text("contenu:\n  - [broken yaml", encoding="utf-8")

        with pytest.raises(ValueError, match="Erreur de parsing YAML"):
            service.save_pdf("psychologie", "test.pdf", b"%PDF-1.4")


# ---------------------------------------------------------------------------
# add_url
# ---------------------------------------------------------------------------


class TestAddUrl:
    """Tests pour l'ajout d'URLs dans urls.yaml."""

    def test_add_url_cree_fichier_et_ajoute_entree(
        self, service: CorpusContentService, corpus_dir: Path
    ):
        """add_url crée urls.yaml et ajoute l'entrée avec date_ajout."""
        entry = {
            "nom": "Legifrance",
            "url": "https://www.legifrance.gouv.fr",
            "description": "Portail juridique",
            "type": "site_web",
        }
        result = service.add_url("psychologie", entry)

        # Entrée retournée avec date_ajout
        assert result["nom"] == "Legifrance"
        assert result["url"] == "https://www.legifrance.gouv.fr"
        assert result["type"] == "site_web"
        assert result["date_ajout"] == date.today().isoformat()

        # Fichier urls.yaml créé et contient l'entrée
        urls_path = corpus_dir / "psychologie" / "urls" / "urls.yaml"
        assert urls_path.exists()
        with open(urls_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert len(data["urls"]) == 1
        assert data["urls"][0]["nom"] == "Legifrance"

    def test_add_url_preserve_urls_existantes(
        self, service: CorpusContentService, corpus_dir: Path
    ):
        """add_url préserve les entrées existantes dans urls.yaml."""
        existing_items = [
            {
                "nom": "Ancien site",
                "url": "https://ancien.example.com",
                "description": "Site ancien",
                "type": "institutionnel",
                "date_ajout": "2025-01-01",
            }
        ]
        urls_path = corpus_dir / "psychologie" / "urls" / "urls.yaml"
        urls_path.parent.mkdir(parents=True)
        with open(urls_path, "w", encoding="utf-8") as f:
            yaml.dump({"urls": existing_items}, f, allow_unicode=True)

        entry = {
            "nom": "Nouveau site",
            "url": "https://nouveau.example.com",
            "description": "Site nouveau",
            "type": "pdf_externe",
        }
        service.add_url("psychologie", entry)

        with open(urls_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert len(data["urls"]) == 2
        assert data["urls"][0]["nom"] == "Ancien site"
        assert data["urls"][1]["nom"] == "Nouveau site"

    def test_add_url_cree_repertoire_urls(
        self, service: CorpusContentService, corpus_dir: Path
    ):
        """add_url crée le répertoire urls/ s'il n'existe pas."""
        urls_dir = corpus_dir / "psychologie" / "urls"
        assert not urls_dir.exists()

        entry = {
            "nom": "Test",
            "url": "https://test.com",
            "description": "Test",
            "type": "site_web",
        }
        service.add_url("psychologie", entry)

        assert urls_dir.exists()
        assert (urls_dir / "urls.yaml").exists()

    def test_add_url_ne_modifie_pas_entree_originale(
        self, service: CorpusContentService, corpus_dir: Path
    ):
        """add_url ne modifie pas le dict d'entrée passé en paramètre."""
        entry = {
            "nom": "Test",
            "url": "https://test.com",
            "description": "Test",
            "type": "site_web",
        }
        original_keys = set(entry.keys())

        service.add_url("psychologie", entry)

        # L'entrée originale ne doit pas avoir date_ajout ajouté
        assert set(entry.keys()) == original_keys

    def test_add_url_yaml_malformed_leve_valueerror(
        self, service: CorpusContentService, corpus_dir: Path
    ):
        """add_url lève ValueError si urls.yaml existant est malformé."""
        urls_path = corpus_dir / "psychologie" / "urls" / "urls.yaml"
        urls_path.parent.mkdir(parents=True)
        urls_path.write_text("urls:\n  - [broken yaml", encoding="utf-8")

        entry = {
            "nom": "Test",
            "url": "https://test.com",
            "description": "Test",
            "type": "site_web",
        }
        with pytest.raises(ValueError, match="Erreur de parsing YAML"):
            service.add_url("psychologie", entry)
