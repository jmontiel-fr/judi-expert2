"""Tests unitaires — configuration des types de workflow."""

from services.workflow_config import (
    WORKFLOW_SIMPLE,
    WORKFLOW_STANDARD,
    is_simple_workflow,
    normalize_workflow_type,
    step_count_for,
)


def test_normalize_workflow_type_defaults_to_standard():
    assert normalize_workflow_type(None) == WORKFLOW_STANDARD
    assert normalize_workflow_type("invalid") == WORKFLOW_STANDARD


def test_step_count_for_workflows():
    assert step_count_for(WORKFLOW_STANDARD) == 5
    assert step_count_for(WORKFLOW_SIMPLE) == 2


def test_is_simple_workflow():
    assert is_simple_workflow(WORKFLOW_SIMPLE) is True
    assert is_simple_workflow(WORKFLOW_STANDARD) is False
