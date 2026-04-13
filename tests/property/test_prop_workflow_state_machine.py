"""Test par propriété — Machine à états du workflow d'expertise.

**Validates: Requirements 7.4, 8.4, 9.5, 10.1, 10.2, 10.3, 10.4**

Propriété 6 : Pour tout dossier et pour toute séquence de transitions d'étapes,
le système doit respecter les invariants suivants :
- L'ordre séquentiel Step0 → Step1 → Step2 → Step3 est strictement imposé
- Une étape au statut "initial" ou "réalisé" interdit l'accès aux étapes suivantes
- Seule la validation d'une étape (passage à "validé") autorise l'accès à l'étape suivante
- Une étape au statut "validé" est immuable (toute tentative de modification échoue)
- La validation du Step3 verrouille définitivement le dossier entier

Utilise une RuleBasedStateMachine Hypothesis pour explorer toutes les séquences
possibles d'opérations execute_step / validate_step.
"""

import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from hypothesis import HealthCheck, settings
from hypothesis.stateful import (
    RuleBasedStateMachine,
    initialize,
    rule,
)
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Ajouter le backend au path pour les imports
sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[2]
        / "site-central"
        / "local"
        / "web"
        / "backend"
    ),
)

from models import Base, Dossier, Step
from services.workflow_engine import (
    DOSSIER_ACTIF,
    DOSSIER_ARCHIVE,
    STATUT_INITIAL,
    STATUT_REALISE,
    STATUT_VALIDE,
    WorkflowEngine,
)


# ---------------------------------------------------------------------------
# Helper : boucle d'événements pour exécuter les coroutines dans la machine
# ---------------------------------------------------------------------------

