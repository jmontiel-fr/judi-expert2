"""Test par propriété — Validation des prérequis système.

**Validates: Requirements 1.1, 1.2**

Propriété 1 : Pour toute configuration système (CPU, RAM, espace disque,
chiffrement), la fonction de validation doit accepter la configuration si et
seulement si toutes les conditions minimales sont satisfaites. De plus, pour
toute configuration rejetée, le message d'erreur doit lister exactement les
conditions non remplies — ni plus, ni moins.
"""

import sys
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# Ajouter le répertoire scripts au path pour les imports
sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[2]
        / "local-site"
        / "scripts"
    ),
)

from prerequisites import (
    MIN_CPU_CORES,
    MIN_DISK_FREE_GB,
    MIN_RAM_GB,
    SystemConfig,
    validate_prerequisites,
)


# ---------------------------------------------------------------------------
# Stratégies Hypothesis
# ---------------------------------------------------------------------------

# CPU : entiers entre 1 et 32 (couvre les cas sous et au-dessus du minimum)
cpu_cores_strategy = st.integers(min_value=1, max_value=32)

# RAM : flottants positifs raisonnables (0.5 à 128 Go)
ram_gb_strategy = st.floats(min_value=0.5, max_value=128.0, allow_nan=False, allow_infinity=False)

# Espace disque : flottants positifs raisonnables (1 à 2000 Go)
disk_free_gb_strategy = st.floats(min_value=1.0, max_value=2000.0, allow_nan=False, allow_infinity=False)

# Chiffrement : booléen
disk_encrypted_strategy = st.booleans()


# Stratégie composite pour une configuration système complète
system_config_strategy = st.builds(
    SystemConfig,
    cpu_cores=cpu_cores_strategy,
    ram_gb=ram_gb_strategy,
    disk_free_gb=disk_free_gb_strategy,
    disk_encrypted=disk_encrypted_strategy,
)


# ---------------------------------------------------------------------------
# Helpers : calcul indépendant des conditions non remplies
# ---------------------------------------------------------------------------

def _count_unmet_conditions(config: SystemConfig) -> int:
    """Compte le nombre de conditions non remplies de manière indépendante."""
    count = 0
    if config.cpu_cores < MIN_CPU_CORES:
        count += 1
    if config.ram_gb < MIN_RAM_GB:
        count += 1
    if config.disk_free_gb < MIN_DISK_FREE_GB:
        count += 1
    if not config.disk_encrypted:
        count += 1
    return count


def _all_conditions_met(config: SystemConfig) -> bool:
    """Vérifie indépendamment si toutes les conditions sont satisfaites."""
    return (
        config.cpu_cores >= MIN_CPU_CORES
        and config.ram_gb >= MIN_RAM_GB
        and config.disk_free_gb >= MIN_DISK_FREE_GB
        and config.disk_encrypted
    )


# ---------------------------------------------------------------------------
# Propriété 1a — Acceptance ssi toutes les conditions sont remplies
# ---------------------------------------------------------------------------

@settings(max_examples=200)
@given(config=system_config_strategy)
def test_acceptance_iff_all_conditions_met(config: SystemConfig):
    """La validation accepte la configuration si et seulement si
    CPU >= MIN, RAM >= MIN, disque >= MIN et disque chiffré."""
    result = validate_prerequisites(config)
    expected_valid = _all_conditions_met(config)

    assert result.valid == expected_valid, (
        f"Config: {config}, expected valid={expected_valid}, got valid={result.valid}"
    )


# ---------------------------------------------------------------------------
# Propriété 1b — Complétude des erreurs : le nombre d'erreurs correspond
#                exactement au nombre de conditions non remplies
# ---------------------------------------------------------------------------

@settings(max_examples=200)
@given(config=system_config_strategy)
def test_error_count_equals_unmet_conditions(config: SystemConfig):
    """Pour toute configuration rejetée, le nombre d'erreurs est exactement
    égal au nombre de conditions non remplies."""
    result = validate_prerequisites(config)
    expected_error_count = _count_unmet_conditions(config)

    assert len(result.errors) == expected_error_count, (
        f"Config: {config}, expected {expected_error_count} errors, "
        f"got {len(result.errors)}: {result.errors}"
    )


# ---------------------------------------------------------------------------
# Propriété 1c — Spécificité des erreurs : chaque condition non remplie
#                produit exactement un message d'erreur correspondant
# ---------------------------------------------------------------------------

@settings(max_examples=200)
@given(config=system_config_strategy)
def test_error_specificity(config: SystemConfig):
    """Chaque condition non remplie produit exactement un message d'erreur
    correspondant, et aucune erreur n'est produite pour une condition remplie."""
    result = validate_prerequisites(config)
    error_text = "\n".join(result.errors)

    # CPU
    cpu_error_present = "CPU insuffisant" in error_text
    cpu_unmet = config.cpu_cores < MIN_CPU_CORES
    assert cpu_error_present == cpu_unmet, (
        f"CPU: unmet={cpu_unmet}, error_present={cpu_error_present}"
    )

    # RAM
    ram_error_present = "RAM insuffisante" in error_text
    ram_unmet = config.ram_gb < MIN_RAM_GB
    assert ram_error_present == ram_unmet, (
        f"RAM: unmet={ram_unmet}, error_present={ram_error_present}"
    )

    # Disque
    disk_error_present = "Espace disque insuffisant" in error_text
    disk_unmet = config.disk_free_gb < MIN_DISK_FREE_GB
    assert disk_error_present == disk_unmet, (
        f"Disk: unmet={disk_unmet}, error_present={disk_error_present}"
    )

    # Chiffrement
    encryption_error_present = "n'est pas chiffré" in error_text
    encryption_unmet = not config.disk_encrypted
    assert encryption_error_present == encryption_unmet, (
        f"Encryption: unmet={encryption_unmet}, error_present={encryption_error_present}"
    )


# ---------------------------------------------------------------------------
# Propriété 1 — Cas valide : aucune erreur quand tout est satisfait
# ---------------------------------------------------------------------------

@settings(max_examples=200)
@given(config=system_config_strategy)
def test_valid_config_has_no_errors(config: SystemConfig):
    """Quand la configuration est valide, la liste d'erreurs est vide."""
    result = validate_prerequisites(config)

    if result.valid:
        assert result.errors == [], (
            f"Config valide mais erreurs présentes : {result.errors}"
        )
    else:
        assert len(result.errors) > 0, (
            f"Config invalide mais aucune erreur listée"
        )
