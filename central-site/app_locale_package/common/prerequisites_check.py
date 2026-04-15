"""Vérification autonome des prérequis système pour l'installation Judi-Expert.

Script standalone exécuté par l'installateur pour vérifier que le PC
de l'expert satisfait les conditions minimales requises.

Réutilise la logique de local-site/scripts/prerequisites.py
mais ajoute la détection automatique de la configuration système.

Exigences : 1.1, 1.2, 31.4
"""

import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field

# ── Conditions minimales requises ─────────────────────────

MIN_CPU_CORES = 4
MIN_RAM_GB = 8.0
MIN_DISK_FREE_GB = 50.0


@dataclass
class SystemConfig:
    """Configuration système détectée."""

    cpu_cores: int
    ram_gb: float
    disk_free_gb: float
    disk_encrypted: bool


@dataclass
class ValidationResult:
    """Résultat de la validation des prérequis."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    config: SystemConfig | None = None


# ── Détection automatique de la configuration ─────────────


def detect_cpu_cores() -> int:
    """Détecte le nombre de cœurs CPU."""
    try:
        count = os.cpu_count()
        return count if count else 0
    except Exception:
        return 0


def detect_ram_gb() -> float:
    """Détecte la quantité de RAM en Go."""
    system = platform.system()
    try:
        if system == "Darwin":
            output = subprocess.check_output(
                ["sysctl", "-n", "hw.memsize"], text=True
            ).strip()
            return round(int(output) / (1024**3), 1)
        elif system == "Linux":
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal"):
                        kb = int(line.split()[1])
                        return round(kb / (1024**2), 1)
        elif system == "Windows":
            output = subprocess.check_output(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "[math]::Round((Get-CimInstance Win32_ComputerSystem)"
                    ".TotalPhysicalMemory / 1GB, 1)",
                ],
                text=True,
            ).strip()
            return float(output)
    except Exception:
        pass
    return 0.0


def detect_disk_free_gb(path: str | None = None) -> float:
    """Détecte l'espace disque libre en Go."""
    try:
        target = path or os.path.expanduser("~")
        usage = shutil.disk_usage(target)
        return round(usage.free / (1024**3), 1)
    except Exception:
        return 0.0


def detect_disk_encrypted() -> bool:
    """Détecte si le disque est chiffré."""
    system = platform.system()
    try:
        if system == "Darwin":
            output = subprocess.check_output(
                ["fdesetup", "status"], text=True
            ).strip()
            return "On" in output
        elif system == "Linux":
            # Vérifier LUKS via lsblk
            output = subprocess.check_output(
                ["lsblk", "-o", "TYPE"], text=True
            )
            if "crypt" in output:
                return True
            # Vérifier via dmsetup
            try:
                output = subprocess.check_output(
                    ["dmsetup", "ls", "--target", "crypt"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                )
                return bool(output.strip())
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        elif system == "Windows":
            output = subprocess.check_output(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "(Get-BitLockerVolume -MountPoint C:"
                    " -ErrorAction SilentlyContinue).ProtectionStatus",
                ],
                text=True,
            ).strip()
            return output == "On"
    except Exception:
        pass
    return False


def detect_system_config() -> SystemConfig:
    """Détecte automatiquement la configuration système."""
    return SystemConfig(
        cpu_cores=detect_cpu_cores(),
        ram_gb=detect_ram_gb(),
        disk_free_gb=detect_disk_free_gb(),
        disk_encrypted=detect_disk_encrypted(),
    )


# ── Validation ────────────────────────────────────────────


def validate_prerequisites(config: SystemConfig) -> ValidationResult:
    """Valide que la configuration système satisfait les prérequis minimaux.

    Retourne un ValidationResult avec valid=True si toutes les conditions
    sont remplies, sinon valid=False avec la liste exacte des erreurs
    correspondant aux conditions non satisfaites.
    """
    errors: list[str] = []

    if config.cpu_cores < MIN_CPU_CORES:
        errors.append(
            f"CPU insuffisant : {config.cpu_cores} cœurs "
            f"(minimum {MIN_CPU_CORES})"
        )
    if config.ram_gb < MIN_RAM_GB:
        errors.append(
            f"RAM insuffisante : {config.ram_gb} Go "
            f"(minimum {MIN_RAM_GB})"
        )
    if config.disk_free_gb < MIN_DISK_FREE_GB:
        errors.append(
            f"Espace disque insuffisant : {config.disk_free_gb} Go "
            f"(minimum {MIN_DISK_FREE_GB})"
        )
    if not config.disk_encrypted:
        errors.append(
            "Le disque n'est pas chiffré (BitLocker/FileVault/LUKS requis)"
        )

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        config=config,
    )


# ── Point d'entrée CLI ───────────────────────────────────


def main() -> int:
    """Point d'entrée pour l'exécution en ligne de commande."""
    print("")
    print("╔══════════════════════════════════════════════════╗")
    print("║   Judi-Expert — Vérification des prérequis      ║")
    print("╚══════════════════════════════════════════════════╝")
    print("")

    print("Détection de la configuration système...")
    config = detect_system_config()

    print(f"  CPU        : {config.cpu_cores} cœurs")
    print(f"  RAM        : {config.ram_gb} Go")
    print(f"  Disque     : {config.disk_free_gb} Go libres")
    print(f"  Chiffrement: {'Oui' if config.disk_encrypted else 'Non'}")
    print("")

    result = validate_prerequisites(config)

    if result.valid:
        print("✔ Tous les prérequis sont satisfaits.")
        print("  L'installation peut continuer.")
        return 0
    else:
        print("✖ Prérequis non satisfaits :")
        print("")
        for error in result.errors:
            print(f"  ✖ {error}")
        print("")
        print("L'installation ne peut pas continuer.")
        print("Veuillez corriger les problèmes ci-dessus et réessayer.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
