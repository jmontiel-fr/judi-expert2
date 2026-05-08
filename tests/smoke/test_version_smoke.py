"""Smoke tests for version management.

Validates that VERSION files exist and are correctly formatted,
and that version requests use HTTPS only.

Requirements: 1.1, 9.3, 11.1
"""

import re
import sys
from pathlib import Path

import pytest

# Repo root is 2 levels up from this test file (tests/smoke/test_version_smoke.py)
REPO_ROOT = Path(__file__).resolve().parents[2]

# Add local backend to sys.path for imports
LOCAL_BACKEND = REPO_ROOT / "local-site" / "web" / "backend"
sys.path.insert(0, str(LOCAL_BACKEND))

# Semver pattern: MAJOR.MINOR.PATCH (non-negative integers)
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")

# ISO date pattern: YYYY-MM-DD
ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_version_file(path: Path) -> None:
    """Validate that a VERSION file exists and has the correct 2-line format."""
    assert path.exists(), f"VERSION file not found: {path}"

    content = path.read_text(encoding="utf-8").strip()
    lines = content.splitlines()

    assert len(lines) == 2, (
        f"VERSION file should have exactly 2 lines (semver + ISO date), "
        f"got {len(lines)} lines in {path}"
    )

    version_line = lines[0].strip()
    date_line = lines[1].strip()

    assert SEMVER_PATTERN.match(version_line), (
        f"First line must be semver (MAJOR.MINOR.PATCH), got: '{version_line}' in {path}"
    )
    assert ISO_DATE_PATTERN.match(date_line), (
        f"Second line must be ISO date (YYYY-MM-DD), got: '{date_line}' in {path}"
    )


class TestVersionFileExists:
    """Verify VERSION files exist and have the correct format."""

    def test_version_file_exists_local(self):
        """Verify local-site/VERSION exists and has 2 lines (semver + ISO date).

        Validates: Requirement 1.1
        """
        version_path = REPO_ROOT / "local-site" / "VERSION"
        _validate_version_file(version_path)

    def test_version_file_exists_central(self):
        """Verify central-site/VERSION exists and has 2 lines (semver + ISO date).

        Validates: Requirement 11.1
        """
        version_path = REPO_ROOT / "central-site" / "VERSION"
        _validate_version_file(version_path)

    def test_version_file_exists_app_locale_package(self):
        """Verify central-site/app_locale_package/VERSION exists and matches local-site/VERSION.

        Validates: Requirements 1.1, 14.1
        """
        package_version_path = REPO_ROOT / "central-site" / "app_locale_package" / "VERSION"
        local_version_path = REPO_ROOT / "local-site" / "VERSION"

        _validate_version_file(package_version_path)

        # The app_locale_package VERSION must be synchronized with local-site VERSION
        package_content = package_version_path.read_text(encoding="utf-8").strip()
        local_content = local_version_path.read_text(encoding="utf-8").strip()

        assert package_content == local_content, (
            f"central-site/app_locale_package/VERSION must match local-site/VERSION.\n"
            f"Package: {package_content}\n"
            f"Local:   {local_content}"
        )


class TestHttpsOnly:
    """Verify that version requests use HTTPS only."""

    def test_https_only_for_version_requests(self):
        """Verify that the SiteCentralClient base URL uses HTTPS.

        The default SITE_CENTRAL_URL constant must use the https:// scheme
        to ensure all version check communications are encrypted.

        Validates: Requirement 9.3
        """
        from services.site_central_client import SITE_CENTRAL_URL

        assert SITE_CENTRAL_URL.startswith("https://"), (
            f"SITE_CENTRAL_URL must use HTTPS protocol, got: '{SITE_CENTRAL_URL}'"
        )
