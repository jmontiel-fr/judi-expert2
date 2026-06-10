"""Service d'archivage dossier — ZIP + timbre SHA-256."""

from __future__ import annotations

import hashlib
import io
import logging
import os
import zipfile
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from models.step_file import StepFile
from services.file_paths import create_archive_dir, dossier_root, step_out_dir

logger = logging.getLogger(__name__)


async def archive_dossier(
    *,
    dossier_id: int,
    dossier_name: str,
    step_number: int,
    step_id: int,
    db: AsyncSession,
    input_filename: str | None = None,
    input_path: str | None = None,
    input_file_type: str | None = None,
    input_file_size: int | None = None,
    revision_correction_count: int = 0,
    placeholders_step: int = 1,
) -> tuple[str, str, str]:
    """Génère l'archive ZIP et le timbre pour un dossier.

    Returns:
        (zip_filename, timbre_filename, sha256_hash)
    """
    root_dir = dossier_root(dossier_name)
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for dirpath, dirnames, filenames in os.walk(root_dir):
            if "archive" in dirnames:
                dirnames.remove("archive")
            for fname in filenames:
                full_path = os.path.join(dirpath, fname)
                arc_name = os.path.relpath(full_path, root_dir)
                zf.write(full_path, arc_name)

    zip_bytes = zip_buffer.getvalue()
    sha256_hash = hashlib.sha256(zip_bytes).hexdigest()

    archive_path = create_archive_dir(dossier_name)
    zip_filename = f"{dossier_name}.zip"
    zip_path = os.path.join(archive_path, zip_filename)
    with open(zip_path, "wb") as f:
        f.write(zip_bytes)

    placeholders_csv_path = os.path.join(
        step_out_dir(dossier_name, placeholders_step), "placeholders.csv"
    )
    meta: dict[str, str] = {}
    if os.path.isfile(placeholders_csv_path):
        with open(placeholders_csv_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("nom_placeholder"):
                    continue
                parts = line.split(";", 1)
                if len(parts) == 2 and parts[1].strip():
                    meta[parts[0].strip()] = parts[1].strip()

    now = datetime.now(UTC)
    timbre_filename = f"{dossier_name}-timbre.txt"
    timbre_path = os.path.join(archive_path, timbre_filename)
    with open(timbre_path, "w", encoding="utf-8") as f:
        f.write(f"=== TIMBRE D'ARCHIVAGE — {dossier_name} ===\n\n")
        f.write(f"Date d'archivage : {now.strftime('%d/%m/%Y %H:%M:%S UTC')}\n\n")
        f.write("--- Contexte expertise ---\n")
        f.write(f"Demandeur nom : {meta.get('nom_demandeur', '')}\n")
        f.write(f"Demandeur prénom : {meta.get('prenom_demandeur', '')}\n")
        f.write(f"Demandeur adresse : {meta.get('adresse_demandeur', '')}\n")
        f.write(f"Demande date : {meta.get('date_ordonnance', '')}\n")
        f.write(f"Tribunal nom : {meta.get('tribunal', '')}\n")
        f.write(f"Tribunal adresse : {meta.get('ville_juridiction', '')}\n")
        f.write(f"Demande référence : {meta.get('reference_dossier', '')}\n")
        f.write(f"MEC nom : {meta.get('nom_mec', meta.get('nom_defendeur', ''))}\n")
        f.write(f"MEC prénom : {meta.get('prenom_mec', meta.get('prenom_defendeur', ''))}\n")
        f.write(f"MEC adresse : {meta.get('adresse_mec', '')}\n")
        f.write(f"Expert nom : {meta.get('nom_expert', '')}\n")
        f.write(f"Expert prénom : {meta.get('prenom_expert', '')}\n")
        f.write(f"Expert adresse : {meta.get('adresse_expert', '')}\n")
        f.write("\n--- Archive ---\n")
        f.write(f"Fichier archive : {zip_filename}\n")
        f.write(f"SHA-256 : {sha256_hash}\n")
        f.write(f"Taille : {len(zip_bytes)} octets\n")
        if revision_correction_count:
            f.write("\n--- Révision linguistique ---\n")
            f.write(f"Corrections appliquées : {revision_correction_count}\n")

    logger.info(
        "[Archive] Dossier %d step %d — %s (%d octets), hash %s",
        dossier_id,
        step_number,
        zip_filename,
        len(zip_bytes),
        sha256_hash,
    )

    if input_filename and input_path and input_file_type and input_file_size is not None:
        db.add(
            StepFile(
                step_id=step_id,
                filename=input_filename,
                file_path=input_path,
                file_type=input_file_type,
                file_size=input_file_size,
            )
        )

    db.add(
        StepFile(
            step_id=step_id,
            filename=zip_filename,
            file_path=zip_path,
            file_type="archive_zip",
            file_size=len(zip_bytes),
        )
    )
    db.add(
        StepFile(
            step_id=step_id,
            filename=timbre_filename,
            file_path=timbre_path,
            file_type="timbre",
            file_size=os.path.getsize(timbre_path),
        )
    )

    return zip_filename, timbre_filename, sha256_hash
