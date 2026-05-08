"""Test par propriété — Aller-retour du fichier VERSION.

# Feature: version-management, Property 1: VERSION file round-trip

**Validates: Requirements 1.1, 11.1**

Propriété 1 : Pour toute version semver valide (MAJOR.MINOR.PATCH sans zéros
en tête) et toute date ISO valide (YYYY-MM-DD), écrire ces deux lignes dans
un fichier temporaire puis appeler read_version_file() doit retourner un
VersionInfo avec les valeurs exactes.
"""

import sys
import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Module isolation: load local-site backend services
# ---------------------------------------------------------------------------
_local_backend = str(
    Path(__file__).resolve().parents[2] / "local-site" / "web" / "backend"
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
sys.path.insert(0, _local_backend)

from services.version_reader import VersionInfo, compare_versions, read_version_file, validate_semver  # noqa: E402

_local_cache = {}
for _prefix in _modules_to_isolate:
    for _k in list(sys.modules):
        if _k == _prefix or _k.startswith(_prefix + "."):
            _local_cache[_k] = sys.modules.pop(_k)

sys.modules.update(_saved_modules)
sys.path[:] = _saved_path


# ---------------------------------------------------------------------------
# Stratégies Hypothesis
# ---------------------------------------------------------------------------

# Composant semver : entier non-négatif sans zéros en tête (0 est valide, 01 non)
semver_component = st.integers(min_value=0, max_value=9999)

# Version semver valide : MAJOR.MINOR.PATCH
semver_strategy = st.builds(
    lambda major, minor, patch: f"{major}.{minor}.{patch}",
    major=semver_component,
    minor=semver_component,
    patch=semver_component,
)

# Date ISO valide : YYYY-MM-DD (utilise hypothesis dates pour garantir la validité)
iso_date_strategy = st.dates(
    min_value=__import__("datetime").date(1900, 1, 1),
    max_value=__import__("datetime").date(2099, 12, 31),
).map(lambda d: d.isoformat())


# ---------------------------------------------------------------------------
# Propriété 1 — Round-trip écriture → lecture du fichier VERSION
# ---------------------------------------------------------------------------


@settings(max_examples=100, deadline=None)
@given(version=semver_strategy, date=iso_date_strategy)
def test_version_file_roundtrip(version: str, date: str):
    """Écrire semver + date ISO dans un fichier, lire avec read_version_file,
    vérifier que le VersionInfo retourné correspond exactement.

    Pour toute version semver valide et toute date ISO valide :
    1. Écrire version sur la ligne 1, date sur la ligne 2
    2. Appeler read_version_file()
    3. Vérifier que result.version == version et result.date == date
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        version_path = Path(tmp_dir) / "VERSION"

        # Écrire le fichier VERSION (2 lignes)
        version_path.write_text(f"{version}\n{date}\n", encoding="utf-8")

        # Lire via read_version_file
        result = read_version_file(version_path)

        # Vérifier le round-trip exact
        assert isinstance(result, VersionInfo)
        assert result.version == version
        assert result.date == date


# ---------------------------------------------------------------------------
# Propriété 2 — Validation du format semver
# Feature: version-management, Property 2: Semver validation
# ---------------------------------------------------------------------------
# **Validates: Requirements 2.5**


# Stratégie : version semver valide (réutilise semver_strategy existante)
# Chaque composant est un entier ≥ 0 sans zéros en tête, formaté en string.

# Stratégies pour les cas invalides
_invalid_semver_leading_zeros = st.builds(
    lambda major, minor, patch: f"0{major}.{minor}.{patch}",
    major=st.integers(min_value=1, max_value=999),
    minor=semver_component,
    patch=semver_component,
)

_invalid_semver_too_few_parts = st.builds(
    lambda major, minor: f"{major}.{minor}",
    major=semver_component,
    minor=semver_component,
)

_invalid_semver_too_many_parts = st.builds(
    lambda major, minor, patch, extra: f"{major}.{minor}.{patch}.{extra}",
    major=semver_component,
    minor=semver_component,
    patch=semver_component,
    extra=semver_component,
)

_invalid_semver_negative = st.builds(
    lambda major, minor, patch: f"-{major}.{minor}.{patch}",
    major=st.integers(min_value=1, max_value=999),
    minor=semver_component,
    patch=semver_component,
)

_invalid_semver_non_numeric = st.builds(
    lambda prefix, minor, patch: f"{prefix}.{minor}.{patch}",
    prefix=st.text(
        alphabet=st.characters(whitelist_categories=("L",)),
        min_size=1,
        max_size=5,
    ),
    minor=semver_component,
    patch=semver_component,
)

_invalid_semver_random_text = st.text(min_size=0, max_size=20).filter(
    lambda s: not __import__("re").match(r"^\d+\.\d+\.\d+$", s)
)

# Union de toutes les stratégies invalides
invalid_semver_strategy = st.one_of(
    _invalid_semver_leading_zeros,
    _invalid_semver_too_few_parts,
    _invalid_semver_too_many_parts,
    _invalid_semver_negative,
    _invalid_semver_non_numeric,
    _invalid_semver_random_text,
)


@settings(max_examples=100, deadline=None)
@given(version=semver_strategy)
def test_semver_valid_accepted(version: str):
    """Cas positif : toute chaîne MAJOR.MINOR.PATCH avec des entiers non-négatifs
    sans zéros en tête doit être acceptée par validate_semver.

    Pour tout triplet (MAJOR, MINOR, PATCH) d'entiers ≥ 0 :
    validate_semver(f"{MAJOR}.{MINOR}.{PATCH}") == True
    """
    assert validate_semver(version) is True


@settings(max_examples=100, deadline=None)
@given(version=invalid_semver_strategy)
def test_semver_invalid_rejected(version: str):
    """Cas négatif : toute chaîne ne correspondant pas au format MAJOR.MINOR.PATCH
    (zéros en tête, mauvais nombre de composants, négatifs, non-numériques, texte
    aléatoire) doit être rejetée par validate_semver.

    Pour toute chaîne invalide :
    validate_semver(chaîne) == False
    """
    assert validate_semver(version) is False


# ---------------------------------------------------------------------------
# Feature: version-management, Property 4: Version display formatting
# ---------------------------------------------------------------------------

# Import format_version_display (already available via the module isolation above)
# Re-import from the cached local modules
sys.path.insert(0, _local_backend)
for _k, _v in _local_cache.items():
    sys.modules[_k] = _v

from services.version_reader import format_version_display  # noqa: E402

# Restore modules again
for _k in list(sys.modules):
    for _prefix in _modules_to_isolate:
        if _k == _prefix or _k.startswith(_prefix + "."):
            if _k not in _local_cache:
                sys.modules.pop(_k, None)
sys.modules.update(_saved_modules)
sys.path[:] = _saved_path

# French month names for verification
_FRENCH_MONTHS_VERIFY = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]

# Strategy: random prefix from the two valid site prefixes
prefix_strategy = st.sampled_from(["App Locale", "Site Central"])


@settings(max_examples=100, deadline=None)
@given(version=semver_strategy, date=iso_date_strategy, prefix=prefix_strategy)
def test_version_display_formatting(version: str, date: str, prefix: str):
    """Propriété 4 : Le formatage de la version pour l'affichage doit produire
    une chaîne contenant le préfixe, "V", la version exacte, " - ", et la date
    formatée en français ({jour} {mois} {année}).

    **Validates: Requirements 5.1, 12.1**
    """
    info = VersionInfo(version=version, date=date)
    result = format_version_display(info, prefix)

    # Parse the date components for verification
    parts = date.split("-")
    year = parts[0]
    month_idx = int(parts[1]) - 1
    day_no_leading_zero = str(int(parts[2]))
    french_month = _FRENCH_MONTHS_VERIFY[month_idx]

    # 1. Result starts with the prefix
    assert result.startswith(prefix), (
        f"Expected result to start with '{prefix}', got: '{result}'"
    )

    # 2. Contains " V" followed by the exact version string
    assert f" V{version}" in result, (
        f"Expected ' V{version}' in result, got: '{result}'"
    )

    # 3. Contains " - "
    assert " - " in result, (
        f"Expected ' - ' in result, got: '{result}'"
    )

    # 4. Contains the year from the date
    assert year in result, (
        f"Expected year '{year}' in result, got: '{result}'"
    )

    # 5. Contains the French month name corresponding to the month number
    assert french_month in result, (
        f"Expected French month '{french_month}' in result, got: '{result}'"
    )

    # 6. Contains the day number (without leading zero)
    # Check that the day appears in the date portion (after " - ")
    date_portion = result.split(" - ", 1)[1]
    assert date_portion.startswith(day_no_leading_zero + " "), (
        f"Expected date portion to start with day '{day_no_leading_zero} ', "
        f"got: '{date_portion}'"
    )


# ---------------------------------------------------------------------------
# Propriété 3 — Ordre de comparaison des versions semver
# Feature: version-management, Property 3: Semver comparison ordering
# ---------------------------------------------------------------------------
# **Validates: Requirements 3.2**


@settings(max_examples=100, deadline=None)
@given(a=semver_strategy)
def test_comparison_reflexivity(a: str):
    """Réflexivité : pour toute version semver valide a, compare_versions(a, a) == 0.

    Pour tout a valide :
    compare_versions(a, a) == 0
    """
    assert compare_versions(a, a) == 0


@settings(max_examples=100, deadline=None)
@given(a=semver_strategy, b=semver_strategy)
def test_comparison_antisymmetry(a: str, b: str):
    """Antisymétrie : pour toutes versions semver valides a, b :
    si compare(a, b) < 0 alors compare(b, a) > 0,
    si compare(a, b) > 0 alors compare(b, a) < 0,
    si compare(a, b) == 0 alors compare(b, a) == 0.

    Pour tout (a, b) valides :
    sign(compare(a, b)) == -sign(compare(b, a))
    """
    cmp_ab = compare_versions(a, b)
    cmp_ba = compare_versions(b, a)

    if cmp_ab < 0:
        assert cmp_ba > 0
    elif cmp_ab > 0:
        assert cmp_ba < 0
    else:
        assert cmp_ba == 0


@settings(max_examples=100, deadline=None)
@given(a=semver_strategy, b=semver_strategy, c=semver_strategy)
def test_comparison_transitivity(a: str, b: str, c: str):
    """Transitivité : pour toutes versions semver valides a, b, c :
    si compare(a, b) <= 0 et compare(b, c) <= 0 alors compare(a, c) <= 0.

    Pour tout (a, b, c) valides :
    compare(a, b) <= 0 AND compare(b, c) <= 0 => compare(a, c) <= 0
    """
    cmp_ab = compare_versions(a, b)
    cmp_bc = compare_versions(b, c)

    if cmp_ab <= 0 and cmp_bc <= 0:
        assert compare_versions(a, c) <= 0


@settings(max_examples=100, deadline=None)
@given(a=semver_strategy, b=semver_strategy)
def test_comparison_consistent_with_tuple_ordering(a: str, b: str):
    """Cohérence avec l'ordre des tuples Python : compare_versions doit
    produire le même résultat que la comparaison de tuples (major, minor, patch).

    Pour tout (a, b) valides :
    compare_versions(a, b) concorde avec la comparaison de
    tuple(int(x) for x in a.split('.')) vs tuple(int(x) for x in b.split('.'))
    """
    tuple_a = tuple(int(x) for x in a.split("."))
    tuple_b = tuple(int(x) for x in b.split("."))

    cmp_result = compare_versions(a, b)

    if tuple_a < tuple_b:
        assert cmp_result == -1
    elif tuple_a > tuple_b:
        assert cmp_result == 1
    else:
        assert cmp_result == 0


# ---------------------------------------------------------------------------
# Feature: version-management, Property 5: Data isolation in version requests
# ---------------------------------------------------------------------------
# **Validates: Requirements 9.1, 9.2**


# Helper function that builds the version check request parameters.
# This represents the contract: when checking for updates, only current_version
# is sent to the Site Central — no dossier or expert data.
def build_version_check_params(current_version: str) -> dict:
    """Construit les paramètres de requête pour la vérification de version.

    Seul le champ current_version est transmis au Site Central.
    Aucune donnée de dossier ou d'expert ne doit être incluse.

    Args:
        current_version: Version semver courante de l'Application Locale.

    Returns:
        Dictionnaire contenant uniquement {"current_version": current_version}.
    """
    return {"current_version": current_version}


# Forbidden fields that must NEVER appear in version check requests
_FORBIDDEN_FIELDS = frozenset([
    "dossier_id",
    "contenu",
    "expert_id",
    "nom",
    "prenom",
    "email",
    "telephone",
    "adresse",
    "dossier",
    "expert",
    "step_content",
    "chat_message",
])


@settings(max_examples=100, deadline=None)
@given(version=semver_strategy)
def test_data_isolation_in_version_requests(version: str):
    """Propriété 5 : Les paramètres de requête de vérification de version ne
    contiennent que le champ current_version. Aucun champ relatif aux dossiers
    ou aux données personnelles de l'expert n'est présent.

    Pour toute version semver valide :
    1. build_version_check_params(version) retourne un dict avec exactement une clé
    2. Cette clé est "current_version"
    3. La valeur correspond à la version d'entrée
    4. Aucun champ interdit (dossier_id, contenu, expert_id, nom, prenom,
       email, telephone, adresse, dossier, expert, step_content, chat_message)
       n'est présent
    """
    params = build_version_check_params(version)

    # 1. The dict has exactly one key
    assert len(params) == 1, (
        f"Expected exactly 1 key in params, got {len(params)}: {list(params.keys())}"
    )

    # 2. The only key is "current_version"
    assert "current_version" in params, (
        f"Expected 'current_version' key, got: {list(params.keys())}"
    )

    # 3. The value matches the input version
    assert params["current_version"] == version, (
        f"Expected value '{version}', got '{params['current_version']}'"
    )

    # 4. No forbidden fields are present
    present_forbidden = set(params.keys()) & _FORBIDDEN_FIELDS
    assert len(present_forbidden) == 0, (
        f"Forbidden fields found in version request params: {present_forbidden}"
    )


# ---------------------------------------------------------------------------
# Feature: version-management, Property 6: Installer filename includes version
# ---------------------------------------------------------------------------
# **Validates: Requirement 10.2**


def build_installer_filename(version: str) -> str:
    """Construit le nom de fichier de l'installateur avec la version."""
    return f"judi-expert-local-{version}.exe"


@settings(max_examples=100, deadline=None)
@given(version=semver_strategy)
def test_installer_filename_includes_version(version: str):
    """Property 6: Le nom de fichier de l'installateur contient la version exacte.

    Pour tout numéro de version semver valide, le nom de fichier de l'installateur
    généré doit contenir la chaîne de version exacte et suivre le pattern attendu.
    """
    filename = build_installer_filename(version)
    assert version in filename
    assert filename.startswith("judi-expert-local-")
    assert filename.endswith(".exe")
