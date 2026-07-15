#!/usr/bin/env python3
"""Extract expert judiciaires from PDL Lyon PDF into CSV for Judi-Expert domains.

Fichiers attendus dans commercial/lyon/ :
  - 2026_Liste_experts_judiciaires.pdf  (source PDL)
  - expert-judiciaires-lyon.csv         (sortie générée)
"""

import csv
import re
from collections import Counter
from pathlib import Path

import fitz

BASE_DIR = Path(__file__).resolve().parent
PDF = BASE_DIR / "2026_Liste_experts_judiciaires.pdf"
OUT = BASE_DIR / "expert-judiciaires-lyon.csv"

# Domaines Judi-Expert (corpus/) ↔ codes spécialité PDL Cour d'appel de Lyon
DOMAIN_PREFIXES = {
    "psychologie": ["F-07", "G-06"],
    "psychiatrie": ["F-02", "G-05"],
    "medecine_legale": ["G-01", "G-02", "G-04", "G-07"],
    "comptabilite": ["D-01"],
    "batiment": ["C-02"],
}

TRIBUNALS = {
    "LYON",
    "ST ETIENNE",
    "BOURG EN BRESSE",
    "VILLEFRANCHE SUR SAONE",
    "ROANNE",
}

SPECIALTY_RE = re.compile(r"^([A-Z]-\d{2}(?:\.\d{2}){0,2})\s*-\s*(.+)$")
YEARS_RE = re.compile(r"^(\d{4})-(\d{4})$")
BIRTH_RE = re.compile(r"^\((\d{4})\)$")
TEL_RE = re.compile(r"^(T.l|Port\.?|Fax|M.l)\s*:\s*(.+)$", re.I)
CP_CITY_RE = re.compile(r"^(.+?)\s+(\d{5})\s+(.+?)\s*$")
CP_ONLY_RE = re.compile(r"^(\d{5})\s+(.+)$")
BP_RE = re.compile(r"(?i)\bbp\.?\s*\d+\b")
LOCATION_HINT_RE = re.compile(
    r"(?i)\b(h[ôo]pital|chu\b|centre hospitalier|clinique|cabinet|service|"
    r"p[ée]niche|port de|maison de|institut|l'h[ôo]pital)\b"
)
ADDR_PRO_RE = re.compile(r"(?i)^adresse professionnelle\s+[àa]\s+(.+)$")
STREET_TYPE_RE = re.compile(
    r"(?i)(?:^|\s)(?:\d+[a-z]?\s+(?:bis\s+|ter\s+)?"
    r"(?:rue|avenue|av\.|chemin|route|all[eé]e|impasse|boulevard|bd\.?|place|cours|quai|"
    r"sentier|passage|voie|imp\.|rte\.|all\.|lotissement|zone|r[eé]sidence|bp\.?)"
    r"|(?:rue|avenue|chemin|route|all[eé]e|impasse|boulevard|place|cours|quai|passage|voie)\s)"
)
DIPLOMA_HINT_RE = re.compile(
    r"(?i)\b(dipl[oô]me|master|dea|dess|d\.u\.t|bts|cap\b|architecte|doctorat|licence|"
    r"certificat|attestation|ma[iî]trise|baccalaur[eé]at|brevet|ing[eé]nieur|formation|"
    r"du\s|ich\b|defa|dplg|b\.e\.p|titulaire)\b"
)
PAGE_NUM_RE = re.compile(r"^\d{1,3}$")
STATUS_PROB_RE = re.compile(r"probatoire", re.I)
STATUS_INSCRIT_RE = re.compile(r"inscrit", re.I)
NAME_BIRTH_RE = re.compile(r"^(.+?)\s+\((\d{4})\)$")


def code_to_domaine(code: str) -> str | None:
    code = code.strip().upper()
    for domaine, prefixes in DOMAIN_PREFIXES.items():
        for prefix in prefixes:
            if code == prefix or code.startswith(prefix + "."):
                return domaine
    return None


def is_tribunal_line(line: str) -> bool:
    return line.strip().upper() in TRIBUNALS


def parse_name_line(line: str) -> tuple[str, str]:
    line = line.strip()
    line = re.sub(r"\s+\(\d{4}\)$", "", line)
    line = re.sub(r"\s+n[eé]e\s+.+$", "", line, flags=re.I)

    if " - " in line and line == line.upper():
        parts = [p.strip() for p in line.split(" - ", 1)]
        if len(parts) == 2:
            return parts[0], parts[1]

    parts = line.split()
    if len(parts) < 2:
        return line, ""

    if parts[0].isupper():
        nom_tokens: list[str] = []
        i = 0
        while i < len(parts) and parts[i].isupper():
            nom_tokens.append(parts[i])
            i += 1
        nom = " ".join(nom_tokens)
        prenom = " ".join(parts[i:]) if i < len(parts) else ""
    else:
        prenom = parts[-1]
        nom = " ".join(parts[:-1])

    return nom.strip(), prenom.strip()


