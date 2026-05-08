"""Service centralisé de gestion des chemins fichiers sur disque.

Toute la logique de construction des chemins est ici.
Structure cible :
    <DATA_DIR>/<nom-dossier>/step{n}/in/
    <DATA_DIR>/<nom-dossier>/step{n}/out/

Où :
- <DATA_DIR> = variable d'env DATA_DIR (défaut: "data")
- <nom-dossier> = nom du dossier (slug, tel que saisi par l'expert)
- n = numéro de step (1 à 5)
- in/ = fichiers d'entrée (uploadés par l'expert ou copiés du step précédent)
- out/ = fichiers de sortie (générés par l'IA ou le traitement)
"""

import os
import re
from pathlib import Path

DATA_DIR: str = os.environ.get("DATA_DIR", "data")

# Nombre de steps dans le workflow
STEP_COUNT = 5


def _slugify(name: str) -> str:
    """Convertit un nom de dossier en slug filesystem-safe.

    Conserve les caractères alphanumériques, tirets, underscores et espaces.
    Remplace les espaces multiples par un seul espace.
    Supprime les caractères spéciaux dangereux pour le filesystem.
    """
    # Supprimer les caractères non autorisés
    slug = re.sub(r'[<>:"/\\|?*]', '', name)
    # Remplacer les espaces multiples par un seul
    slug = re.sub(r'\s+', ' ', slug).strip()
    # Fallback si le slug est vide
    if not slug:
        slug = "dossier"
    return slug


def dossier_root(dossier_name: str) -> str:
    """Retourne le chemin racine d'un dossier sur disque.

    Ex: data/Expertise Dupont 2026/
    """
    return os.path.join(DATA_DIR, _slugify(dossier_name))


def step_dir(dossier_name: str, step_number: int) -> str:
    """Retourne le chemin du répertoire d'un step.

    Ex: data/Expertise Dupont 2026/step1/
    """
    return os.path.join(dossier_root(dossier_name), f"step{step_number}")


def step_in_dir(dossier_name: str, step_number: int) -> str:
    """Retourne le chemin du sous-dossier d'entrée d'un step.

    Ex: data/Expertise Dupont 2026/step1/in/
    """
    return os.path.join(step_dir(dossier_name, step_number), "in")


def step_out_dir(dossier_name: str, step_number: int) -> str:
    """Retourne le chemin du sous-dossier de sortie d'un step.

    Ex: data/Expertise Dupont 2026/step1/out/
    """
    return os.path.join(step_dir(dossier_name, step_number), "out")


def create_dossier_tree(dossier_name: str) -> str:
    """Crée l'arborescence complète d'un dossier (step1-5/in + out).

    Retourne le chemin racine du dossier créé.
    """
    root = dossier_root(dossier_name)
    for n in range(1, STEP_COUNT + 1):
        os.makedirs(step_in_dir(dossier_name, n), exist_ok=True)
        os.makedirs(step_out_dir(dossier_name, n), exist_ok=True)
    return root


def file_path_in(dossier_name: str, step_number: int, filename: str) -> str:
    """Retourne le chemin complet d'un fichier d'entrée."""
    return os.path.join(step_in_dir(dossier_name, step_number), filename)


def file_path_out(dossier_name: str, step_number: int, filename: str) -> str:
    """Retourne le chemin complet d'un fichier de sortie."""
    return os.path.join(step_out_dir(dossier_name, step_number), filename)


# ---------------------------------------------------------------------------
# Compatibilité : fonctions legacy (par ID) — à supprimer après migration
# ---------------------------------------------------------------------------


def legacy_dossier_root(dossier_id: int) -> str:
    """[LEGACY] Chemin racine par ID — pour migration uniquement."""
    return os.path.join(DATA_DIR, "dossiers", str(dossier_id))


def legacy_step_dir(dossier_id: int, step_number: int) -> str:
    """[LEGACY] Chemin step par ID — pour migration uniquement."""
    return os.path.join(legacy_dossier_root(dossier_id), f"step{step_number}")
