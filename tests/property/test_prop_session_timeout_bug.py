"""Test par propriété — Bug Condition: Token expiré sans déconnexion automatique.

# Feature: session-timeout-auto-logout, Property 1: Bug Condition

**Validates: Requirements 1.1, 1.2, 1.3, 1.4**

Ce test vérifie que le code actuel (non corrigé) NE gère PAS correctement
l'expiration du token JWT. Il est ATTENDU que ces tests ÉCHOUENT sur le code
non corrigé, prouvant ainsi l'existence du bug.

Le bug : lorsque le token JWT expire après 1 heure d'inactivité, ni le site
local ni le site central ne déconnectent automatiquement l'utilisateur.

Stratégie : Analyser le code source TypeScript pour vérifier que :
- L'intercepteur axios (site local) ne gère PAS les réponses 401 avec logout/redirect
- handleResponse (site central) ne gère PAS les 401 avec logout/redirect
- Il n'existe PAS de fonction isTokenExpired()
- Il n'existe PAS de listener visibilitychange qui vérifie l'expiration du token
"""

import base64
import json
import re
import time
from pathlib import Path
from typing import Optional

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st


# ---------------------------------------------------------------------------
# Paths to source files
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]

LOCAL_API_TS = REPO_ROOT / "local-site" / "web" / "frontend" / "src" / "lib" / "api.ts"
CENTRAL_API_TS = REPO_ROOT / "central-site" / "web" / "frontend" / "src" / "lib" / "api.ts"
CENTRAL_AUTH_CONTEXT = (
    REPO_ROOT / "central-site" / "web" / "frontend" / "src" / "contexts" / "AuthContext.tsx"
)
LOCAL_AUTH_TS = REPO_ROOT / "local-site" / "web" / "frontend" / "src" / "lib" / "auth.ts"
CENTRAL_AUTH_TS = REPO_ROOT / "central-site" / "web" / "frontend" / "src" / "lib" / "auth.ts"


# ---------------------------------------------------------------------------
# Helpers: JWT token generation for testing
# ---------------------------------------------------------------------------


def make_jwt_payload(exp: int, sub: str = "user@test.com") -> str:
    """Create a fake JWT token with the given expiration timestamp."""
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": sub, "exp": exp, "iat": exp - 3600}).encode()
    ).rstrip(b"=").decode()
    signature = base64.urlsafe_b64encode(b"fakesignature").rstrip(b"=").decode()
    return f"{header}.{payload}.{signature}"