def extract_lines(doc: fitz.Document) -> list[str]:
    lines: list[str] = []
    for page_idx in range(13, min(342, doc.page_count)):
        text = doc[page_idx].get_text()
        for raw in text.splitlines():
            line = raw.strip()
            if not line or PAGE_NUM_RE.match(line):
                continue
            lines.append(line)
    return lines


def is_address_line(line: str) -> bool:
    line = line.strip()
    if not line or CP_ONLY_RE.match(line):
        return False
    if BP_RE.search(line):
        return True
    if LOCATION_HINT_RE.search(line):
        return True
    if STREET_TYPE_RE.search(line):
        return True
    return bool(re.match(r"^\d+[\s,]", line))


def extract_street_from_mixed(line: str) -> str:
    line = line.strip()
    bp_match = re.search(r"(?i)([\w\s'\-]+-\s*)?bp\.?\s*\d+", line)
    if bp_match:
        return bp_match.group(0).strip()

    if is_address_line(line) and not DIPLOMA_HINT_RE.search(line):
        return line

    patterns = [
        r"([\w\s&\-\']+\s+\d+[\s,].{3,80}(?:route|rue|avenue|chemin|all[eé]e|impasse|boulevard|place|cours|quai)\s[^,\d]+)",
        r"((?:\d+[a-zA-Z]?\s+)?(?:bis\s+|ter\s+)?(?:rue|avenue|av\.|chemin|route|all[eé]e|impasse|boulevard|bd\.?|place|cours|quai|passage|voie)\s[^,\d]{3,80})",
        r"(CS\s+\d+\s+\d+[\s,][^,\d]{5,80})",
        r"((?:[\w\s'\-]+)(?:h[ôo]pital|chu|clinique|centre)[^,\d]{3,80})",
    ]
    for pattern in patterns:
        matches = list(re.finditer(pattern, line, re.I))
        if matches:
            return matches[-1].group(1).strip()

    if is_address_line(line):
        return line
    return ""


def parse_address(addr_lines: list[str]) -> tuple[str, str, str]:
    cp = ""
    ville = ""
    street = ""

    for bl in addr_lines:
        cm = CP_CITY_RE.match(bl.strip())
        if cm and is_address_line(cm.group(1)):
            return cm.group(1).strip(), cm.group(2), cm.group(3).strip()

    cp_idx = -1
    for idx in range(len(addr_lines) - 1, -1, -1):
        match = CP_ONLY_RE.match(addr_lines[idx].strip())
        if match:
            cp = match.group(1)
            ville = match.group(2).strip()
            cp_idx = idx
            break

    if cp_idx >= 0:
        for j in range(cp_idx - 1, -1, -1):
            candidate = addr_lines[j].strip()
            if is_address_line(candidate):
                street = extract_street_from_mixed(candidate) or candidate
                break
            extracted = extract_street_from_mixed(candidate)
            if extracted:
                street = extracted
                break
        if not street and cp_idx > 0:
            candidate = addr_lines[cp_idx - 1].strip()
            if not DIPLOMA_HINT_RE.search(candidate):
                street = candidate
        if not street:
            joined = " ".join(addr_lines[:cp_idx])
            street = extract_street_from_mixed(joined)
        return street, cp, ville

    joined = " ".join(addr_lines).strip()
    match = re.search(r"(.+?)\s+(\d{5})\s+(.+)$", joined)
    if match:
        street = extract_street_from_mixed(match.group(1))
        return street, match.group(2), match.group(3).strip()

    for bl in reversed(addr_lines):
        pro_match = ADDR_PRO_RE.match(bl.strip())
        if pro_match:
            location = pro_match.group(1).strip()
            return bl.strip(), "", location.upper()

    for bl in reversed(addr_lines):
        extracted = extract_street_from_mixed(bl)
        if extracted:
            return extracted, cp, ville

    return "", cp, ville


