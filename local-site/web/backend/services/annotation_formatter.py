"""Service de formatage des annotations PEA pour le PRE.

Transforme les annotations balisées (@dires, @analyse, @verbatim, etc.)
en texte rédigé pour le pré-rapport d'expertise.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class SectionIndex:
    """Index d'une section du rapport avec son numéro et titre."""

    number: str  # "2.1.3"
    title: str  # "biographie/education/primaire"
    content: str  # textual content of the section


class AnnotationFormatter:
    """Formate les annotations PEA en texte pour le PRE."""

    def format_dires(self, content: str) -> str:
        """Formate @dires → 'Dires : contenu'"""
        return f"Dires : {content.strip()}"

    def format_analyse(self, content: str) -> str:
        """Formate @analyse → 'Analyse : contenu'"""
        return f"Analyse : {content.strip()}"

    def format_verbatim(self, content: str) -> str:
        """Formate @verbatim → '"contenu"' (sans modification)"""
        text = content.strip()
        # If already quoted, keep as-is
        if text.startswith('"') and text.endswith('"'):
            return text
        return f'"{text}"'

    def format_custom(self, annotation_name: str, content: str) -> str:
        """Formate @/custom → 'Custom : contenu'

        Capitalizes the annotation name and replaces underscores with spaces.
        """
        # Remove leading slash if present
        name = annotation_name.lstrip("/")
        # Replace underscores with spaces and capitalize each word
        formatted_name = name.replace("_", " ").title()
        return f"{formatted_name} : {content.strip()}"

    def resolve_reference(
        self, ref: str, sections: dict[str, SectionIndex]
    ) -> str:
        """Résout @reference @dires_x.y.z@ → 'cf section X.Y.Z - titre'

        Args:
            ref: The reference identifier (e.g., "dires_2.1.3")
            sections: Dict mapping section identifiers to SectionIndex

        Returns:
            Formatted reference string or error message if section not found.
        """
        section = sections.get(ref)
        if section is None:
            return f"[Référence non trouvée : {ref}]"
        return f"cf section {section.number} - {section.title}"

    def resolve_cite(
        self, ref: str, sections: dict[str, SectionIndex]
    ) -> str:
        """Résout @cite @dires_x.y.z@ → 'citation section X.Y.Z - titre ... texte'

        Args:
            ref: The citation identifier (e.g., "dires_2.1.3")
            sections: Dict mapping section identifiers to SectionIndex

        Returns:
            Formatted citation string or error message if section not found.
        """
        section = sections.get(ref)
        if section is None:
            return f"[Citation non trouvée : {ref}]"
        # Truncate content if too long for inline citation
        cite_text = section.content.strip()
        if len(cite_text) > 200:
            cite_text = cite_text[:200] + "…"
        return (
            f'citation section {section.number} - {section.title} "{cite_text}"'
        )

    def build_section_index(
        self, headings: list[tuple[int, str, str]]
    ) -> dict[str, SectionIndex]:
        """Construit l'index des sections à partir des headings du document.

        Args:
            headings: List of (level, title, content) tuples from the document.
                     level: heading level (1, 2, 3...)
                     title: heading text
                     content: text content under this heading

        Returns:
            Dict mapping section identifiers to SectionIndex objects.
            Keys are formatted as "type_number" (e.g., "dires_2.1.3")
        """
        sections: dict[str, SectionIndex] = {}
        counters: list[int] = [0] * 10  # Support up to 10 levels

        for level, title, content in headings:
            # Increment counter at this level
            counters[level - 1] += 1
            # Reset all deeper counters
            for i in range(level, len(counters)):
                counters[i] = 0

            # Build section number (e.g., "2.1.3")
            number_parts = [
                str(counters[i]) for i in range(level) if counters[i] > 0
            ]
            number = ".".join(number_parts)

            # Build path title (e.g., "biographie/education/primaire")
            # Use the title as-is for the path
            path_title = title.lower().strip()

            # Create section index entry
            section = SectionIndex(
                number=number,
                title=path_title,
                content=content,
            )

            # Register with multiple keys for lookup
            # Key by number: "2.1.3"
            sections[number] = section
            # Key by "dires_number" and "analyse_number" for annotation references
            sections[f"dires_{number}"] = section
            sections[f"analyse_{number}"] = section

        return sections

    def format_annotation(
        self,
        annotation_type: str,
        suffix: str,
        content: str,
        is_custom: bool,
        sections: dict[str, SectionIndex] | None = None,
    ) -> str:
        """Dispatch formatting based on annotation type.

        Args:
            annotation_type: Type of annotation (dires, analyse, verbatim, etc.)
            suffix: Suffix/identifier (e.g., "fratrie", "2.1.3")
            content: Annotation content
            is_custom: Whether this is a custom annotation (@/...)
            sections: Section index for resolving references/citations

        Returns:
            Formatted text for the PRE.
        """
        if is_custom:
            return self.format_custom(annotation_type, content)

        if annotation_type == "dires":
            return self.format_dires(content)
        elif annotation_type == "analyse":
            return self.format_analyse(content)
        elif annotation_type == "verbatim":
            return self.format_verbatim(content)
        elif annotation_type == "reference":
            if sections is None:
                return f"[Référence : {content}]"
            # Extract the reference target from content
            ref_match = re.match(
                r"@?(dires|analyse)_(.+?)@?", content.strip()
            )
            if ref_match:
                ref_key = f"{ref_match.group(1)}_{ref_match.group(2)}"
                return self.resolve_reference(ref_key, sections)
            return self.resolve_reference(content.strip(), sections)
        elif annotation_type == "cite":
            if sections is None:
                return f"[Citation : {content}]"
            ref_match = re.match(
                r"@?(dires|analyse)_(.+?)@?", content.strip()
            )
            if ref_match:
                ref_key = f"{ref_match.group(1)}_{ref_match.group(2)}"
                return self.resolve_cite(ref_key, sections)
            return self.resolve_cite(content.strip(), sections)
        elif annotation_type == "question":
            # @question n@ — just return the question number reference
            return f"Question {content.strip()}"
        else:
            # Unknown type — format as custom
            return self.format_custom(annotation_type, content)
