"""Configuration des types de workflow dossier (standard vs simple)."""

from __future__ import annotations

WORKFLOW_STANDARD = "standard"
WORKFLOW_SIMPLE = "simple"

VALID_WORKFLOW_TYPES = frozenset({WORKFLOW_STANDARD, WORKFLOW_SIMPLE})

STEP_COUNT_BY_WORKFLOW: dict[str, int] = {
    WORKFLOW_STANDARD: 5,
    WORKFLOW_SIMPLE: 2,
}


def normalize_workflow_type(workflow_type: str | None) -> str:
    """Retourne un type de workflow valide (défaut : standard)."""
    if workflow_type in VALID_WORKFLOW_TYPES:
        return workflow_type
    return WORKFLOW_STANDARD


def step_count_for(workflow_type: str) -> int:
    """Nombre d'étapes pour un type de workflow."""
    return STEP_COUNT_BY_WORKFLOW[normalize_workflow_type(workflow_type)]


def is_simple_workflow(workflow_type: str) -> bool:
    return normalize_workflow_type(workflow_type) == WORKFLOW_SIMPLE
