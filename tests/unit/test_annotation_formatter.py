"""Tests unitaires pour l'AnnotationFormatter.

Teste le formatage des annotations PEA (dires, analyse, verbatim, custom)
et la résolution des références/citations via l'index de sections.
"""

import sys
from pathlib import Path

import pytest

# Ajouter le backend au path
sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "local-site" / "web" / "backend")
)

from services.annotation_formatter import AnnotationFormatter, SectionIndex


# ---------------------------------------------------------------------------
# Tests : Formatage @dires
# ---------------------------------------------------------------------------


class TestFormatDires:
    """Vérifie le formatage des annotations @dires."""

    def test_format_dires(self):
        """@dires produit 'Dires : contenu'."""
        formatter = AnnotationFormatter()

        result = formatter.format_dires("Le patient déclare souffrir de maux de tête.")

        assert result == "Dires : Le patient déclare souffrir de maux de tête."

    def test_format_dires_strips_whitespace(self):
        """@dires supprime les espaces en début/fin de contenu."""
        formatter = AnnotationFormatter()

        result = formatter.format_dires("  contenu avec espaces  ")

        assert result == "Dires : contenu avec espaces"


# ---------------------------------------------------------------------------
# Tests : Formatage @analyse
# ---------------------------------------------------------------------------


class TestFormatAnalyse:
    """Vérifie le formatage des annotations @analyse."""

    def test_format_analyse(self):
        """@analyse produit 'Analyse : contenu'."""
        formatter = AnnotationFormatter()

        result = formatter.format_analyse("Les symptômes sont cohérents avec le diagnostic.")

        assert result == "Analyse : Les symptômes sont cohérents avec le diagnostic."

    def test_format_analyse_strips_whitespace(self):
        """@analyse supprime les espaces en début/fin de contenu."""
        formatter = AnnotationFormatter()

        result = formatter.format_analyse("  analyse avec espaces  ")

        assert result == "Analyse : analyse avec espaces"


# ---------------------------------------------------------------------------
# Tests : Formatage @verbatim
# ---------------------------------------------------------------------------


class TestFormatVerbatim:
    """Vérifie le formatage des annotations @verbatim."""

    def test_format_verbatim_adds_quotes(self):
        """@verbatim ajoute des guillemets au texte non-quoté."""
        formatter = AnnotationFormatter()

        result = formatter.format_verbatim("texte sans guillemets")

        assert result == '"texte sans guillemets"'

    def test_format_verbatim_preserves_quotes(self):
        """@verbatim préserve les guillemets existants."""
        formatter = AnnotationFormatter()

        result = formatter.format_verbatim('"texte déjà entre guillemets"')

        assert result == '"texte déjà entre guillemets"'

    def test_format_verbatim_strips_whitespace_before_quoting(self):
        """@verbatim supprime les espaces avant d'ajouter les guillemets."""
        formatter = AnnotationFormatter()

        result = formatter.format_verbatim("  texte avec espaces  ")

        assert result == '"texte avec espaces"'


# ---------------------------------------------------------------------------
# Tests : Formatage @/custom
# ---------------------------------------------------------------------------


class TestFormatCustom:
    """Vérifie le formatage des annotations personnalisées."""

    def test_format_custom_capitalizes(self):
        """@/mon_annotation → 'Mon Annotation : contenu'."""
        formatter = AnnotationFormatter()

        result = formatter.format_custom("/mon_annotation", "contenu personnalisé")

        assert result == "Mon Annotation : contenu personnalisé"

    def test_format_custom_without_slash(self):
        """Un nom sans slash est aussi correctement formaté."""
        formatter = AnnotationFormatter()

        result = formatter.format_custom("observation_clinique", "le patient est calme")

        assert result == "Observation Clinique : le patient est calme"

    def test_format_custom_single_word(self):
        """Un nom personnalisé d'un seul mot est capitalisé."""
        formatter = AnnotationFormatter()

        result = formatter.format_custom("/remarque", "contenu")

        assert result == "Remarque : contenu"


# ---------------------------------------------------------------------------
# Tests : Résolution de référence
# ---------------------------------------------------------------------------


