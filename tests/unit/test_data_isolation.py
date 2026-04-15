"""Tests d'isolation des données d'expertise.

Vérifie par analyse statique que l'Application Locale ne transmet au Site Central
que les tickets (ticket_code), et que les données d'expertise restent en local.

Valide : Exigences 32.1, 32.2
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

# Root of the local backend source code (resolve relative to project root)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOCAL_BACKEND_ROOT = _PROJECT_ROOT / "local-site" / "web" / "backend"

# Files that are expected to make outbound HTTP calls to SITE_CENTRAL_URL
# These are the ONLY files allowed to call the Site Central
ALLOWED_OUTBOUND_FILES = {
    str(Path("routers/dossiers.py")),
    str(Path("routers/tickets.py")),
    str(Path("routers/config.py")),
}

# Pattern matching httpx calls that send JSON bodies to SITE_CENTRAL_URL
HTTPX_POST_PATTERN = re.compile(
    r"""client\.post\s*\(\s*[^)]*json\s*=\s*\{([^}]*)\}""",
    re.DOTALL,
)

# Pattern matching references to SITE_CENTRAL_URL
SITE_CENTRAL_REF_PATTERN = re.compile(r"SITE_CENTRAL_URL")

# Add local backend to sys.path for middleware imports
_BACKEND_PATH = str(
    Path(__file__).resolve().parents[2]
    / "local-site"
    / "web"
    / "backend"
)
if _BACKEND_PATH not in sys.path:
    sys.path.insert(0, _BACKEND_PATH)


def _get_python_files(root: Path) -> list[Path]:
    """Collect all .py files under the given root."""
    return sorted(root.rglob("*.py"))


def _extract_json_keys_from_post_calls(source: str) -> list[set[str]]:
    """Extract the keys from json={...} arguments in httpx post calls."""
    results = []
    for match in HTTPX_POST_PATTERN.finditer(source):
        inner = match.group(1)
        keys = set(re.findall(r'"(\w+)"\s*:', inner))
        results.append(keys)
    return results


def _normalize_path(p: str) -> str:
    """Normalize path separators for cross-platform comparison."""
    return p.replace("\\", "/")


class TestDataIsolationStaticAnalysis:
    """Static analysis tests ensuring data isolation between local app and Site Central."""

    def test_only_allowed_files_reference_site_central(self):
        """Only routers/dossiers.py, routers/tickets.py, routers/config.py should reference SITE_CENTRAL_URL."""
        allowed_normalized = {_normalize_path(f) for f in ALLOWED_OUTBOUND_FILES}
        violating_files = []

        for py_file in _get_python_files(LOCAL_BACKEND_ROOT):
            rel_path = str(py_file.relative_to(LOCAL_BACKEND_ROOT))
            rel_normalized = _normalize_path(rel_path)

            # Skip __pycache__, migrations, and the middleware itself
            if "__pycache__" in rel_normalized or "alembic" in rel_normalized:
                continue
            if "middleware/data_isolation" in rel_normalized:
                continue
            # site_central_client.py is the centralized HTTP client — allowed
            if "services/site_central_client" in rel_normalized:
                continue

            source = py_file.read_text(encoding="utf-8", errors="replace")

            if SITE_CENTRAL_REF_PATTERN.search(source):
                if rel_normalized not in allowed_normalized:
                    if "httpx" in source and ("client.post" in source or "client.get" in source):
                        violating_files.append(rel_normalized)

        assert violating_files == [], (
            f"Les fichiers suivants font des appels HTTP vers SITE_CENTRAL_URL "
            f"mais ne sont pas autorisés : {violating_files}. "
            f"Seuls {allowed_normalized} peuvent communiquer avec le Site Central."
        )

    def test_outbound_calls_only_send_ticket_code(self):
        """All httpx POST calls to SITE_CENTRAL_URL should only send ticket_code in the JSON body."""
        violations = []

        for rel_name in ALLOWED_OUTBOUND_FILES:
            py_file = LOCAL_BACKEND_ROOT / rel_name
            if not py_file.exists():
                continue

            source = py_file.read_text(encoding="utf-8", errors="replace")
            json_key_sets = _extract_json_keys_from_post_calls(source)

            for keys in json_key_sets:
                extra = keys - {"ticket_code"}
                if extra:
                    violations.append(
                        f"{rel_name}: envoie les champs {extra} en plus de ticket_code"
                    )

        assert violations == [], (
            f"Des données non autorisées sont envoyées au Site Central : {violations}. "
            f"Seul 'ticket_code' doit être transmis (Exigence 32.2)."
        )

    def test_no_expertise_data_in_outbound_calls(self):
        """Verify that expertise-related keywords never appear in outbound HTTP call payloads."""
        forbidden_keywords = {
            "markdown", "requisition", "qmec", "ne_content", "reb_content",
            "ref_content", "raux", "pdf_content", "ocr_text", "dossier_data",
            "step_data", "file_content", "rapport",
        }

        violations = []

        for rel_name in ALLOWED_OUTBOUND_FILES:
            py_file = LOCAL_BACKEND_ROOT / rel_name
            if not py_file.exists():
                continue

            source = py_file.read_text(encoding="utf-8", errors="replace")
            json_key_sets = _extract_json_keys_from_post_calls(source)

            for keys in json_key_sets:
                leaked = keys & forbidden_keywords
                if leaked:
                    violations.append(
                        f"{rel_name}: contient des données d'expertise dans le payload : {leaked}"
                    )

        assert violations == [], (
            f"Des données d'expertise sont transmises au Site Central : {violations}. "
            f"Toutes les données d'expertise doivent rester en local (Exigence 32.1)."
        )

    def test_local_services_do_not_call_site_central(self):
        """Services (LLM, RAG, OCR) should only call their local containers, never the Site Central.

        The site_central_client.py is excluded as it IS the centralized client for Site Central.
        """
        services_dir = LOCAL_BACKEND_ROOT / "services"
        if not services_dir.exists():
            pytest.skip("services/ directory not found")

        violating_services = []

        for py_file in services_dir.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            source = py_file.read_text(encoding="utf-8", errors="replace")
            rel_name = _normalize_path(str(py_file.relative_to(LOCAL_BACKEND_ROOT)))

            # site_central_client.py is the centralized HTTP client — allowed
            if "site_central_client" in rel_name:
                continue

            if SITE_CENTRAL_REF_PATTERN.search(source):
                violating_services.append(rel_name)

        assert violating_services == [], (
            f"Les services suivants référencent SITE_CENTRAL_URL : {violating_services}. "
            f"Les services locaux (LLM, RAG, OCR) ne doivent communiquer qu'avec "
            f"leurs conteneurs Docker locaux respectifs."
        )


class TestDataIsolationMiddleware:
    """Tests for the data isolation validation function."""

    def test_valid_ticket_payload(self):
        """A payload with only ticket_code should be valid."""
        from middleware.data_isolation import validate_outbound_payload

        assert validate_outbound_payload(
            {"ticket_code": "ABC123"},
            "https://www.judi-expert.fr/api/tickets/verify",
        ) is True

    def test_empty_payload(self):
        """A None payload should be valid."""
        from middleware.data_isolation import validate_outbound_payload

        assert validate_outbound_payload(
            None,
            "https://www.judi-expert.fr/api/tickets/verify",
        ) is True

    def test_payload_with_extra_fields_rejected(self):
        """A payload with extra fields should be rejected."""
        from middleware.data_isolation import validate_outbound_payload

        assert validate_outbound_payload(
            {"ticket_code": "ABC123", "dossier_data": "secret"},
            "https://www.judi-expert.fr/api/tickets/verify",
        ) is False

    def test_non_central_url_always_valid(self):
        """Payloads to non-Site-Central URLs should always be valid."""
        from middleware.data_isolation import validate_outbound_payload

        assert validate_outbound_payload(
            {"anything": "goes", "data": "here"},
            "http://judi-ocr:8001/api/ocr/extract",
        ) is True
