#!/usr/bin/env python3
"""
Read/write only TRE-Ed3.docx: unpack, apply string-level XML edits, repack.
Does not read or modify any other .docx file in the folder.
"""
from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRE_DOC = HERE / "TRE-Ed3.docx"
WORK = HERE / "_tre_build"
NUM_ID = "10"
ABSTRACT_ID = "9"

NUMBERING_ABSTRACT_ONLY = (
    f'<w:abstractNum w:abstractNumId="{ABSTRACT_ID}">'
    f'<w:nsid w:val="A1B2C3D4"/><w:multiLevelType w:val="multilevel"/>'
    f'<w:tmpl w:val="0409001F"/>'
    + "".join(
        f'<w:lvl w:ilvl="{ilvl}"><w:start w:val="1"/><w:numFmt w:val="decimal"/>'
        f'<w:lvlText w:val="{ ".".join(f"%{j+1}" for j in range(ilvl + 1)) }."/>'
        f'<w:lvlJc w:val="left"/><w:pStyle w:val="Heading{ilvl + 1}"/>'
        # left = hanging: first line starts at margin like Normal; room for long numbers (tab).
        f'<w:pPr><w:tabs><w:tab w:val="num" w:pos="720"/></w:tabs>'
        f'<w:ind w:left="720" w:hanging="720"/></w:pPr></w:lvl>'
        for ilvl in range(9)
    )
    + "</w:abstractNum>"
)
NUMBERING_NUM_INSTANCE = (
    f'<w:num w:numId="{NUM_ID}"><w:abstractNumId w:val="{ABSTRACT_ID}"/></w:num>'
)
NUMBERING_FRAGMENT = NUMBERING_ABSTRACT_ONLY + NUMBERING_NUM_INSTANCE

# fldSimple: Word updates this reliably; quotes in the instruction use &quot; in the attribute.
DOC_TOC = (
    '<w:p><w:pPr><w:pStyle w:val="TOCHeading"/><w:jc w:val="start"/></w:pPr>'
    '<w:r><w:t>Table des matières</w:t></w:r></w:p>'
    '<w:p><w:pPr><w:jc w:val="start"/></w:pPr>'
    r'<w:fldSimple w:instr=" TOC \o &quot;1-3&quot; \h \z \u ">'
    '<w:r><w:t xml:space="preserve"> </w:t></w:r>'
    "</w:fldSimple></w:p><w:p/>"
)

# Earlier builds used a complex field; Word often refused to update it.
TOC_LEGACY_COMPLEX = (
    '<w:p><w:pPr><w:pStyle w:val="TOCHeading"/><w:jc w:val="start"/></w:pPr>'
    '<w:r><w:t>Table des matières</w:t></w:r></w:p>'
    '<w:p><w:pPr><w:jc w:val="start"/></w:pPr>'
    '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
    r'<w:r><w:instrText xml:space="preserve"> TOC \o "1-3" \h \z \u </w:instrText></w:r>'
    '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
    '<w:r><w:t>Clic droit : Mettre à jour le champ.</w:t></w:r>'
    '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p><w:p/>'
)
TOC_LEGACY_COMPLEX_LEFT = TOC_LEGACY_COMPLEX.replace('w:jc w:val="start"', 'w:jc w:val="left"')

DOC_ANCHOR = (
    '<w:p/><w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr>'
    '<w:r><w:t>CADRE DE L\'ENTRETIEN</w:t></w:r></w:p>'
)


def patch_numbering(text: str) -> str:
    if re.search(rf'<w:abstractNum w:abstractNumId="{ABSTRACT_ID}"', text):
        text = re.sub(
            rf'<w:abstractNum w:abstractNumId="{ABSTRACT_ID}">.*?</w:abstractNum>',
            NUMBERING_ABSTRACT_ONLY,
            text,
            count=1,
            flags=re.DOTALL,
        )
        return text
    return text.replace("</w:numbering>", NUMBERING_FRAGMENT + "</w:numbering>")


def patch_styles_xml_min(text: str) -> str:
    if "<w:pPrDefault><w:pPr><w:jc w:val=\"start\"" in text:
        return text
    if "<w:pPrDefault><w:pPr><w:jc w:val=\"left\"" in text:
        return text.replace('w:jc w:val="left"', 'w:jc w:val="start"')
    old = "<w:pPrDefault><w:pPr><w:spacing"
    ins = "<w:pPrDefault><w:pPr><w:jc w:val=\"start\"/><w:spacing"
    if old not in text:
        return text
    return text.replace(old, ins, 1)


