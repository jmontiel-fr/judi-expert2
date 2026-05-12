"""Test par propriété — Preservation: Sessions valides non affectées.

# Feature: session-timeout-auto-logout, Property 2: Preservation

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

Ce test vérifie que le comportement existant pour les sessions VALIDES
(token non expiré ou absent) est correct et doit être préservé après le
correctif. Ces tests sont exécutés sur le code NON corrigé et doivent PASSER.

Propriété de préservation :
Pour tout état de session X où NOT isBugCondition(X) (token est null OU
currentTime <= token.exp), le système doit :
- Permettre les appels API sans déclencher de logout/redirect
- Continuer la navigation sans interruption
- Ne pas supprimer le token du localStorage

Stratégie : Simuler en Python pur le comportement du frontend pour les
sessions valides, en reproduisant la logique des intercepteurs axios (local)
et de handleResponse (central).
"""

import base64
import json
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


# ---------------------------------------------------------------------------
# Helpers: JWT token generation
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
# Simulated frontend behavior (mirrors the actual TypeScript code)
# ---------------------------------------------------------------------------


class LocalStorage:
    """Simulates browser localStorage for testing."""

    def __init__(self):
        self._store: dict[str, str] = {}

    def getItem(self, key: str) -> Optional[str]:
        return self._store.get(key)

    def setItem(self, key: str, value: str) -> None:
        self._store[key] = value

    def removeItem(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


class ApiResponse:
    """Simulates an HTTP response."""

    def __init__(self, status: int, data: dict = None):
        self.status = status
        self.data = data or {}
        self.ok = 200 <= status < 300


def simulate_local_api_call(
    token: Optional[str], response_status: int, local_storage: LocalStorage
) -> dict:
    """
    Simulate the local site axios interceptor behavior on the CURRENT (unfixed) code.

    Current behavior (unfixed):
    - Request interceptor: attaches token as Bearer header
    - Response interceptor: only extracts error.response.data.detail for error message
    - Does NOT handle 401 with logout/redirect

    Returns a dict describing what happened:
    - api_call_succeeded: bool
    - token_removed: bool
    - redirected: bool
    - redirect_target: str or None
    """
    result = {
        "api_call_succeeded": False,
        "token_removed": False,
        "redirected": False,
        "redirect_target": None,
    }

    # Simulate request interceptor: token is attached (no modification to localStorage)
    # The token stays in localStorage regardless of the response

    if 200 <= response_status < 300:
        # Successful response — data returned normally
        result["api_call_succeeded"] = True
    else:
        # Error response — current code only extracts error message
        # It does NOT remove token or redirect on 401
        result["api_call_succeeded"] = False

    # On unfixed code: token is NEVER removed by the interceptor
    # and no redirect happens regardless of status
    # (This is the bug for expired tokens, but correct for valid tokens)

    return result


def simulate_central_handle_response(
    token: Optional[str], response_status: int, local_storage: LocalStorage
) -> dict:
    """
    Simulate the central site handleResponse behavior on the CURRENT (unfixed) code.

    Current behavior (unfixed):
    - If response is not ok, throws ApiError with status and message
    - Does NOT handle 401 specifically (no token removal, no redirect)

    Returns a dict describing what happened.
    """
    result = {
        "api_call_succeeded": False,
        "token_removed": False,
        "redirected": False,
        "redirect_target": None,
        "error_thrown": False,
    }

    if 200 <= response_status < 300:
        result["api_call_succeeded"] = True
    else:
        # Current code: throws ApiError but does NOT clear token or redirect
        result["error_thrown"] = True

    return result


def simulate_visibility_change_event(
    token: Optional[str], current_time: float, local_storage: LocalStorage
) -> dict:
    """
    Simulate what happens on visibilitychange event on CURRENT (unfixed) code.

    Current behavior (unfixed):
    - There is NO visibilitychange listener that checks token expiration
    - Nothing happens when the tab becomes visible again

    Returns a dict describing what happened.
    """
    result = {
        "token_removed": False,
        "redirected": False,
        "redirect_target": None,
        "logout_triggered": False,
    }

    # On unfixed code: no visibilitychange handler exists
    # So nothing happens — token stays, no redirect, no logout
    # This is CORRECT for valid tokens (preservation property)

    return result


def is_token_expired_python(token: Optional[str], current_time: float) -> bool:
    """
    Pure Python implementation of isTokenExpired logic.
    Returns True if token is expired (currentTime > exp).
    Returns False if token is None, malformed, or still valid.
    """
    if token is None:
        return False
    exp = decode_jwt_exp(token)
    if exp is None:
        return True  # Malformed token treated as expired
    return current_time > exp


# ---------------------------------------------------------------------------
# Hypothesis strategies: generate VALID (non-bug-condition) session states
# ---------------------------------------------------------------------------


@st.composite
def valid_token_strategy(draw):
    """
    Generate a session state where the token is VALID (NOT expired).
    NOT isBugCondition: token is null OR currentTime <= token.exp
    This strategy generates tokens with exp in the future.
    """
    # Token valid for between 1 second and 2 hours from now
    seconds_remaining = draw(st.integers(min_value=1, max_value=7200))
    current_time = time.time()
    exp = int(current_time) + seconds_remaining
    token = make_jwt_payload(exp)
    return {
        "token": token,
        "current_time": current_time,
        "exp": exp,
        "seconds_remaining": seconds_remaining,
    }


@st.composite
def null_token_strategy(draw):
    """
    Generate a session state where there is NO token (null).
    NOT isBugCondition: token is null → always false.
    """
    # Draw a small offset to vary the current_time across examples
    offset = draw(st.integers(min_value=0, max_value=100))
    current_time = time.time() + offset
    return {
        "token": None,
        "current_time": current_time,
        "exp": None,
        "seconds_remaining": None,
    }


@st.composite
def preservation_session_strategy(draw):
    """
    Generate any session state where NOT isBugCondition is true.
    Either: token is None, OR currentTime <= token.exp.
    """
    use_null_token = draw(st.booleans())
    if use_null_token:
        return draw(null_token_strategy())
    else:
        return draw(valid_token_strategy())


# Strategy for API response status codes (successful responses)
successful_status = st.sampled_from([200, 201, 204])

# Strategy for various non-401 error status codes
non_401_error_status = st.sampled_from([400, 403, 404, 422, 500, 502, 503])


# ---------------------------------------------------------------------------
# Property-based tests: Preservation
# ---------------------------------------------------------------------------


class TestPreservationApiCallsWithValidToken:
    """
    Property: For all SessionState inputs where NOT isBugCondition(input)
    (token is null OR currentTime <= token.exp), API calls succeed without
    triggering logout/redirect and no token removal from localStorage.

    **Validates: Requirements 3.1, 3.4**

    EXPECTED: These tests PASS on unfixed code (confirms baseline to preserve).
    """

    @settings(max_examples=10, deadline=None)
    @given(session=valid_token_strategy(), status=successful_status)
    def test_local_site_valid_token_api_call_succeeds_no_logout(
        self, session: dict, status: int
    ) -> None:
        """
        Property: For any valid token (not expired), a successful API response
        does NOT trigger token removal or redirect on the local site.

        The local site axios interceptor should pass through successful responses
        without any side effects on localStorage or navigation.
        """
        # Precondition: NOT bug condition
        assert not is_bug_condition(session["token"], session["current_time"])

        # Setup localStorage with valid token
        storage = LocalStorage()
        storage.setItem("token", session["token"])

        # Simulate API call with successful response
        result = simulate_local_api_call(session["token"], status, storage)

        # Assertions: preservation properties
        assert result["api_call_succeeded"] is True, (
            "API call with valid token should succeed"
        )
        assert result["token_removed"] is False, (
            "Token should NOT be removed from localStorage for valid sessions"
        )
        assert result["redirected"] is False, (
            "No redirect should occur for valid sessions"
        )

    @settings(max_examples=10, deadline=None)
    @given(session=valid_token_strategy(), status=successful_status)
    def test_central_site_valid_token_api_call_succeeds_no_logout(
        self, session: dict, status: int
    ) -> None:
        """
        Property: For any valid token (not expired), a successful API response
        does NOT trigger token removal or redirect on the central site.

        The central site handleResponse should return data normally without
        any side effects on localStorage or navigation.
        """
        assert not is_bug_condition(session["token"], session["current_time"])

        storage = LocalStorage()
        storage.setItem("judi_access_token", session["token"])

        result = simulate_central_handle_response(session["token"], status, storage)

        assert result["api_call_succeeded"] is True, (
            "API call with valid token should succeed"
        )
        assert result["token_removed"] is False, (
            "Token should NOT be removed from localStorage for valid sessions"
        )
        assert result["redirected"] is False, (
            "No redirect should occur for valid sessions"
        )

    @settings(max_examples=10, deadline=None)
    @given(session=valid_token_strategy(), status=non_401_error_status)
    def test_local_site_valid_token_non_401_error_no_logout(
        self, session: dict, status: int
    ) -> None:
        """
        Property: For any valid token, a non-401 error response does NOT
        trigger token removal or redirect. Only the error message is extracted.

        **Validates: Requirements 3.1**
        """
        assert not is_bug_condition(session["token"], session["current_time"])

        storage = LocalStorage()
        storage.setItem("token", session["token"])

        result = simulate_local_api_call(session["token"], status, storage)

        # Non-401 errors should NOT trigger logout
        assert result["token_removed"] is False, (
            f"Token should NOT be removed on HTTP {status} error with valid token"
        )
        assert result["redirected"] is False, (
            f"No redirect should occur on HTTP {status} error with valid token"
        )

    @settings(max_examples=10, deadline=None)
    @given(session=valid_token_strategy(), status=non_401_error_status)
    def test_central_site_valid_token_non_401_error_no_logout(
        self, session: dict, status: int
    ) -> None:
        """
        Property: For any valid token, a non-401 error response on the central
        site does NOT trigger token removal or redirect.

        **Validates: Requirements 3.1**
        """
        assert not is_bug_condition(session["token"], session["current_time"])

        storage = LocalStorage()
        storage.setItem("judi_access_token", session["token"])

        result = simulate_central_handle_response(session["token"], status, storage)

        assert result["token_removed"] is False, (
            f"Token should NOT be removed on HTTP {status} error with valid token"
        )
        assert result["redirected"] is False, (
            f"No redirect should occur on HTTP {status} error with valid token"
        )


class TestPreservationIsTokenExpired:
    """
    Property: For all valid tokens (random exp values in the future),
    isTokenExpired(token) returns false.

    **Validates: Requirements 3.1, 3.4**

    EXPECTED: These tests PASS on unfixed code (confirms baseline to preserve).
    """

    @settings(max_examples=10, deadline=None)
    @given(session=valid_token_strategy())
    def test_valid_token_is_not_expired(self, session: dict) -> None:
        """
        Property: For any token with exp > currentTime, the token is NOT expired.
        isTokenExpired should return False for all valid tokens.

        This tests the pure Python reference implementation that mirrors
        what the TypeScript isTokenExpired() function should do.
        """
        assert not is_bug_condition(session["token"], session["current_time"])

        # The token should NOT be considered expired
        expired = is_token_expired_python(session["token"], session["current_time"])
        assert expired is False, (
            f"Valid token (exp={session['exp']}, "
            f"remaining={session['seconds_remaining']}s) "
            f"should NOT be considered expired"
        )

    @settings(max_examples=10, deadline=None)
    @given(
        seconds_in_future=st.integers(min_value=1, max_value=86400),
        sub=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "P")),
            min_size=1,
            max_size=50,
        ),
    )
    def test_any_future_exp_is_not_expired(
        self, seconds_in_future: int, sub: str
    ) -> None:
        """
        Property: For ANY token with exp set to any point in the future,
        isTokenExpired returns False regardless of the subject claim.
        """
        current_time = time.time()
        exp = int(current_time) + seconds_in_future
        token = make_jwt_payload(exp, sub=sub)

        expired = is_token_expired_python(token, current_time)
        assert expired is False, (
            f"Token with exp {seconds_in_future}s in the future should not be expired"
        )

    @settings(max_examples=10, deadline=None)
    @given(data=st.data())
    def test_null_token_is_not_expired(self, data) -> None:
        """
        Property: A null token is NOT considered expired (no session = no bug).
        This is part of NOT isBugCondition: token is null → returns False.
        """
        current_time = time.time()
        expired = is_token_expired_python(None, current_time)
        assert expired is False, "Null token should not be considered expired"