def decode_jwt_exp(token: str) -> Optional[int]:
    """Decode the exp field from a JWT token payload."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        payload_b64 = parts[1]
        # Add padding
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload_json = base64.urlsafe_b64decode(payload_b64)
        payload = json.loads(payload_json)
        return payload.get("exp")
    except Exception:
        return None


def is_bug_condition(token: Optional[str], current_time: float) -> bool:
    """
    Returns True when the bug condition is met:
    token is NOT null AND currentTime > token.exp
    """
    if token is None:
        return False
    exp = decode_jwt_exp(token)
    if exp is None:
        return False
    return current_time > exp


# ---------------------------------------------------------------------------
# Hypothesis strategies: generate expired token scenarios
# ---------------------------------------------------------------------------

# Strategy for generating expired tokens (exp in the past)
@st.composite
def expired_token_strategy(draw):
    """Generate a session state where the token is expired (bug condition is true)."""
    # Token expired between 1 second and 2 hours ago
    seconds_expired = draw(st.integers(min_value=1, max_value=7200))
    current_time = time.time()
    exp = int(current_time) - seconds_expired
    token = make_jwt_payload(exp)
    return {
        "token": token,
        "current_time": current_time,
        "exp": exp,
        "seconds_expired": seconds_expired,
    }


# ---------------------------------------------------------------------------
# Source code analysis helpers
# ---------------------------------------------------------------------------


def read_source(path: Path) -> str:
    """Read a source file, return empty string if not found."""
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def has_401_interceptor_with_logout(source: str) -> bool:
    """
    Check if the source code contains a 401 response interceptor that:
    - Detects status 401
    - Removes token from localStorage
    - Redirects to home page
    """
    # Look for patterns indicating 401 handling with logout
    has_401_check = bool(
        re.search(r"(status\s*===?\s*401|\.status\s*===?\s*401)", source)
        and re.search(r"(localStorage\.removeItem|clearToken)", source)
        and re.search(r"(window\.location|redirect|router\.push)", source)
    )
    # Must be in the context of an interceptor or error handler
    has_interceptor_context = bool(
        re.search(r"interceptors\.response", source)
        or re.search(r"error.*401", source, re.DOTALL)
    )
    return has_401_check and has_interceptor_context


def has_401_handling_in_handle_response(source: str) -> bool:
    """
    Check if handleResponse handles 401 by clearing token and redirecting.
    """
    # Look for 401 handling within handleResponse or similar
    has_401_check = bool(
        re.search(r"(status\s*===?\s*401|res\.status\s*===?\s*401)", source)
    )
    has_token_clear = bool(
        re.search(r"localStorage\.removeItem\s*\(\s*[\"']judi_access_token[\"']\s*\)", source)
    )
    has_redirect = bool(
        re.search(r"window\.location", source)
    )
    return has_401_check and has_token_clear and has_redirect


def has_is_token_expired_function(source: str) -> bool:
    """Check if the source contains an isTokenExpired function."""
    return bool(
        re.search(r"(function\s+isTokenExpired|const\s+isTokenExpired|export\s+function\s+isTokenExpired)", source)
    )


def has_visibility_change_with_token_check(source: str) -> bool:
    """
    Check if the source has a visibilitychange listener that checks token expiration.
    """
    has_visibility_listener = bool(
        re.search(r"visibilitychange", source)
    )
    has_token_check = bool(
        re.search(r"isTokenExpired", source)
    )
    return has_visibility_listener and has_token_check


# ---------------------------------------------------------------------------
# Property-based tests: Bug Condition Exploration
# ---------------------------------------------------------------------------


class TestLocalSite401Handling:
    """
    Test that the local site axios interceptor handles 401 responses
    by clearing the token and redirecting to /accueil.

    EXPECTED: These tests FAIL on unfixed code (proving the bug exists).
    """

    @settings(max_examples=10, deadline=None)
    @given(session=expired_token_strategy())
    def test_local_site_401_interceptor_clears_token_and_redirects(
        self, session: dict
    ) -> None:
        """
        Property: For any expired token (isBugCondition=true), the local site
        axios interceptor SHOULD handle 401 by calling localStorage.removeItem("token")
        AND redirecting to /accueil.

        We verify this by checking the source code contains the expected behavior.
        """
        # Confirm bug condition
        assert is_bug_condition(session["token"], session["current_time"])

        # Read the actual source code
        source = read_source(LOCAL_API_TS)
        assert source, f"Source file not found: {LOCAL_API_TS}"

        # The source SHOULD contain 401 interceptor with logout logic
        # On unfixed code, this will FAIL (proving the bug exists)
        assert has_401_interceptor_with_logout(source), (
            f"BUG CONFIRMED: Local site axios interceptor does NOT handle 401 "
            f"with token removal and redirect. "
            f"Token expired {session['seconds_expired']}s ago (exp={session['exp']}), "
            f"user would remain on authenticated page with no redirection to /accueil."
        )


class TestCentralSite401Handling:
    """
    Test that the central site handleResponse handles 401 responses
    by clearing judi_access_token and redirecting to /.

    EXPECTED: These tests FAIL on unfixed code (proving the bug exists).
    """

    @settings(max_examples=10, deadline=None)
    @given(session=expired_token_strategy())
    def test_central_site_handle_response_clears_token_and_redirects(
        self, session: dict
    ) -> None:
        """
        Property: For any expired token (isBugCondition=true), the central site
        handleResponse SHOULD detect 401, remove judi_access_token from localStorage,
        and redirect to /.

        We verify this by checking the source code contains the expected behavior.
        """
        assert is_bug_condition(session["token"], session["current_time"])

        source = read_source(CENTRAL_API_TS)
        assert source, f"Source file not found: {CENTRAL_API_TS}"

        # The source SHOULD contain 401 handling with token clear and redirect
        # On unfixed code, this will FAIL (proving the bug exists)
        assert has_401_handling_in_handle_response(source), (
            f"BUG CONFIRMED: Central site handleResponse does NOT handle 401 "
            f"with token removal and redirect to /. "
            f"Token expired {session['seconds_expired']}s ago (exp={session['exp']}), "
            f"user would remain on authenticated page with no redirection."
        )


class TestIsTokenExpiredFunction:
    """
    Test that an isTokenExpired() utility function exists and correctly
    identifies expired tokens.

    EXPECTED: These tests FAIL on unfixed code (no such function exists).
    """

    @settings(max_examples=10, deadline=None)
    @given(session=expired_token_strategy())
    def test_local_site_has_is_token_expired(self, session: dict) -> None:
        """
        Property: For any token with exp < currentTime, there SHOULD exist
        an isTokenExpired() function in the local site that returns true.

        We verify the function exists in the source code.
        """
        assert is_bug_condition(session["token"], session["current_time"])

        # Check local-site lib/auth.ts or lib/api.ts for isTokenExpired
        local_auth_source = read_source(LOCAL_AUTH_TS)
        local_api_source = read_source(LOCAL_API_TS)
        combined_source = local_auth_source + local_api_source

        assert has_is_token_expired_function(combined_source), (
            f"BUG CONFIRMED: No isTokenExpired() function found in local site. "
            f"Token expired {session['seconds_expired']}s ago (exp={session['exp']}), "
            f"but there is no client-side mechanism to detect token expiration."
        )

    @settings(max_examples=10, deadline=None)
    @given(session=expired_token_strategy())
    def test_central_site_has_is_token_expired(self, session: dict) -> None:
        """
        Property: For any token with exp < currentTime, there SHOULD exist
        an isTokenExpired() function in the central site that returns true.

        We verify the function exists in the source code.
        """
        assert is_bug_condition(session["token"], session["current_time"])

        # Check central-site lib/auth.ts or contexts/AuthContext.tsx
        central_auth_source = read_source(CENTRAL_AUTH_TS)
        central_api_source = read_source(CENTRAL_API_TS)
        central_context_source = read_source(CENTRAL_AUTH_CONTEXT)
        combined_source = central_auth_source + central_api_source + central_context_source

        assert has_is_token_expired_function(combined_source), (
            f"BUG CONFIRMED: No isTokenExpired() function found in central site. "
            f"Token expired {session['seconds_expired']}s ago (exp={session['exp']}), "
            f"but there is no client-side mechanism to detect token expiration."
        )


class TestVisibilityChangeTokenCheck:
    """
    Test that a visibilitychange event listener exists that checks token
    expiration when the user returns to the tab.

    EXPECTED: These tests FAIL on unfixed code (no such listener exists).
    """

    @settings(max_examples=10, deadline=None)
    @given(session=expired_token_strategy())
    def test_local_site_visibility_change_triggers_logout(self, session: dict) -> None:
        """
        Property: For any expired token, when the tab becomes visible again,
        the local site SHOULD check isTokenExpired() and trigger logout.

        We verify the visibilitychange listener exists in the source code.
        """
        assert is_bug_condition(session["token"], session["current_time"])

        # Check all relevant local site source files
        local_api_source = read_source(LOCAL_API_TS)
        local_auth_source = read_source(LOCAL_AUTH_TS)

        # Also check for a useSessionGuard hook
        hooks_dir = REPO_ROOT / "local-site" / "web" / "frontend" / "src" / "hooks"
        hook_source = ""
        if hooks_dir.exists():
            for f in hooks_dir.glob("*.ts"):
                hook_source += f.read_text(encoding="utf-8")
            for f in hooks_dir.glob("*.tsx"):
                hook_source += f.read_text(encoding="utf-8")

        combined_source = local_api_source + local_auth_source + hook_source

        assert has_visibility_change_with_token_check(combined_source), (
            f"BUG CONFIRMED: No visibilitychange listener with token expiration check "
            f"found in local site. "
            f"Token expired {session['seconds_expired']}s ago (exp={session['exp']}), "
            f"user returning to tab after inactivity would NOT be logged out."
        )

    @settings(max_examples=10, deadline=None)
    @given(session=expired_token_strategy())
    def test_central_site_visibility_change_triggers_logout(self, session: dict) -> None:
        """
        Property: For any expired token, when the tab becomes visible again,
        the central site SHOULD check isTokenExpired() and trigger logout.

        We verify the visibilitychange listener exists in the source code.
        """
        assert is_bug_condition(session["token"], session["current_time"])

        # Check central site AuthContext and api.ts
        central_context_source = read_source(CENTRAL_AUTH_CONTEXT)
        central_api_source = read_source(CENTRAL_API_TS)
        central_auth_source = read_source(CENTRAL_AUTH_TS)
        combined_source = central_context_source + central_api_source + central_auth_source

        assert has_visibility_change_with_token_check(combined_source), (
            f"BUG CONFIRMED: No visibilitychange listener with token expiration check "
            f"found in central site (AuthContext). "
            f"Token expired {session['seconds_expired']}s ago (exp={session['exp']}), "
            f"user returning to tab after inactivity would NOT be logged out."
        )