def strip_paragraph_style_indents(xml: str) -> str:
    """Remove w:ind from every paragraph style so alignment matches Normal (no extra offset)."""

    def repl(m: re.Match[str]) -> str:
        block = m.group(0)
        return re.sub(r"<w:ind\b[^>]*/>", "", block)

    return re.sub(
        r'<w:style w:type="paragraph"[^>]*>.*?</w:style>',
        repl,
        xml,
        flags=re.DOTALL,
    )


def jc_left_to_start(xml: str) -> str:
    """Normal uses w:jc start; treat left as start for consistency."""
    return xml.replace('w:jc w:val="left"', 'w:jc w:val="start"')


# Word: numId 0 = no list; in style Normal this clears numbering when user applies default style.
NORMAL_CLEAR_NUM = "<w:numPr><w:numId w:val=\"0\"/><w:ilvl w:val=\"0\"/></w:numPr>"


def patch_normal_style_resets_numbering(xml: str) -> str:
    """Ensure Normal paragraph style includes numId 0 so applying Normal drops heading/list numbering."""

    def patch_one_block(start: int, end: int) -> tuple[str, int, int] | None:
        if start == -1 or end == -1:
            return None
        block = xml[start:end]
        if NORMAL_CLEAR_NUM in block:
            return None
        if "<w:pPr>" not in block or "</w:pPr>" not in block:
            return None
        new_block = re.sub(r"<w:numPr>.*?</w:numPr>", "", block, flags=re.DOTALL)
        new_block = new_block.replace("</w:pPr>", NORMAL_CLEAR_NUM + "</w:pPr>", 1)
        return new_block, start, end

    for pat in (
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"',
        '<w:style w:type="paragraph" w:styleId="Normal"',
    ):
        start = xml.find(pat)
        if start != -1:
            end = xml.find("</w:style>", start)
            got = patch_one_block(start, end)
            if got:
                new_block, s, e = got
                xml = xml[:s] + new_block + xml[e:]
            break
    return xml


def patch_styles_xml_headings(text: str) -> str:
    """Word merges styles.xml with stylesWithEffects.xml; Heading pPr must include numPr here too."""
    for i in range(1, 10):
        marker = f'<w:style w:type="paragraph" w:styleId="Heading{i}"'
        start = text.find(marker)
        if start == -1:
            raise SystemExit(f"styles.xml: missing {marker}")
        end = text.find("</w:style>", start)
        if end == -1:
            raise SystemExit("styles.xml: unclosed style")
        block = text[start:end]
        if f'<w:numId w:val="{NUM_ID}"' in block:
            text = text[:start] + block + text[end:]
            continue
        ol = f'<w:outlineLvl w:val="{i - 1}"/>'
        if ol not in block:
            ol_sp = f'<w:outlineLvl w:val="{i - 1}" />'
            if ol_sp not in block:
                raise SystemExit(f"styles.xml Heading{i}: outline marker not found")
            ol = ol_sp
        insert = ol + f'<w:numPr><w:numId w:val="{NUM_ID}"/><w:ilvl w:val="{i - 1}"/></w:numPr>'
        new_block = block.replace(ol, insert, 1)
        text = text[:start] + new_block + text[end:]
    return text


def patch_styles_with_effects(text: str) -> str:
    text = jc_left_to_start(text)
    # Avoid doubling jc if script is re-run on an already-patched file.
    text = re.sub(
        r'<w:pPr>(?!\s*<w:jc\s+w:val="start"\s*/>)',
        '<w:pPr><w:jc w:val="start"/>',
        text,
    )

    for i in range(1, 10):
        marker = f'<w:style w:type="paragraph" w:styleId="Heading{i}"'
        start = text.find(marker)
        if start == -1:
            raise SystemExit(f"missing style {marker}")
        end = text.find("</w:style>", start)
        if end == -1:
            raise SystemExit("unclosed style")
        block = text[start:end]
        ol = f'<w:outlineLvl w:val="{i - 1}"/>'
        if ol not in block:
            ol_sp = f'<w:outlineLvl w:val="{i - 1}" />'
            if ol_sp not in block:
                raise SystemExit(f"Heading{i}: outline marker not found")
            ol = ol_sp
        if f'<w:numId w:val="{NUM_ID}"' in block:
            text = text[:start] + block + text[end:]
            continue
        insert = ol + "\n      <w:numPr><w:numId w:val=\"" + NUM_ID + "\"/><w:ilvl w:val=\"" + str(i - 1) + "\"/></w:numPr>"
        new_block = block.replace(ol, insert, 1)
        text = text[:start] + new_block + text[end:]
    return text


