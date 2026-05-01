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
    """Détecte si le disque est chiffré (BitLocker ou VeraCrypt)."""
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
            # Vérifier BitLocker
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
            if output == "On":
                return True
            # Vérifier VeraCrypt (driver actif)
            try:
                output = subprocess.check_output(
                    [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        "Get-Service veracrypt -ErrorAction SilentlyContinue"
                        " | Select-Object -ExpandProperty Status",
                    ],
                    text=True,
                ).strip()
                if output == "Running":
                    return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
    except Exception:
        pass
    return False


def detect_chrome_installed() -> bool:
    """Détecte si Google Chrome est installé."""
    if platform.system() != "Windows":
        return True  # Non vérifié hors Windows
    chrome_paths = [
        os.path.join(os.environ.get("PROGRAMFILES", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
    ]
    return any(os.path.isfile(p) for p in chrome_paths if p)


def detect_veracrypt_installed() -> bool:
    """Détecte si VeraCrypt est installé."""
    if platform.system() != "Windows":
        return True  # Non vérifié hors Windows
    veracrypt_paths = [
        os.path.join(os.environ.get("PROGRAMFILES", ""), "VeraCrypt", "VeraCrypt.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "VeraCrypt", "VeraCrypt.exe"),
    ]
    return any(os.path.isfile(p) for p in veracrypt_paths if p)


def detect_system_config() -> SystemConfig:
    """Détecte automatiquement la configuration système."""
    return SystemConfig(
        cpu_cores=detect_cpu_cores(),
        ram_gb=detect_ram_gb(),
        disk_free_gb=detect_disk_free_gb(),
        disk_encrypted=detect_disk_encrypted(),
    )


# ── Détection de synchronisation cloud ────────────────────

CLOUD_SYNC_MARKERS = [
    "OneDrive",
    "Dropbox",
    "Google Drive",
    "iCloudDrive",
    "MEGA",
    "pCloud",
]


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

    # Chemin d'installation recommandé
    install_path = os.environ.get("JUDI_INSTALL_PATH", r"C:\judi-expert")

    print("Détection de la configuration système...")
    config = detect_system_config()

    print(f"  CPU        : {config.cpu_cores} cœurs")
    print(f"  RAM        : {config.ram_gb} Go")
    print(f"  Disque     : {config.disk_free_gb} Go libres")
    print(f"  Chiffrement: {'Oui' if config.disk_encrypted else 'Non'}")
    print(f"  Installation: {install_path}")

    # Détection logiciels
    chrome_ok = detect_chrome_installed()
    veracrypt_ok = detect_veracrypt_installed()
    print(f"  Chrome     : {'Installé' if chrome_ok else 'Non trouvé'}")
    if not config.disk_encrypted:
        print(f"  VeraCrypt  : {'Installé' if veracrypt_ok else 'Non trouvé'}")
    print("")

    result = validate_prerequisites(config)

    # Vérification synchronisation cloud
    cloud_service = detect_cloud_sync(install_path)
    if cloud_service:
        print(f"⚠ ATTENTION : Le répertoire d'installation est dans un")
        print(f"  dossier synchronisé ({cloud_service}).")
        print(f"  Les données d'expertise ne doivent PAS être")
        print(f"  synchronisées dans le cloud (RGPD/secret professionnel).")
        print(f"  → Utilisez C:\\judi-expert comme répertoire.")
        print("")

    # Vérification logiciels
    warnings: list[str] = []

    if not chrome_ok:
        warnings.append(
            "Google Chrome n'est pas installé. Il est requis pour "
            "l'interface Judi-Expert. Téléchargez-le sur https://www.google.com/chrome/"
        )

    if not config.disk_encrypted and not veracrypt_ok:
        warnings.append(
            "Le disque n'est pas chiffré et VeraCrypt n'est pas installé. "
            "Installez VeraCrypt (https://veracrypt.eu) puis chiffrez le "
            "disque système pour protéger les données d'expertise."
        )

    for w in warnings:
        print(f"⚠ {w}")
        print("")

    if result.valid and not cloud_service and not warnings:
        print("✔ Tous les prérequis sont satisfaits.")
        print("  L'installation peut continuer.")
        return 0
    else:
        if result.errors:
            print("✖ Prérequis non satisfaits :")
            print("")
            for error in result.errors:
                print(f"  ✖ {error}")
            print("")
        if cloud_service:
            print("✖ Répertoire d'installation dans un dossier cloud.")
            print("")
        if warnings:
            print("⚠ Logiciels manquants (voir ci-dessus).")
            print("")
        print("Veuillez corriger les problèmes ci-dessus et réessayer.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