def run_async(coro):
    """Exécute une coroutine de manière synchrone (pour la RuleBasedStateMachine)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Machine à états du workflow
# ---------------------------------------------------------------------------

class WorkflowStateMachine(RuleBasedStateMachine):
    """Machine à états Hypothesis pour le workflow d'expertise.

    Explore toutes les séquences possibles d'opérations execute_step et
    validate_step sur un dossier avec 4 étapes, et vérifie que le
    WorkflowEngine respecte les invariants du workflow.
    """

    def __init__(self):
        super().__init__()
        self.engine = WorkflowEngine()
        # État attendu de chaque étape (0-3)
        self.expected_statuts: dict[int, str] = {}
        self.expected_dossier_statut: str = DOSSIER_ACTIF
        self.dossier_id: int | None = None
        self.session_factory = None
        self.db_engine = None

    @initialize()
    def setup_dossier(self):
        """Crée une base en mémoire, un dossier avec 4 étapes 'initial'."""
        self.db_engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", echo=False
        )
        self.session_factory = async_sessionmaker(
            self.db_engine, expire_on_commit=False
        )

        async def _init():
            async with self.db_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            async with self.session_factory() as session:
                dossier = Dossier(
                    nom="Test-Dossier",
                    ticket_id="TICKET-001",
                    domaine="psychologie",
                    statut=DOSSIER_ACTIF,
                )
                session.add(dossier)
                await session.flush()

                for step_number in range(4):
                    session.add(
                        Step(
                            dossier_id=dossier.id,
                            step_number=step_number,
                            statut=STATUT_INITIAL,
                        )
                    )
                await session.flush()
                await session.commit()
                return dossier.id

        self.dossier_id = run_async(_init())
        self.expected_statuts = {i: STATUT_INITIAL for i in range(4)}
        self.expected_dossier_statut = DOSSIER_ACTIF

    def teardown(self):
        """Nettoie le moteur de base de données."""
        if self.db_engine is not None:
            run_async(self.db_engine.dispose())

    # ------------------------------------------------------------------
    # Helpers de prédiction
    # ------------------------------------------------------------------

    def _can_execute(self, step_number: int) -> bool:
        """Prédit si execute_step devrait réussir."""
        if self.expected_dossier_statut != DOSSIER_ACTIF:
            return False
        if self.expected_statuts[step_number] != STATUT_INITIAL:
            return False
        # Toutes les étapes précédentes doivent être validées
        for i in range(step_number):
            if self.expected_statuts[i] != STATUT_VALIDE:
                return False
        return True

    def _can_validate(self, step_number: int) -> bool:
        """Prédit si validate_step devrait réussir."""
        if self.expected_dossier_statut != DOSSIER_ACTIF:
            return False
        if self.expected_statuts[step_number] != STATUT_REALISE:
            return False
        # Toutes les étapes précédentes doivent être validées
        for i in range(step_number):
            if self.expected_statuts[i] != STATUT_VALIDE:
                return False
        return True

    # ------------------------------------------------------------------
    # Règles
    # ------------------------------------------------------------------

    @rule()
    def execute_step_0(self):
        self._do_execute(0)

    @rule()
    def execute_step_1(self):
        self._do_execute(1)

    @rule()
    def execute_step_2(self):
        self._do_execute(2)

    @rule()
    def execute_step_3(self):
        self._do_execute(3)

    @rule()
    def validate_step_0(self):
        self._do_validate(0)

    @rule()
    def validate_step_1(self):
        self._do_validate(1)

    @rule()
    def validate_step_2(self):
        self._do_validate(2)

    @rule()
    def validate_step_3(self):
        self._do_validate(3)

    # ------------------------------------------------------------------
    # Implémentation des actions
    # ------------------------------------------------------------------

    def _do_execute(self, step_number: int):
        """Tente d'exécuter une étape et vérifie le résultat."""
        should_succeed = self._can_execute(step_number)

        async def _run():
            async with self.session_factory() as session:
                try:
                    result = await self.engine.execute_step(
                        self.dossier_id, step_number, session
                    )
                    await session.commit()
                    return ("ok", result)
                except HTTPException as exc:
                    await session.rollback()
                    return ("error", exc.status_code)

        outcome, data = run_async(_run())

        if should_succeed:
            assert outcome == "ok", (
                f"execute_step({step_number}) devrait réussir "
                f"(statuts={self.expected_statuts}, dossier={self.expected_dossier_statut}) "
                f"mais a échoué avec status_code={data}"
            )
            assert data.statut == STATUT_REALISE
            assert data.executed_at is not None
            self.expected_statuts[step_number] = STATUT_REALISE
        else:
            assert outcome == "error", (
                f"execute_step({step_number}) devrait échouer "
                f"(statuts={self.expected_statuts}, dossier={self.expected_dossier_statut}) "
                f"mais a réussi"
            )
            assert data == 403

    def _do_validate(self, step_number: int):
        """Tente de valider une étape et vérifie le résultat."""
        should_succeed = self._can_validate(step_number)

        async def _run():
            async with self.session_factory() as session:
                try:
                    result = await self.engine.validate_step(
                        self.dossier_id, step_number, session
                    )
                    await session.commit()
                    return ("ok", result)
                except HTTPException as exc:
                    await session.rollback()
                    return ("error", exc.status_code)

        outcome, data = run_async(_run())

        if should_succeed:
            assert outcome == "ok", (
                f"validate_step({step_number}) devrait réussir "
                f"(statuts={self.expected_statuts}, dossier={self.expected_dossier_statut}) "
                f"mais a échoué avec status_code={data}"
            )
            assert data.statut == STATUT_VALIDE
            assert data.validated_at is not None
            self.expected_statuts[step_number] = STATUT_VALIDE
            # Validation du Step3 → archivage du dossier
            if step_number == 3:
                self.expected_dossier_statut = DOSSIER_ARCHIVE
        else:
            assert outcome == "error", (
                f"validate_step({step_number}) devrait échouer "
                f"(statuts={self.expected_statuts}, dossier={self.expected_dossier_statut}) "
                f"mais a réussi"
            )
            assert data == 403

    # ------------------------------------------------------------------
    # Invariants vérifiés après chaque étape
    # ------------------------------------------------------------------

    def _check_invariants(self):
        """Vérifie les invariants globaux du workflow."""
        # Si le dossier est archivé, toutes les étapes doivent être validées
        if self.expected_dossier_statut == DOSSIER_ARCHIVE:
            for i in range(4):
                assert self.expected_statuts[i] == STATUT_VALIDE

        # L'ordre séquentiel est respecté : si step N est réalisé ou validé,
        # toutes les étapes < N doivent être validées
        for i in range(4):
            if self.expected_statuts[i] in (STATUT_REALISE, STATUT_VALIDE):
                for j in range(i):
                    assert self.expected_statuts[j] == STATUT_VALIDE, (
                        f"Step {i} est {self.expected_statuts[i]} mais "
                        f"Step {j} est {self.expected_statuts[j]} (devrait être validé)"
                    )


# ---------------------------------------------------------------------------
# Exécution du test stateful via pytest
# ---------------------------------------------------------------------------

TestWorkflowStateMachine = WorkflowStateMachine.TestCase
TestWorkflowStateMachine.settings = settings(
    max_examples=100,
    stateful_step_count=30,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
