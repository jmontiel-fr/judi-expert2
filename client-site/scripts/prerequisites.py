"""Validation des prérequis système pour l'installation de l'Application Locale.

Vérifie que le PC de l'expert satisfait les conditions minimales requises
en CPU, RAM, espace disque, chiffrement du disque et absence de
synchronisation cloud sur le répertoire de données.

Exigences : 1.1, 1.2
"""

import os
from dataclasses import dataclass, field


@dataclass
class SystemConfig:
    """Configuration système du PC de l'expert."""

    cpu_cores: int
    ram_gb: float
    disk_free_gb: float
    disk_encrypted: bool
    install_path: str = r"C:\judi-expert"


# Conditions minimales requises
MIN_CPU_CORES = 4
MIN_RAM_GB = 8.0
MIN_DISK_FREE_GB = 50.0

# Services cloud connus dont la synchronisation est incompatible
CLOUD_SYNC_MARKERS = [
    "OneDrive",
    "Dropbox",
    "Google Drive",
    "iCloudDrive",
    "MEGA",
    "pCloud",
]


@dataclass
class ValidationResult:
    """Résultat de la validation des prérequis."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def detect_cloud_sync(install_path: str) -> str | None:
    """Détecte si le chemin d'installation est dans un dossier synchronisé.

    Args:
        install_path: Chemin d'installation de Judi-Expert.

    Returns:
        Nom du service cloud détecté, ou None si aucun.
    """
    normalized = os.path.normpath(install_path).replace("\\", "/").lower()
    for marker in CLOUD_SYNC_MARKERS:
        if marker.lower() in normalized:
            return marker
    return None


def validate_prerequisites(config: SystemConfig) -> ValidationResult:
    """Valide que la configuration système satisfait les prérequis minimaux.

    Retourne un ValidationResult avec valid=True si toutes les conditions
    sont remplies, sinon valid=False avec la liste exacte des erreurs
    correspondant aux conditions non satisfaites.
    """
    errors: list[str] = []
    warnings: list[str] = []

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
            "Le disque n'est pas chiffré (BitLocker/VeraCrypt requis)"
        )

    cloud_service = detect_cloud_sync(config.install_path)
    if cloud_service:
        warnings.append(
            f"Le répertoire d'installation est dans un dossier synchronisé "
            f"({cloud_service}). Les données d'expertise ne doivent pas être "
            f"synchronisées dans le cloud (RGPD). Utilisez C:\\judi-expert."
        )

    return ValidationResult(
        valid=len(errors) == 0 and len(warnings) == 0,
        errors=errors,
        warnings=warnings,
    )