class TestResolveReference:
    """Vérifie la résolution des annotations @reference."""

    def test_resolve_reference_found(self):
        """Une référence existante produit 'cf section X.Y.Z - titre'."""
        formatter = AnnotationFormatter()
        sections = {
            "dires_2.1.3": SectionIndex(
                number="2.1.3",
                title="biographie/education/primaire",
                content="Contenu de la section.",
            ),
        }

        result = formatter.resolve_reference("dires_2.1.3", sections)

        assert result == "cf section 2.1.3 - biographie/education/primaire"

    def test_resolve_reference_not_found(self):
        """Une référence inexistante produit un message d'erreur."""
        formatter = AnnotationFormatter()
        sections: dict[str, SectionIndex] = {}

        result = formatter.resolve_reference("dires_9.9.9", sections)

        assert "Référence non trouvée" in result
        assert "dires_9.9.9" in result


# ---------------------------------------------------------------------------
# Tests : Résolution de citation
# ---------------------------------------------------------------------------


class TestResolveCite:
    """Vérifie la résolution des annotations @cite."""

    def test_resolve_cite_found(self):
        """Une citation existante produit le format attendu."""
        formatter = AnnotationFormatter()
        sections = {
            "dires_1.2": SectionIndex(
                number="1.2",
                title="antécédents médicaux",
                content="Le patient a été hospitalisé en 2020.",
            ),
        }

        result = formatter.resolve_cite("dires_1.2", sections)

        assert "citation section 1.2" in result
        assert "antécédents médicaux" in result
        assert "Le patient a été hospitalisé en 2020." in result

    def test_resolve_cite_not_found(self):
        """Une citation inexistante produit un message d'erreur."""
        formatter = AnnotationFormatter()
        sections: dict[str, SectionIndex] = {}

        result = formatter.resolve_cite("analyse_5.1", sections)

        assert "Citation non trouvée" in result
        assert "analyse_5.1" in result

    def test_resolve_cite_truncates_long_content(self):
        """Une citation avec contenu > 200 chars est tronquée."""
        formatter = AnnotationFormatter()
        long_content = "A" * 300
        sections = {
            "dires_1.1": SectionIndex(
                number="1.1",
                title="section longue",
                content=long_content,
            ),
        }

        result = formatter.resolve_cite("dires_1.1", sections)

        # Le contenu est tronqué à 200 chars + "…"
        assert "…" in result
        assert len(result) < 300


# ---------------------------------------------------------------------------
# Tests : Construction de l'index de sections
# ---------------------------------------------------------------------------


class TestBuildSectionIndex:
    """Vérifie la construction de l'index de sections."""

    def test_build_section_index(self):
        """L'index est construit avec la numérotation correcte."""
        formatter = AnnotationFormatter()
        headings = [
            (1, "Introduction", "Contenu intro"),
            (1, "Biographie", "Contenu bio"),
            (2, "Enfance", "Contenu enfance"),
            (2, "Adolescence", "Contenu ado"),
            (1, "Analyse", "Contenu analyse"),
        ]

        sections = formatter.build_section_index(headings)

        # Vérifier la numérotation
        assert "1" in sections  # Introduction
        assert sections["1"].title == "introduction"
        assert sections["1"].number == "1"

        assert "2" in sections  # Biographie
        assert sections["2"].title == "biographie"

        assert "2.1" in sections  # Enfance
        assert sections["2.1"].title == "enfance"

        assert "2.2" in sections  # Adolescence
        assert sections["2.2"].title == "adolescence"

        assert "3" in sections  # Analyse
        assert sections["3"].title == "analyse"

    def test_build_section_index_registers_dires_keys(self):
        """L'index enregistre les clés dires_X et analyse_X."""
        formatter = AnnotationFormatter()
        headings = [
            (1, "Section Un", "Contenu"),
        ]

        sections = formatter.build_section_index(headings)

        # Les clés dires_ et analyse_ sont enregistrées
        assert "dires_1" in sections
        assert "analyse_1" in sections
        assert sections["dires_1"].number == "1"

    def test_build_section_index_empty_headings(self):
        """Une liste vide de headings produit un index vide."""
        formatter = AnnotationFormatter()

        sections = formatter.build_section_index([])

        assert sections == {}
