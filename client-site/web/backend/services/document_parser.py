"""
Judi-Expert — Service de parsing documentaire.

Parse les fichiers .docx, .txt et .md en préservant la structure XML
et les références aux éléments pour modification ultérieure par le
TrackChangesGenerator.

Valide : Exigences 2.2, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 7.2, 7.5
"""

from __future__ import annotations

import io
import logging
import zipfile
from copy import deepcopy
from typing import Union

from lxml import etree

from services.revision_models import (
    DocumentParseError,
    ParagraphInfo,
    ParsedDocument,
    RunInfo,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes OOXML
# ---------------------------------------------------------------------------

WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NSMAP = {"w": WORD_NS}


def _qn(tag: str) -> str:
    """Construit un nom qualifié Clark notation pour le namespace w:."""
    return f"{{{WORD_NS}}}{tag}"


# ---------------------------------------------------------------------------
# DocumentParser
# ---------------------------------------------------------------------------


class DocumentParser:
    """Parse un fichier (.docx, .txt, .md) en préservant la structure.

    Pour les fichiers .docx, extrait les paragraphes avec leurs runs et
    conserve les références aux éléments XML pour modification in-place.
    Pour les fichiers .txt et .md, retourne le contenu textuel brut.
    """

    def parse(self, file_bytes: bytes, file_ext: str) -> Union[ParsedDocument, str]:
        """Parse un fichier selon son extension.

        Args:
            file_bytes: Contenu brut du fichier.
            file_ext: Extension du fichier (avec ou sans point).

        Returns:
            ParsedDocument pour .docx, str pour .txt/.md.

        Raises:
            DocumentParseError: Fichier invalide ou illisible.
        """
        ext = file_ext.lower().lstrip(".")

        if ext == "docx":
            return self._parse_docx(file_bytes)
        elif ext == "txt":
            return self._parse_text(file_bytes)
        elif ext == "md":
            return self._parse_markdown(file_bytes)
        else:
            raise DocumentParseError(
                f"Format non supporté : .{ext}. "
                "Formats acceptés : .docx, .txt, .md"
            )

    # ------------------------------------------------------------------
    # Parsing .docx
    # ------------------------------------------------------------------

    def _parse_docx(self, file_bytes: bytes) -> ParsedDocument:
        """Parse un fichier .docx en extrayant paragraphes et runs.

        Valide que le fichier est un ZIP contenant word/document.xml,
        puis extrait les paragraphes du body principal et des tables.

        Args:
            file_bytes: Contenu brut du fichier .docx.

        Returns:
            ParsedDocument avec paragraphes, XML racine et archive.

        Raises:
            DocumentParseError: Fichier non-ZIP ou sans word/document.xml.
        """
        # Validation : doit être un ZIP valide
        if not zipfile.is_zipfile(io.BytesIO(file_bytes)):
            raise DocumentParseError(
                "Le fichier n'est pas un fichier .docx valide "
                "(archive ZIP invalide)."
            )

        try:
            package = zipfile.ZipFile(io.BytesIO(file_bytes), "r")
        except zipfile.BadZipFile as exc:
            raise DocumentParseError(
                f"Le fichier .docx est corrompu : {exc}"
            ) from exc

        # Validation : doit contenir word/document.xml
        if "word/document.xml" not in package.namelist():
            package.close()
            raise DocumentParseError(
                "Le fichier ZIP ne contient pas word/document.xml. "
                "Ce n'est pas un fichier .docx valide."
            )

        # Parser le XML du document principal
        try:
            document_xml_bytes = package.read("word/document.xml")
            document_tree = etree.fromstring(document_xml_bytes)
        except etree.XMLSyntaxError as exc:
            package.close()
            raise DocumentParseError(
                f"Le XML du document est invalide : {exc}"
            ) from exc

        # Extraire les paragraphes du body
        body = document_tree.find(_qn("body"))
        if body is None:
            package.close()
            raise DocumentParseError(
                "Le document ne contient pas d'élément w:body."
            )

        paragraphs: list[ParagraphInfo] = []
        paragraph_index = 0

        # Parcourir les éléments directs du body
        for element in body:
            tag = etree.QName(element.tag).localname

            if tag == "p":
                para_info = self._extract_paragraph(
                    element, paragraph_index, is_in_table=False
                )
                if para_info is not None:
                    paragraphs.append(para_info)
                    paragraph_index += 1

            elif tag == "tbl":
                # Itérer sur les cellules du tableau
                table_paragraphs = self._extract_table_paragraphs(
                    element, paragraph_index
                )
                for para_info in table_paragraphs:
                    paragraphs.append(para_info)
                    paragraph_index += 1

        return ParsedDocument(
            paragraphs=paragraphs,
            document_xml=document_tree,
            package=package,
        )

    def _extract_paragraph(
        self,
        p_element: "etree._Element",
        index: int,
        is_in_table: bool = False,
        table_cell_ref: "etree._Element | None" = None,
    ) -> ParagraphInfo | None:
        """Extrait les informations d'un paragraphe XML (w:p).

        Args:
            p_element: Élément XML w:p.
            index: Index du paragraphe dans le document.
            is_in_table: True si le paragraphe est dans une cellule.
            table_cell_ref: Référence à l'élément w:tc parent.

        Returns:
            ParagraphInfo ou None si le paragraphe est vide sans runs.
        """
        runs: list[RunInfo] = []

        # Extraire les propriétés du paragraphe (w:pPr)
        p_properties = p_element.find(_qn("pPr"))

        # Extraire les runs (w:r)
        for r_element in p_element.findall(_qn("r")):
            run_info = self._extract_run(r_element)
            if run_info is not None:
                runs.append(run_info)

        # Construire le texte complet
        full_text = "".join(run.text for run in runs)

        return ParagraphInfo(
            index=index,
            runs=runs,
            xml_element=p_element,
            properties=p_properties,
            full_text=full_text,
            is_in_table=is_in_table,
            table_cell_ref=table_cell_ref,
        )

    def _extract_run(self, r_element: "etree._Element") -> RunInfo | None:
        """Extrait les informations d'un run XML (w:r).

        Args:
            r_element: Élément XML w:r.

        Returns:
            RunInfo ou None si le run n'a pas de texte.
        """
        # Extraire le texte du run (w:t)
        text_parts: list[str] = []
        for t_element in r_element.findall(_qn("t")):
            if t_element.text:
                text_parts.append(t_element.text)

        text = "".join(text_parts)
        if not text:
            return None

        # Extraire les propriétés du run (w:rPr) — copie profonde
        r_properties = r_element.find(_qn("rPr"))
        properties_copy = deepcopy(r_properties) if r_properties is not None else None

        return RunInfo(
            text=text,
            xml_element=r_element,
            properties=properties_copy,
        )

    def _extract_table_paragraphs(
        self,
        tbl_element: "etree._Element",
        start_index: int,
    ) -> list[ParagraphInfo]:
        """Extrait les paragraphes de toutes les cellules d'un tableau.

        Args:
            tbl_element: Élément XML w:tbl.
            start_index: Index de départ pour la numérotation.

        Returns:
            Liste de ParagraphInfo extraits du tableau.
        """
        paragraphs: list[ParagraphInfo] = []
        current_index = start_index

        # Parcourir les lignes (w:tr)
        for tr_element in tbl_element.findall(_qn("tr")):
            # Parcourir les cellules (w:tc)
            for tc_element in tr_element.findall(_qn("tc")):
                # Parcourir les paragraphes dans la cellule
                for p_element in tc_element.findall(_qn("p")):
                    para_info = self._extract_paragraph(
                        p_element,
                        current_index,
                        is_in_table=True,
                        table_cell_ref=tc_element,
                    )
                    if para_info is not None:
                        paragraphs.append(para_info)
                        current_index += 1

        return paragraphs

    # ------------------------------------------------------------------
    # Parsing .txt
    # ------------------------------------------------------------------

    def _parse_text(self, file_bytes: bytes) -> str:
        """Parse un fichier .txt en texte UTF-8.

        Args:
            file_bytes: Contenu brut du fichier .txt.

        Returns:
            Contenu textuel du fichier.

        Raises:
            DocumentParseError: Si le fichier n'est pas encodé en UTF-8.
        """
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DocumentParseError(
                "Le fichier .txt ne peut pas être lu : "
                "l'encodage n'est pas UTF-8 valide."
            ) from exc

    # ------------------------------------------------------------------
    # Parsing .md
    # ------------------------------------------------------------------

    def _parse_markdown(self, file_bytes: bytes) -> str:
        """Parse un fichier .md en texte UTF-8 Markdown.

        Préserve la structure Markdown (titres, listes, code blocks, etc.)
        sans transformation.

        Args:
            file_bytes: Contenu brut du fichier .md.

        Returns:
            Contenu Markdown du fichier.

        Raises:
            DocumentParseError: Si le fichier n'est pas encodé en UTF-8.
        """
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DocumentParseError(
                "Le fichier .md ne peut pas être lu : "
                "l'encodage n'est pas UTF-8 valide."
            ) from exc
