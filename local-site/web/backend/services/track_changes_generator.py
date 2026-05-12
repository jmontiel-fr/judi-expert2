"""
Judi-Expert — Générateur de marques de révision OOXML (Track Changes).

Ce module implémente la génération des éléments w:ins et w:del dans le XML
d'un document .docx, permettant l'affichage natif du suivi des modifications
dans Microsoft Word.

Utilise difflib.SequenceMatcher pour le diff mot-à-mot entre texte original
et texte corrigé, puis injecte les éléments de révision dans l'arbre XML
du document tout en préservant le formatage des runs originaux.

Valide : Exigences 5.1, 5.2, 5.3, 5.4, 5.5
"""

from __future__ import annotations

import difflib
import io
import re
import zipfile
from copy import deepcopy
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from lxml import etree

if TYPE_CHECKING:
    from lxml.etree import _Element as Element

from services.revision_models import (
    ParagraphCorrection,
    ParsedDocument,
)

# ---------------------------------------------------------------------------
# Constantes OOXML
# ---------------------------------------------------------------------------

WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"

NSMAP = {"w": WORD_NS}

# QNames fréquemment utilisés
W_R = f"{{{WORD_NS}}}r"
W_T = f"{{{WORD_NS}}}t"
W_RPR = f"{{{WORD_NS}}}rPr"
W_DEL = f"{{{WORD_NS}}}del"
W_INS = f"{{{WORD_NS}}}ins"
W_DEL_TEXT = f"{{{WORD_NS}}}delText"
W_P = f"{{{WORD_NS}}}p"
W_PPR = f"{{{WORD_NS}}}pPr"


def _qn(tag: str) -> str:
    """Convertit un tag préfixé (ex: 'w:ins') en QName complet."""
    prefix, local = tag.split(":")
    if prefix == "w":
        return f"{{{WORD_NS}}}{local}"
    raise ValueError(f"Préfixe inconnu : {prefix}")


# ---------------------------------------------------------------------------
# Classe principale
# ---------------------------------------------------------------------------