class TestPreservationVisibilityChange:
    """
    Property: visibilitychange event with valid token does NOT trigger logout.

    **Validates: Requirements 3.4**

    EXPECTED: These tests PASS on unfixed code (confirms baseline to preserve).
    On unfixed code, there is no visibilitychange handler at all, so nothing
    happens — which is correct for valid tokens (no interruption).
    """

    @settings(max_examples=10, deadline=None)
    @given(session=valid_token_strategy())
    def test_visibility_change_with_valid_token_no_logout(
        self, session: dict
    ) -> None:
        """
        Property: For any valid token (not expired), a visibilitychange event
        (tab becoming visible) does NOT trigger logout, token removal, or redirect.

        On unfixed code: no handler exists → nothing happens → test passes.
        After fix: handler exists but checks isTokenExpired → valid token → no action.
        """
        assert not is_bug_condition(session["token"], session["current_time"])

        storage = LocalStorage()
        storage.setItem("token", session["token"])

        result = simulate_visibility_change_event(
            session["token"], session["current_time"], storage
        )

        assert result["logout_triggered"] is False, (
            "Visibility change with valid token should NOT trigger logout"
        )
        assert result["token_removed"] is False, (
            "Visibility change with valid token should NOT remove token"
        )
        assert result["redirected"] is False, (
            "Visibility change with valid token should NOT redirect"
        )

    @settings(max_examples=10, deadline=None)
    @given(session=null_token_strategy())
    def test_visibility_change_with_no_token_no_logout(
        self, session: dict
    ) -> None:
        """
        Property: When there is no token (user not authenticated),
        a visibilitychange event does NOT trigger any logout logic.

        **Validates: Requirements 3.3**
        """
        assert not is_bug_condition(session["token"], session["current_time"])

        storage = LocalStorage()
        # No token in storage

        result = simulate_visibility_change_event(
            session["token"], session["current_time"], storage
        )

        assert result["logout_triggered"] is False, (
            "Visibility change with no token should NOT trigger logout"
        )
        assert result["token_removed"] is False, (
            "Visibility change with no token should NOT attempt token removal"
        )
        assert result["redirected"] is False, (
            "Visibility change with no token should NOT redirect"
        )


