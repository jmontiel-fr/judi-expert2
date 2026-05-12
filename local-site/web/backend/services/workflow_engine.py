"""Moteur de workflow séquentiel pour les dossiers d'expertise.

Impose l'ordre strict Step1 → Step2 → Step3 → Step4 → Step5 et gère les
transitions de statut : initial → en_cours → fait → validé.

Valide : Exigences 10.1, 10.2, 10.3, 10.4
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.dossier import Dossier
from models.step import Step
from models.step_file import StepFile

# Nombre total d'étapes dans le workflow
_TOTAL_STEPS = 5
_VALID_STEP_NUMBERS = frozenset(range(1, _TOTAL_STEPS + 1))  # {1, 2, 3, 4, 5}

# Statuts possibles d'une étape
STATUT_INITIAL = "initial"
STATUT_EN_COURS = "en_cours"
STATUT_REALISE = "fait"
STATUT_VALIDE = "valide"

# Statuts possibles d'un dossier
DOSSIER_ACTIF = "actif"
DOSSIER_FERME = "fermé"
DOSSIER_ARCHIVE = "archive"


class WorkflowEngine:
    """Moteur de workflow séquentiel pour les dossiers d'expertise."""

    # ------------------------------------------------------------------
    # Helpers internes
    # ------------------------------------------------------------------

    @staticmethod
    async def _get_dossier_with_steps(
        dossier_id: int, db: AsyncSession
    ) -> Dossier:
        """Charge un dossier avec ses étapes ou lève 404."""
        result = await db.execute(
            select(Dossier)
            .options(selectinload(Dossier.steps))
            .where(Dossier.id == dossier_id)
        )
        dossier = result.scalar_one_or_none()
        if dossier is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dossier non trouvé",
            )
        return dossier

    @staticmethod
    def _get_step(dossier: Dossier, step_number: int) -> Step:
        """Retourne l'étape demandée ou lève 404."""
        if step_number not in _VALID_STEP_NUMBERS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le numéro d'étape doit être entre 1 et 5",
            )
        for s in dossier.steps:
            if s.step_number == step_number:
                return s
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Étape {step_number} non trouvée pour le dossier",
        )

    @staticmethod
    def _previous_steps_validated(dossier: Dossier, step_number: int) -> bool:
        """Vérifie que toutes les étapes précédentes sont validées."""
        for s in dossier.steps:
            if s.step_number < step_number and s.statut != STATUT_VALIDE:
                return False
        return True

    # ------------------------------------------------------------------
    # Vérifications d'accès
    # ------------------------------------------------------------------

    async def can_access_step(
        self, dossier_id: int, step_number: int, db: AsyncSession
    ) -> bool:
        """Vérifie si l'étape peut être consultée / accédée.

        Step0 est toujours accessible.
        Les autres étapes nécessitent que toutes les étapes précédentes
        soient au statut "validé".
        Un dossier archivé interdit tout accès en modification (mais
        l'accès en lecture reste possible via cette méthode).
        """
        dossier = await self._get_dossier_with_steps(dossier_id, db)
        if step_number == 1:
            return True
        return self._previous_steps_validated(dossier, step_number)

    async def can_execute_step(
        self, dossier_id: int, step_number: int, db: AsyncSession
    ) -> bool:
        """Vérifie si l'étape peut être exécutée (passage à "réalisé").

        Conditions :
        - Le dossier est actif (ni fermé, ni archivé)
        - L'étape est au statut "initial"
        - Toutes les étapes précédentes sont validées (Step0 : aucune)
        """
        dossier = await self._get_dossier_with_steps(dossier_id, db)
        if dossier.statut != DOSSIER_ACTIF:
            return False
        step = self._get_step(dossier, step_number)
        if step.statut != STATUT_INITIAL:
            return False
        if step_number == 1:
            return True
        return self._previous_steps_validated(dossier, step_number)

    async def can_validate_step(
        self, dossier_id: int, step_number: int, db: AsyncSession
    ) -> bool:
        """Vérifie si l'étape peut être validée (passage à "validé").

        Conditions :
        - Le dossier est actif (ni fermé, ni archivé)
        - L'étape est au statut "réalisé"
        - Toutes les étapes précédentes sont validées (Step0 : aucune)
        """
        dossier = await self._get_dossier_with_steps(dossier_id, db)
        if dossier.statut != DOSSIER_ACTIF:
            return False
        step = self._get_step(dossier, step_number)
        if step.statut != STATUT_REALISE:
            return False
        if step_number == 1:
            return True
        return self._previous_steps_validated(dossier, step_number)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    async def start_step(
        self, dossier_id: int, step_number: int, db: AsyncSession
    ) -> Step:
        """Marque une étape comme "en_cours" (génération lancée).

        Lève HTTPException 403 si l'opération n'est pas autorisée.
        """
        dossier = await self._get_dossier_with_steps(dossier_id, db)

        if dossier.statut != DOSSIER_ACTIF:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Le dossier n'est pas actif",
            )

        step = self._get_step(dossier, step_number)

        if step.statut not in (STATUT_INITIAL, STATUT_REALISE):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="L'étape ne peut pas être relancée dans son statut actuel",
            )

        if step_number > 1 and not self._previous_steps_validated(dossier, step_number):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Étape précédente non validée",
            )

        step.statut = STATUT_EN_COURS
        step.executed_at = datetime.now(UTC)  # Timestamp de début d'exécution
        await db.flush()
        return step

    async def fail_step(
        self, dossier_id: int, step_number: int, db: AsyncSession
    ) -> Step:
        """Remet une étape "en_cours" à "initial" après un échec."""
        dossier = await self._get_dossier_with_steps(dossier_id, db)
        step = self._get_step(dossier, step_number)
        if step.statut == STATUT_EN_COURS:
            step.statut = STATUT_INITIAL
            step.progress_current = None
            step.progress_total = None
            step.progress_message = None
            await db.flush()
        return step

    async def execute_step(
        self, dossier_id: int, step_number: int, db: AsyncSession
    ) -> Step:
        """Marque une étape comme "fait".

        Lève HTTPException 403 si l'opération n'est pas autorisée.
        """
        dossier = await self._get_dossier_with_steps(dossier_id, db)

        if dossier.statut == DOSSIER_FERME:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Le dossier est fermé, aucune modification n'est possible",
            )

        if dossier.statut != DOSSIER_ACTIF:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Le dossier est archivé, aucune modification n'est possible",
            )

        step = self._get_step(dossier, step_number)

        if step.statut == STATUT_VALIDE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Étape verrouillée, modification impossible",
            )

        if step.statut not in (STATUT_INITIAL, STATUT_EN_COURS):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="L'étape doit être au statut 'initial' ou 'en_cours' pour être exécutée",
            )

        if step_number > 1 and not self._previous_steps_validated(dossier, step_number):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Étape précédente non validée",
            )

        step.statut = STATUT_REALISE
        now = datetime.now(UTC)
        # Calculer la durée d'exécution si le step a été démarré
        if step.executed_at:
            # Gérer le cas où executed_at est naive (SQLite ne stocke pas la timezone)
            start = step.executed_at
            if start.tzinfo is None:
                start = start.replace(tzinfo=UTC)
            duration = (now - start).total_seconds()
            step.execution_duration_seconds = round(duration, 1)
        step.executed_at = now
        await db.flush()
        return step

    async def validate_step(
        self, dossier_id: int, step_number: int, db: AsyncSession
    ) -> Step:
        """Marque une étape comme "validé".

        Lève HTTPException 403 si l'opération n'est pas autorisée.
        Note : la validation du Step 3 ne passe plus automatiquement
        le dossier en "archive". L'expert doit explicitement fermer
        le dossier via le bouton "Fermer le dossier".
        """
        dossier = await self._get_dossier_with_steps(dossier_id, db)

        if dossier.statut == DOSSIER_FERME:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Le dossier est fermé, aucune modification n'est possible",
            )

        if dossier.statut != DOSSIER_ACTIF:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Le dossier est archivé, aucune modification n'est possible",
            )

        step = self._get_step(dossier, step_number)

        if step.statut == STATUT_VALIDE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Étape verrouillée, modification impossible",
            )

        if step.statut != STATUT_REALISE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="L'étape doit être au statut 'réalisé' pour être validée",
            )

        if step_number > 1 and not self._previous_steps_validated(dossier, step_number):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Étape précédente non validée",
            )

        step.statut = STATUT_VALIDE
        step.validated_at = datetime.now(UTC)

        await db.flush()
        return step

    # ------------------------------------------------------------------
    # Résolution de fichiers
    # ------------------------------------------------------------------

    async def resolve_file_path(
        self,
        dossier_id: int,
        step_number: int,
        filename: str,
        db: AsyncSession,
    ) -> str:
        """Résout le chemin du fichier actif (modifié ou original) pour une étape.

        Retourne ``step_file.file_path`` qui pointe toujours vers le
        fichier actif — qu'il ait été remplacé par l'expert ou non.

        Args:
            dossier_id: Identifiant du dossier.
            step_number: Numéro de l'étape (1-5).
            filename: Nom du fichier recherché.
            db: Session async SQLAlchemy.

        Returns:
            Chemin absolu vers le fichier actif sur le disque.

        Raises:
            HTTPException 404: Si le fichier n'est pas trouvé.
        """
        result = await db.execute(
            select(StepFile)
            .join(Step, StepFile.step_id == Step.id)
            .where(
                Step.dossier_id == dossier_id,
                Step.step_number == step_number,
                StepFile.filename == filename,
            )
        )
        step_file = result.scalar_one_or_none()
        if step_file is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fichier non trouvé",
            )
        return step_file.file_path

    # ------------------------------------------------------------------
    # Guards (à utiliser dans les routes)
    # ------------------------------------------------------------------

    async def require_step_access(
        self, dossier_id: int, step_number: int, db: AsyncSession
    ) -> None:
        """Lève HTTPException 403 si l'étape ne peut pas être accédée."""
        can = await self.can_access_step(dossier_id, step_number, db)
        if not can:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Étape précédente non validée",
            )

    async def require_step_not_validated(
        self, dossier_id: int, step_number: int, db: AsyncSession
    ) -> None:
        """Lève HTTPException 403 si l'étape est déjà validée (immuable)."""
        dossier = await self._get_dossier_with_steps(dossier_id, db)
        step = self._get_step(dossier, step_number)
        if step.statut == STATUT_VALIDE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Étape verrouillée, modification impossible",
            )

    # ------------------------------------------------------------------
    # Fermeture de dossier
    # ------------------------------------------------------------------

    async def close_dossier(
        self, dossier_id: int, db: AsyncSession
    ) -> Dossier:
        """Ferme le dossier si toutes les étapes sont validées.

        Vérifie que les 5 étapes ont statut "validé".
        Met le dossier.statut à "fermé".
        Lève HTTP 403 si pré-conditions non remplies.
        """
        dossier = await self._get_dossier_with_steps(dossier_id, db)

        if dossier.statut == DOSSIER_FERME:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Le dossier est déjà fermé",
            )

        # Vérifier que toutes les étapes sont validées
        for step in dossier.steps:
            if step.statut != STATUT_VALIDE:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Toutes les étapes doivent être validées pour fermer le dossier",
                )

        dossier.statut = DOSSIER_FERME
        await db.flush()
        return dossier

    @staticmethod
    def is_dossier_closed(dossier: Dossier) -> bool:
        """Vérifie si le dossier est fermé."""
        return dossier.statut == DOSSIER_FERME

    @staticmethod
    def is_dossier_modifiable(dossier: Dossier) -> bool:
        """Vérifie si le dossier accepte des modifications (statut actif)."""
        return dossier.statut == DOSSIER_ACTIF

    async def reset_step(
        self, dossier_id: int, step_number: int, db: AsyncSession
    ) -> Step:
        """Remet une étape à "initial" et supprime ses fichiers en base.

        Conditions :
        - Le dossier est actif
        - L'étape n'est pas déjà au statut "initial"
        - Aucune étape suivante n'est validée

        Les fichiers sur disque doivent être nettoyés par l'appelant.
        """
        dossier = await self._get_dossier_with_steps(dossier_id, db)

        if dossier.statut != DOSSIER_ACTIF:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Le dossier n'est pas actif, reset impossible",
            )

        step = self._get_step(dossier, step_number)

        if step.statut == STATUT_INITIAL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="L'étape est déjà au statut initial",
            )

        # Vérifier qu'aucune étape suivante n'est validée
        for s in dossier.steps:
            if s.step_number > step_number and s.statut == STATUT_VALIDE:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"L'étape {s.step_number} est validée, reset impossible",
                )

        # Remettre cette étape et les suivantes non-validées à initial
        for s in dossier.steps:
            if s.step_number >= step_number and s.statut != STATUT_INITIAL:
                s.statut = STATUT_INITIAL
                s.executed_at = None
                s.validated_at = None
                s.progress_current = None
                s.progress_total = None
                s.progress_message = None

        # Supprimer les StepFile de cette étape en base
        result = await db.execute(
            select(StepFile).where(StepFile.step_id == step.id)
        )
        for sf in result.scalars().all():
            await db.delete(sf)

        await db.flush()
        return step


# Singleton réutilisable dans les routes
workflow_engine = WorkflowEngine()