class TrackChangesGenerator:
    """Génère les marques de révision OOXML dans le document.

    Attributes:
        AUTHOR: Nom de l'auteur des révisions dans les métadonnées Word.
    """

    AUTHOR: str = "Judi-Expert"

    def __init__(self) -> None:
        """Initialise le générateur avec un compteur d'ID de révision."""
        self._revision_id: int = 0

    def _next_revision_id(self) -> int:
        """Retourne un ID de révision unique et incrémente le compteur."""
        self._revision_id += 1
        return self._revision_id

    def generate(
        self,
        parsed_doc: ParsedDocument,
        corrections: list[ParagraphCorrection],
    ) -> bytes:
        """Applique les corrections comme track changes dans le XML du document.

        Pour chaque paragraphe corrigé :
        1. Calcule le diff mot-à-mot (difflib.SequenceMatcher)
        2. Remplace les runs originaux par des éléments w:del (suppression)
           et w:ins (insertion) avec les attributs de révision
        3. Préserve le formatage des runs originaux sur les insertions

        Args:
            parsed_doc: Document parsé avec références XML préservées.
            corrections: Liste des corrections par paragraphe.

        Returns:
            Bytes du fichier .docx modifié avec les marques de révision.
        """
        self._revision_id = 0
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Indexer les corrections par index de paragraphe
        corrections_map: dict[int, ParagraphCorrection] = {
            c.paragraph_index: c for c in corrections if c.has_changes
        }

        for para_info in parsed_doc.paragraphs:
            if para_info.index not in corrections_map:
                continue

            correction = corrections_map[para_info.index]
            self._apply_correction_to_paragraph(
                para_info.xml_element,
                para_info,
                correction,
                timestamp,
            )

        # Sérialiser le XML modifié et réécrire le .docx
        return self._repackage_docx(parsed_doc)

    def _apply_correction_to_paragraph(
        self,
        para_element: "Element",
        para_info: "object",
        correction: ParagraphCorrection,
        timestamp: str,
    ) -> None:
        """Applique une correction à un paragraphe en remplaçant ses runs.

        Args:
            para_element: Élément XML w:p du paragraphe.
            para_info: ParagraphInfo avec les runs et propriétés.
            correction: Correction contenant texte original et corrigé.
            timestamp: Horodatage ISO pour les attributs de révision.
        """
        from services.revision_models import ParagraphInfo

        assert isinstance(para_info, ParagraphInfo)

        # Extraire les propriétés de formatage du premier run (fallback)
        run_properties = self._get_dominant_run_properties(para_info)

        # Calculer le diff mot-à-mot
        original_words = self._tokenize(correction.original_text)
        corrected_words = self._tokenize(correction.corrected_text)

        matcher = difflib.SequenceMatcher(
            None, original_words, corrected_words
        )
        opcodes = matcher.get_opcodes()

        # Construire les nouveaux éléments enfants du paragraphe
        new_children: list["Element"] = []

        # Préserver w:pPr s'il existe
        ppr = para_element.find(W_PPR)
        if ppr is not None:
            new_children.append(deepcopy(ppr))

        for tag, i1, i2, j1, j2 in opcodes:
            if tag == "equal":
                # Texte inchangé → run normal
                text = self._join_tokens(original_words[i1:i2])
                if text:
                    new_children.append(
                        self._create_run_element(text, run_properties)
                    )
            elif tag == "delete":
                # Texte supprimé → w:del
                text = self._join_tokens(original_words[i1:i2])
                if text:
                    new_children.append(
                        self._create_revision_element(
                            "w:del", text, run_properties, timestamp
                        )
                    )
            elif tag == "insert":
                # Texte inséré → w:ins
                text = self._join_tokens(corrected_words[j1:j2])
                if text:
                    new_children.append(
                        self._create_revision_element(
                            "w:ins", text, run_properties, timestamp
                        )
                    )
            elif tag == "replace":
                # Remplacement → w:del + w:ins
                del_text = self._join_tokens(original_words[i1:i2])
                ins_text = self._join_tokens(corrected_words[j1:j2])
                if del_text:
                    new_children.append(
                        self._create_revision_element(
                            "w:del", del_text, run_properties, timestamp
                        )
                    )
                if ins_text:
                    new_children.append(
                        self._create_revision_element(
                            "w:ins", ins_text, run_properties, timestamp
                        )
                    )

        # Remplacer le contenu du paragraphe
        # Supprimer tous les enfants existants
        for child in list(para_element):
            para_element.remove(child)

        # Ajouter les nouveaux enfants
        for child in new_children:
            para_element.append(child)

    def _get_dominant_run_properties(
        self, para_info: "object"
    ) -> "Element | None":
        """Récupère les propriétés de formatage dominantes du paragraphe.

        Utilise les propriétés du premier run non-vide comme référence.

        Args:
            para_info: ParagraphInfo contenant les runs.

        Returns:
            Copie profonde de l'élément w:rPr ou None si aucun formatage.
        """
        from services.revision_models import ParagraphInfo

        assert isinstance(para_info, ParagraphInfo)

        for run in para_info.runs:
            if run.properties is not None:
                return deepcopy(run.properties)
        return None

    def _create_revision_element(
        self,
        tag: str,
        text: str,
        run_properties: "Element | None",
        timestamp: str,
    ) -> "Element":
        """Crée un élément XML de révision OOXML (w:ins ou w:del).

        Args:
            tag: Type d'élément ("w:ins" ou "w:del").
            text: Contenu textuel de l'élément.
            run_properties: Propriétés de formatage à préserver ou None.
            timestamp: Horodatage ISO pour l'attribut w:date.

        Returns:
            Élément XML w:ins ou w:del complet avec run enfant.
        """
        revision_id = self._next_revision_id()

        # Créer l'élément de révision (w:ins ou w:del)
        rev_element = etree.Element(_qn(tag), nsmap=NSMAP)
        rev_element.set(_qn("w:id"), str(revision_id))
        rev_element.set(_qn("w:author"), self.AUTHOR)
        rev_element.set(_qn("w:date"), timestamp)

        # Créer le run enfant (w:r)
        run_elem = etree.SubElement(rev_element, W_R, nsmap=NSMAP)

        # Ajouter les propriétés de formatage si présentes
        if run_properties is not None:
            run_elem.append(deepcopy(run_properties))

        # Ajouter le texte (w:delText pour suppression, w:t pour insertion)
        if tag == "w:del":
            text_elem = etree.SubElement(run_elem, W_DEL_TEXT, nsmap=NSMAP)
        else:
            text_elem = etree.SubElement(run_elem, W_T, nsmap=NSMAP)

        text_elem.set(f"{{{XML_NS}}}space", "preserve")
        text_elem.text = text

        return rev_element

    def _create_run_element(
        self, text: str, run_properties: "Element | None"
    ) -> "Element":
        """Crée un élément w:r normal (texte inchangé).

        Args:
            text: Contenu textuel du run.
            run_properties: Propriétés de formatage ou None.

        Returns:
            Élément XML w:r avec texte.
        """
        run_elem = etree.Element(W_R, nsmap=NSMAP)

        if run_properties is not None:
            run_elem.append(deepcopy(run_properties))

        text_elem = etree.SubElement(run_elem, W_T, nsmap=NSMAP)
        text_elem.set(f"{{{XML_NS}}}space", "preserve")
        text_elem.text = text

        return run_elem

    def _tokenize(self, text: str) -> list[str]:
        """Découpe le texte en tokens (mots + espaces/ponctuation).

        Utilise une tokenisation qui préserve les espaces comme tokens
        séparés pour un diff plus précis.

        Args:
            text: Texte à tokeniser.

        Returns:
            Liste de tokens (mots et séparateurs).
        """
        # Sépare en mots tout en gardant les espaces comme séparateurs
        # Chaque token est soit un mot, soit un espace/ponctuation
        tokens = re.findall(r"\S+|\s+", text)
        return tokens

    def _join_tokens(self, tokens: list[str]) -> str:
        """Rejoint une liste de tokens en texte.

        Args:
            tokens: Liste de tokens à joindre.

        Returns:
            Texte reconstitué.
        """
        return "".join(tokens)

    def _repackage_docx(self, parsed_doc: ParsedDocument) -> bytes:
        """Sérialise le XML modifié et reconstruit l'archive .docx.

        Lit l'archive originale, remplace word/document.xml par le XML
        modifié, et écrit le tout dans un nouveau buffer en mémoire.

        Args:
            parsed_doc: Document parsé contenant le XML modifié et le package.

        Returns:
            Bytes du fichier .docx reconstruit.
        """
        # Sérialiser le XML modifié
        xml_content = etree.tostring(
            parsed_doc.document_xml,
            xml_declaration=True,
            encoding="UTF-8",
            standalone=True,
        )

        # Créer un nouveau ZIP en mémoire
        output_buffer = io.BytesIO()

        with zipfile.ZipFile(output_buffer, "w", zipfile.ZIP_DEFLATED) as out_zip:
            # Copier tous les fichiers de l'archive originale sauf document.xml
            for item in parsed_doc.package.infolist():
                if item.filename == "word/document.xml":
                    # Remplacer par notre XML modifié
                    out_zip.writestr(item, xml_content)
                else:
                    # Copier tel quel
                    out_zip.writestr(item, parsed_doc.package.read(item.filename))

        return output_buffer.getvalue()
