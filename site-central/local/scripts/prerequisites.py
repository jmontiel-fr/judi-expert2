"""Validation des prérequis système pour l'installation de l'Application Locale.

Vérifie que le PC de l'expert satisfait les conditions minimales requises
en CPU, RAM, espace disque et chiffrement du disque.

Exigences : 1.1, 1.2
"""

from dataclasses import dataclass, field


@dataclass
class SystemConfig:
    """Configuration système du PC de l'expert."""

    cpu_cores: int
    ram_gb: float
    disk_free_gb: float
    disk_encrypted: bool


# Conditions minimales requises
MIN_CPU_CORES = 4
MIN_RAM_GB = 8.0
MIN_DISK_FREE_GB = 50.0


@dataclass
class ValidationResult:
    """Résultat de la validation des prérequis."""

    valid: bool
    errors: list[str] = field(default_factory=list)


def validate_prerequisites(config: SystemConfig) -> ValidationResult:
    """Valide que la configuration système satisfait les prérequis minimaux.

    Retourne un ValidationResult avec valid=True si toutes les conditions
    sont remplies, sinon valid=False avec la liste exacte des erreurs
    correspondant aux conditions non satisfaites.
    """
    errors: list[str] = []

    if config.cpu_cores < MIN_CPU_CORES:
        errors.append(
            f"CPU insuffisant : {config.cpu_cores} cœurs (minimum {MIN_CPU_CORES})"
        )
    if config.ram_gb < MIN_RAM_GB:
        errors.append(
            f"RAM insuffisante : {config.ram_gb} Go (minimum {MIN_RAM_GB})"
        )
    if config.disk_free_gb < MIN_DISK_FREE_GB:
        errors.append(
            f"Espace disque insuffisant : {config.disk_free_gb} Go (minimum {MIN_DISK_FREE_GB})"
        )
    if not config.disk_encrypted:
        errors.append(
            "Le disque n'est pas chiffré (BitLocker ou équivalent requis)"
        )

    return ValidationResult(valid=len(errors) == 0, errors=errors)