def insert_toc_before_first_heading1_cadre(text: str) -> str:
    """Insert TOC before the first Heading1 paragraph that contains CADRE (any apostrophe encoding)."""
    if "Table des matières" in text:
        return text
    marker = 'w:val="Heading1"'
    pos = 0
    while True:
        hi = text.find(marker, pos)
        if hi == -1:
            raise SystemExit("document.xml: no Heading1 style found for TOC placement")
        p_start = text.rfind("<w:p", 0, hi)
        if p_start == -1:
            pos = hi + 1
            continue
        pend = text.find("</w:p>", hi)
        if pend == -1:
            raise SystemExit("document.xml: malformed paragraph")
        block = text[p_start : pend + len("</w:p>")]
        if "CADRE" in block:
            return text[:p_start] + DOC_TOC + text[p_start:]
        pos = hi + 1


def patch_document(text: str) -> str:
    text = jc_left_to_start(text)
    text = text.replace('w:jc w:val="center"', 'w:jc w:val="start"')
    text = text.replace('w:jc w:val="right"', 'w:jc w:val="start"')

    for legacy in (TOC_LEGACY_COMPLEX_LEFT, TOC_LEGACY_COMPLEX):
        if legacy in text:
            text = text.replace(legacy, DOC_TOC, 1)
            return text

    if "Table des matières" in text and 'w:fldSimple w:instr="' in text and "TOC" in text:
        return text

    if DOC_ANCHOR in text:
        return text.replace(DOC_ANCHOR, DOC_TOC + DOC_ANCHOR, 1)
    return insert_toc_before_first_heading1_cadre(text)


def patch_settings(text: str) -> str:
    if "w:updateFields" in text:
        return text
    ins = '<w:updateFields w:val="true"/>'
    needle = "<w:decimalSymbol"
    if needle in text:
        return text.replace(needle, ins + needle, 1)
    if "</w:settings>" in text:
        return text.replace("</w:settings>", ins + "</w:settings>", 1)
    raise SystemExit("settings.xml: unexpected structure")


def main() -> None:
    if not TRE_DOC.is_file():
        raise SystemExit(f"Missing file: {TRE_DOC}")

    if WORK.is_dir():
        shutil.rmtree(WORK)
    WORK.mkdir()

    with zipfile.ZipFile(TRE_DOC, "r") as zin:
        member_order = zin.namelist()
        zin.extractall(WORK)

    npath = WORK / "word" / "numbering.xml"
    npath.write_text(patch_numbering(npath.read_text(encoding="utf-8")), encoding="utf-8")

    sp = WORK / "word" / "styles.xml"
    sx = sp.read_text(encoding="utf-8")
    sx = patch_styles_xml_min(sx)
    sx = patch_styles_xml_headings(sx)
    sx = strip_paragraph_style_indents(sx)
    sx = jc_left_to_start(sx)
    sx = patch_normal_style_resets_numbering(sx)
    sp.write_text(sx, encoding="utf-8")

    sw_path = WORK / "word" / "stylesWithEffects.xml"
    if sw_path.is_file():
        sw = sw_path.read_text(encoding="utf-8")
        sw = patch_styles_with_effects(sw)
        sw = strip_paragraph_style_indents(sw)
        sw = jc_left_to_start(sw)
        sw = patch_normal_style_resets_numbering(sw)
        sw_path.write_text(sw, encoding="utf-8")

    dp = WORK / "word" / "document.xml"
    dp.write_text(patch_document(dp.read_text(encoding="utf-8")), encoding="utf-8")

    st = WORK / "word" / "settings.xml"
    st.write_text(patch_settings(st.read_text(encoding="utf-8")), encoding="utf-8")

    with zipfile.ZipFile(TRE_DOC, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for name in member_order:
            fp = WORK / name
            if fp.is_file():
                zout.write(fp, name)

    shutil.rmtree(WORK)
    print("Updated", TRE_DOC)


if __name__ == "__main__":
    main()