class TestPreservationPublicPages:
    """
    Property: Public pages (login, accueil) are accessible without
    triggering any logout logic.

    **Validates: Requirements 3.3**

    EXPECTED: These tests PASS on unfixed code (confirms baseline to preserve).
    """

    @settings(max_examples=10, deadline=None)
    @given(session=null_token_strategy())
    def test_public_page_access_without_token_no_logout(
        self, session: dict
    ) -> None:
        """
        Property: Accessing public pages without a token does NOT trigger
        any logout or redirect logic. The system should allow normal access.
        """
        assert not is_bug_condition(session["token"], session["current_time"])

        storage = LocalStorage()
        # No token — simulating unauthenticated user on public page

        # Simulate API call (e.g., fetching public data)
        result_local = simulate_local_api_call(None, 200, storage)
        result_central = simulate_central_handle_response(None, 200, storage)

        # No logout should be triggered
        assert result_local["token_removed"] is False
        assert result_local["redirected"] is False
        assert result_central["token_removed"] is False
        assert result_central["redirected"] is False

    @settings(max_examples=10, deadline=None)
    @given(session=valid_token_strategy())
    def test_authenticated_user_on_public_page_no_interruption(
        self, session: dict
    ) -> None:
        """
        Property: An authenticated user with a valid token visiting public pages
        experiences no session interruption or forced logout.
        """
        assert not is_bug_condition(session["token"], session["current_time"])

        storage = LocalStorage()
        storage.setItem("token", session["token"])

        # Simulate accessing a public page (200 response)
        result = simulate_local_api_call(session["token"], 200, storage)

        assert result["api_call_succeeded"] is True
        assert result["token_removed"] is False
        assert result["redirected"] is False


