"""Moteur de workflow séquentiel pour les dossiers d'expertise.

Impose l'ordre strict Step0 → Step1 → Step2 → Step3 et gère les
transitions de statut : initial → réalisé → validé.

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

# Nombre total d'étapes dans le workflow
_TOTAL_STEPS = 4
_VALID_STEP_NUMBERS = frozenset(range(_TOTAL_STEPS))  # {0, 1, 2, 3}

# Statuts possibles d'une étape
STATUT_INITIAL = "initial"
STATUT_REALISE = "réalisé"
STATUT_VALIDE = "validé"

# Statuts possibles d'un dossier
DOSSIER_ACTIF = "actif"
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
                detail="Le numéro d'étape doit être entre 0 et 3",
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
        if step_number == 0:
            return True
        return self._previous_steps_validated(dossier, step_number)

    async def can_execute_step(
        self, dossier_id: int, step_number: int, db: AsyncSession
    ) -> bool:
        """Vérifie si l'étape peut être exécutée (passage à "réalisé").

        Conditions :
        - Le dossier est actif
        - L'étape est au statut "initial"
        - Toutes les étapes précédentes sont validées (Step0 : aucune)
        """
        dossier = await self._get_dossier_with_steps(dossier_id, db)
        if dossier.statut != DOSSIER_ACTIF:
            return False
        step = self._get_step(dossier, step_number)
        if step.statut != STATUT_INITIAL:
            return False
        if step_number == 0:
            return True
        return self._previous_steps_validated(dossier, step_number)

    async def can_validate_step(
        self, dossier_id: int, step_number: int, db: AsyncSession
    ) -> bool:
        """Vérifie si l'étape peut être validée (passage à "validé").

        Conditions :
        - Le dossier est actif
        - L'étape est au statut "réalisé"
        - Toutes les étapes précédentes sont validées (Step0 : aucune)
        """
        dossier = await self._get_dossier_with_steps(dossier_id, db)
        if dossier.statut != DOSSIER_ACTIF:
            return False
        step = self._get_step(dossier, step_number)
        if step.statut != STATUT_REALISE:
            return False
        if step_number == 0:
            return True
        return self._previous_steps_validated(dossier, step_number)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    async def execute_step(
        self, dossier_id: int, step_number: int, db: AsyncSession
    ) -> Step:
        """Marque une étape comme "réalisé".

        Lève HTTPException 403 si l'opération n'est pas autorisée.
        """
        dossier = await self._get_dossier_with_steps(dossier_id, db)

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

        if step.statut != STATUT_INITIAL:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="L'étape doit être au statut 'initial' pour être exécutée",
            )

        if step_number > 0 and not self._previous_steps_validated(dossier, step_number):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Étape précédente non validée",
            )

        step.statut = STATUT_REALISE
        step.executed_at = datetime.now(UTC)
        await db.flush()
        return step

    async def validate_step(
        self, dossier_id: int, step_number: int, db: AsyncSession
    ) -> Step:
        """Marque une étape comme "validé".

        Si step_number == 3, archive également le dossier.
        Lève HTTPException 403 si l'opération n'est pas autorisée.
        """
        dossier = await self._get_dossier_with_steps(dossier_id, db)

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

        if step_number > 0 and not self._previous_steps_validated(dossier, step_number):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Étape précédente non validée",
            )

        step.statut = STATUT_VALIDE
        step.validated_at = datetime.now(UTC)

        # Validation du Step3 → archivage du dossier
        if step_number == 3:
            dossier.statut = DOSSIER_ARCHIVE

        await db.flush()
        return step

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


# Singleton réutilisable dans les routes
workflow_engine = WorkflowEngine()
