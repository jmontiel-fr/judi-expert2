"""Utilitaire de lecture et validation du fichier VERSION.

Ce module fournit les fonctions nécessaires pour lire, valider et formater
les informations de version de l'application Judi-Expert.

Le fichier VERSION contient 2 lignes :
- Ligne 1 : numéro de version semver (MAJOR.MINOR.PATCH)
- Ligne 2 : date de publication au format ISO (YYYY-MM-DD)
"""

import re
from dataclasses import dataclass
from pathlib import Path

# Mois en français pour le formatage de la date d'affichage
_FRENCH_MONTHS = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
]

_SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
_ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class VersionInfo:
    """Informations de version lues depuis le fichier VERSION.

    Attributes:
        version: Numéro de version semver (ex: "1.2.0").
        date: Date de publication au format ISO (ex: "2026-04-17").
    """

    version: str
    date: str


def read_version_file(path: Path) -> VersionInfo:
    """Lit le fichier VERSION (2 lignes : semver, date ISO).

    Args:
        path: Chemin vers le fichier VERSION.

    Returns:
        VersionInfo contenant la version et la date.

    Raises:
        FileNotFoundError: Si le fichier est absent.
        ValueError: Si le format du fichier est invalide.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Fichier de version manquant : {path}"
        )

    content = path.read_text(encoding="utf-8").strip()
    lines = content.splitlines()

    if len(lines) < 2:
        raise ValueError(
            f"Format invalide dans {path} : le fichier doit contenir "
            f"2 lignes (version semver et date ISO)"
        )

    version = lines[0].strip()
    date = lines[1].strip()

    if not validate_semver(version):
        raise ValueError(
            f"Version invalide dans {path} : '{version}' "
            f"ne respecte pas le format MAJOR.MINOR.PATCH"
        )

    if not _ISO_DATE_PATTERN.match(date):
        raise ValueError(
            f"Date invalide dans {path} : '{date}' "
            f"ne respecte pas le format YYYY-MM-DD"
        )

    return VersionInfo(version=version, date=date)


def validate_semver(version: str) -> bool:
    """Valide qu'une chaîne respecte le format semver MAJOR.MINOR.PATCH.

    Chaque composant doit être un entier non-négatif.

    Args:
        version: Chaîne à valider.

    Returns:
        True si la chaîne est un semver valide, False sinon.
    """
    if not _SEMVER_PATTERN.match(version):
        return False

    parts = version.split(".")
    for part in parts:
        # Rejeter les zéros en tête (ex: "01.02.03") sauf "0" seul
        if len(part) > 1 and part.startswith("0"):
            return False

    return True


def compare_versions(a: str, b: str) -> int:
    """Compare deux versions semver.

    Args:
        a: Première version semver (ex: "1.2.0").
        b: Deuxième version semver (ex: "1.3.0").

    Returns:
        -1 si a < b, 0 si a == b, 1 si a > b.

    Raises:
        ValueError: Si l'une des versions n'est pas un semver valide.
    """
    if not validate_semver(a):
        raise ValueError(f"Version invalide : '{a}'")
    if not validate_semver(b):
        raise ValueError(f"Version invalide : '{b}'")

    parts_a = tuple(int(x) for x in a.split("."))
    parts_b = tuple(int(x) for x in b.split("."))

    if parts_a < parts_b:
        return -1
    elif parts_a > parts_b:
        return 1
    else:
        return 0


def format_version_display(info: VersionInfo, prefix: str) -> str:
    """Produit la chaîne d'affichage de la version au format français.

    Format : "{prefix} V{version} - {jour} {mois} {année}"
    Exemple : "App Locale V1.2.0 - 17 avril 2026"

    Args:
        info: Informations de version.
        prefix: Préfixe du site (ex: "App Locale" ou "Site Central").

    Returns:
        Chaîne formatée pour l'affichage.

    Raises:
        ValueError: Si la date dans info n'est pas au format ISO valide.
    """
    if not _ISO_DATE_PATTERN.match(info.date):
        raise ValueError(
            f"Date invalide : '{info.date}' "
            f"ne respecte pas le format YYYY-MM-DD"
        )

    parts = info.date.split("-")
    year = parts[0]
    month_idx = int(parts[1]) - 1
    day = str(int(parts[2]))  # Supprime le zéro en tête (08 -> 8)

    if month_idx < 0 or month_idx > 11:
        raise ValueError(
            f"Mois invalide dans la date : '{info.date}'"
        )

    month_name = _FRENCH_MONTHS[month_idx]

    return f"{prefix} V{info.version} - {day} {month_name} {year}"
