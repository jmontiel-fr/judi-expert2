"""Tests unitaires pour les méthodes helper du RevisionService (TRE-centric).

Teste _extract_verbatim, _restore_verbatim et _identify_corrections
sans appeler le LLM.
"""

import sys
from pathlib import Path

import pytest

# Ajouter le backend au path
sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "local-site" / "web" / "backend")
)

from services.revision_service import Correction, RevisionService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service() -> RevisionService:
    """Crée un RevisionService sans dépendance LLM (pour tester les helpers)."""
    return RevisionService.__new__(RevisionService)


# ---------------------------------------------------------------------------
# Tests : _extract_verbatim
# ---------------------------------------------------------------------------


class TestExtractVerbatim:
    """Vérifie que _extract_verbatim remplace les textes quotés par des tokens."""

    def test_extract_verbatim_replaces_with_tokens(self):
        """Les textes entre guillemets sont remplacés par des tokens."""
        service = _make_service()
        text = 'Le patient déclare "je souffre beaucoup" et ajoute "depuis 2020".'

        tokenized, verbatim_map = service._extract_verbatim(text)

        # Les guillemets originaux ne sont plus dans le texte tokenisé
        assert '"je souffre beaucoup"' not in tokenized
        assert '"depuis 2020"' not in tokenized

        # Les tokens sont présents
        assert "__VERBATIM_001__" in tokenized
        assert "__VERBATIM_002__" in tokenized

        # Le mapping contient les originaux
        assert len(verbatim_map) == 2
        assert '__VERBATIM_001__' in verbatim_map
        assert verbatim_map["__VERBATIM_001__"] == '"je souffre beaucoup"'
        assert verbatim_map["__VERBATIM_002__"] == '"depuis 2020"'

    def test_extract_verbatim_no_quotes(self):
        """Un texte sans guillemets n'est pas modifié."""
        service = _make_service()
        text = "Un texte sans aucun guillemet."

        tokenized, verbatim_map = service._extract_verbatim(text)

        assert tokenized == text
        assert verbatim_map == {}

    def test_extract_verbatim_preserves_surrounding_text(self):
        """Le texte autour des guillemets est préservé."""
        service = _make_service()
        text = 'Avant "contenu" après.'

        tokenized, verbatim_map = service._extract_verbatim(text)

        assert tokenized.startswith("Avant ")
        assert tokenized.endswith(" après.")


# ---------------------------------------------------------------------------
# Tests : _restore_verbatim
# ---------------------------------------------------------------------------


class TestRestoreVerbatim:
    """Vérifie que _restore_verbatim restaure les tokens en texte original."""

    def test_restore_verbatim_restores_tokens(self):
        """Les tokens sont remplacés par les textes originaux."""
        service = _make_service()
        tokenized = "Le patient déclare __VERBATIM_001__ et ajoute __VERBATIM_002__."
        verbatim_map = {
            "__VERBATIM_001__": '"je souffre beaucoup"',
            "__VERBATIM_002__": '"depuis 2020"',
        }

        result = service._restore_verbatim(tokenized, verbatim_map)

        assert result == 'Le patient déclare "je souffre beaucoup" et ajoute "depuis 2020".'

    def test_restore_verbatim_empty_map(self):
        """Un mapping vide ne modifie pas le texte."""
        service = _make_service()
        text = "Texte sans tokens."

        result = service._restore_verbatim(text, {})

        assert result == text

    def test_restore_verbatim_missing_token_unchanged(self):
        """Un token absent du texte ne cause pas d'erreur."""
        service = _make_service()
        text = "Texte sans le token attendu."
        verbatim_map = {"__VERBATIM_001__": '"contenu"'}

        result = service._restore_verbatim(text, verbatim_map)

        assert result == text


# ---------------------------------------------------------------------------
# Tests : Roundtrip extract → restore
# ---------------------------------------------------------------------------


class TestExtractRestoreRoundtrip:
    """Vérifie que extract puis restore redonne le texte original."""

    def test_extract_and_restore_roundtrip(self):
        """extract_verbatim suivi de restore_verbatim = texte original."""
        service = _make_service()
        original = 'Le rapport indique "traumatisme crânien" et "perte de conscience" comme séquelles.'

        tokenized, verbatim_map = service._extract_verbatim(original)
        restored = service._restore_verbatim(tokenized, verbatim_map)

        assert restored == original

    def test_roundtrip_with_multiple_quotes(self):
        """Le roundtrip fonctionne avec plusieurs citations."""
        service = _make_service()
        original = '"Premier" texte "Deuxième" et "Troisième" fin.'

        tokenized, verbatim_map = service._extract_verbatim(original)
        restored = service._restore_verbatim(tokenized, verbatim_map)

        assert restored == original

    def test_roundtrip_no_quotes(self):
        """Le roundtrip sur un texte sans guillemets est un no-op."""
        service = _make_service()
        original = "Texte simple sans guillemets."

        tokenized, verbatim_map = service._extract_verbatim(original)
        restored = service._restore_verbatim(tokenized, verbatim_map)

        assert restored == original


# ---------------------------------------------------------------------------
# Tests : _identify_corrections
# ---------------------------------------------------------------------------


class TestIdentifyCorrections:
    """Vérifie l'identification des corrections par diff mot-à-mot."""

    def test_identify_corrections_finds_changes(self):
        """Les mots modifiés sont identifiés comme corrections."""
        service = _make_service()
        original = "Le patient soufre de maux de tete."
        corrected = "Le patient souffre de maux de tête."

        corrections = service._identify_corrections(original, corrected)

        assert len(corrections) >= 2
        # Vérifier que les corrections contiennent les mots changés
        originals = [c.original for c in corrections]
        correcteds = [c.corrected for c in corrections]
        assert "soufre" in originals
        assert "souffre" in correcteds
        assert "tete." in originals or "tête." in correcteds

    def test_identify_corrections_no_changes(self):
        """Deux textes identiques ne produisent aucune correction."""
        service = _make_service()
        text = "Le patient est en bonne santé."

        corrections = service._identify_corrections(text, text)

        assert corrections == []

    def test_identify_corrections_returns_correction_objects(self):
        """Les corrections retournées sont des objets Correction."""
        service = _make_service()
        original = "Un mot faux ici."
        corrected = "Un mot juste ici."

        corrections = service._identify_corrections(original, corrected)

        assert len(corrections) == 1
        assert isinstance(corrections[0], Correction)
        assert corrections[0].original == "faux"
        assert corrections[0].corrected == "juste"
        assert corrections[0].position >= 0

    def test_identify_corrections_position_increases(self):
        """Les positions des corrections sont croissantes."""
        service = _make_service()
        original = "Le chat noir mange le poisson rouge."
        corrected = "Le chien blanc mange le poisson bleu."

        corrections = service._identify_corrections(original, corrected)

        positions = [c.position for c in corrections]
        assert positions == sorted(positions)