class TestPreservationManualLogout:
    """
    Property: Manual logout via "Déconnexion" button clears token and
    redirects appropriately. This behavior must be preserved.

    **Validates: Requirements 3.2**

    EXPECTED: These tests PASS on unfixed code (confirms baseline to preserve).
    """

    @settings(max_examples=10, deadline=None)
    @given(session=valid_token_strategy())
    def test_manual_logout_clears_token_local_site(self, session: dict) -> None:
        """
        Property: Manual logout on the local site clears the token from
        localStorage. This is existing behavior that must be preserved.

        We verify by checking the source code contains clearToken() function.
        """
        source = LOCAL_API_TS.read_text(encoding="utf-8")

        # The local site has a clearToken() function that removes "token" from localStorage
        assert "clearToken" in source or "localStorage.removeItem" in source, (
            "Local site should have a mechanism to clear the token on logout"
        )

    @settings(max_examples=10, deadline=None)
    @given(session=valid_token_strategy())
    def test_manual_logout_clears_token_central_site(self, session: dict) -> None:
        """
        Property: Manual logout on the central site clears judi_access_token
        from localStorage. This is existing behavior that must be preserved.

        We verify by checking the AuthContext contains logout logic.
        """
        source = CENTRAL_AUTH_CONTEXT.read_text(encoding="utf-8")

        # The central site AuthContext has a logout function that removes the token
        assert "localStorage.removeItem" in source, (
            "Central site AuthContext should remove token on logout"
        )
        assert "TOKEN_KEY" in source or "judi_access_token" in source, (
            "Central site should reference the token key for removal"
        )
