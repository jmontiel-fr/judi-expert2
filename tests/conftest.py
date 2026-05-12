"""Root conftest — environment setup for all tests.

Sets environment variables required by backend modules that may be imported
during test collection (e.g., central-site/web/backend/main.py needs VERSION_FILE).
"""

import os
from pathlib import Path

# Central-site backend expects VERSION_FILE env var (defaults to /app/VERSION in Docker).
# Point it to the actual file in the repo so tests can import main.py without error.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_CENTRAL_VERSION = _REPO_ROOT / "central-site" / "VERSION"

if _CENTRAL_VERSION.exists() and "VERSION_FILE" not in os.environ:
    os.environ["VERSION_FILE"] = str(_CENTRAL_VERSION)