def parse_expert_block(
    lines: list[str],
    start: int,
    domaine: str,
    tribunal: str,
    status_probation: str,
    numero_enregistrement: str,
) -> tuple[dict[str, str] | None, int]:
    i = start
    if i >= len(lines):
        return None, i

    if YEARS_RE.match(lines[i]) or SPECIALTY_RE.match(lines[i]) or is_tribunal_line(lines[i]):
        return None, i

    name_line = lines[i]
    birth_match = NAME_BIRTH_RE.match(name_line)
    if birth_match:
        name_line = birth_match.group(1).strip()
    i += 1
    if birth_match is None and i < len(lines) and BIRTH_RE.match(lines[i]):
        i += 1

    tel = ""
    email = ""
    addr_lines: list[str] = []
    has_contact = False

    while i < len(lines):
        nxt = lines[i]
        if SPECIALTY_RE.match(nxt) or is_tribunal_line(nxt):
            break
        if STATUS_PROB_RE.search(nxt) or (STATUS_INSCRIT_RE.search(nxt) and "/" in nxt):
            break
        if YEARS_RE.match(nxt):
            break
        tm = TEL_RE.match(nxt)
        if tm:
            kind, val = tm.group(1).lower(), tm.group(2).strip()
            if kind.startswith("m"):
                email = val
                has_contact = True
            elif kind.startswith("port") and not tel:
                tel = val
            elif kind.startswith("t") and not tel:
                tel = val
            i += 1
            continue
        if has_contact:
            i += 1
            continue
        addr_lines.append(nxt)
        i += 1

    nom, prenom = parse_name_line(name_line)
    if not nom and not prenom:
        return None, i

    adresse, cp, ville = parse_address(addr_lines)

    return (
        {
            "domaine": domaine,
            "nom": nom,
            "prenom": prenom,
            "tribunal_enregistrement": tribunal,
            "numero_enregistrement": numero_enregistrement,
            "status_probation": status_probation,
            "email": email,
            "tel": tel,
            "adresse": adresse,
            "cp": cp,
            "ville": ville,
        },
        i,
    )


def parse_experts(lines: list[str]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    current_domaine: str | None = None
    current_tribunal = ""
    current_status = "OK"
    i = 0

    while i < len(lines):
        line = lines[i]
        sm = SPECIALTY_RE.match(line)
        if sm:
            code, _label = sm.group(1), sm.group(2)
            current_domaine = code_to_domaine(code)
            i += 1
            continue

        if current_domaine is None:
            i += 1
            continue

        if is_tribunal_line(line):
            current_tribunal = line.strip().upper()
            i += 1
            continue

        if STATUS_PROB_RE.search(line):
            current_status = "en cours"
            i += 1
            continue

        if STATUS_INSCRIT_RE.search(line) and "/" in line:
            current_status = "OK"
            i += 1
            continue

        if YEARS_RE.match(line):
            numero = line
            record, i = parse_expert_block(
                lines,
                i + 1,
                current_domaine,
                current_tribunal,
                current_status,
                numero,
            )
            if record:
                records.append(record)
            continue

        i += 1

    return records


def period_bounds(numero: str) -> tuple[int, int]:
    match = YEARS_RE.match(numero)
    if not match:
        return 0, 0
    return int(match.group(1)), int(match.group(2))


def dedupe_exact(records: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, ...]] = set()
    deduped: list[dict[str, str]] = []
    for record in records:
        key = (
            record["domaine"],
            record["nom"].upper(),
            record["prenom"].upper(),
            record["numero_enregistrement"],
            record["tribunal_enregistrement"],
            record["email"].lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return deduped


def dedupe_by_person(records: list[dict[str, str]]) -> list[dict[str, str]]:
    best: dict[tuple[str, ...], dict[str, str]] = {}
    for record in records:
        key = (
            record["domaine"],
            record["nom"].upper(),
            record["prenom"].upper(),
            record["tribunal_enregistrement"],
        )
        existing = best.get(key)
        if existing is None:
            best[key] = record
            continue

        start, end = period_bounds(record["numero_enregistrement"])
        e_start, e_end = period_bounds(existing["numero_enregistrement"])
        if (end, start) > (e_end, e_start):
            best[key] = record

    return list(best.values())


def main() -> None:
    if not PDF.exists():
        raise SystemExit(f"PDF introuvable : {PDF}")

    doc = fitz.open(PDF)
    lines = extract_lines(doc)
    raw_records = parse_experts(lines)
    records = dedupe_by_person(dedupe_exact(raw_records))

    counts = Counter(record["domaine"] for record in records)
    print("Raw records:", len(raw_records))
    print("After dedupe by person:", len(records))
    print("Counts by domaine:", dict(counts))
    print("Total:", len(records))
    print("With email:", sum(1 for r in records if r["email"]))
    print("Probation (en cours):", sum(1 for r in records if r["status_probation"] == "en cours"))

    fieldnames = [
        "domaine",
        "nom",
        "prenom",
        "tribunal_enregistrement",
        "numero_enregistrement",
        "status_probation",
        "email",
        "tel",
        "adresse",
        "cp",
        "ville",
    ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in sorted(
            records,
            key=lambda x: (x["domaine"], x["nom"], x["prenom"], x["numero_enregistrement"]),
        ):
            writer.writerow(record)

    print("Written", OUT)


if __name__ == "__main__":
    main()
