import pytest
import requests
import uuid

# ---------------------------------------------------------------------------
# Constants — do NOT change these
# ---------------------------------------------------------------------------
BASE_URL = "http://localhost:5001"

TEST_USERS = {
    "superadmin": {"email": "superadmin@test.com", "password": "Str0ng!Pass#2024", "role": "superadmin"},
    "merchant":   {"email": "merchant@test.com",   "password": "MerchantPass123!", "role": "merchant"},
    "customer":   {"email": "customer@test.com",   "password": "CustomerPass123!", "role": "customer"},
    "blocked":    {"email": "blocked@test.com",    "password": "BlockedPass123!",  "role": "customer"},
}

LOGIN_ENDPOINT    = "/api/auth/login"
REGISTER_ENDPOINT = "/api/auth/register"
LOGOUT_ENDPOINT   = "/api/auth/logout"
REFRESH_ENDPOINT  = "/api/auth/refresh"

# ---------------------------------------------------------------------------
# Fixtures — Provided by conftest.py
# Available: base_url, requests_session, auth_headers, merchant_headers, customer_headers
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Helper — do NOT change it
# ---------------------------------------------------------------------------
def login(session, base_url, email, password):
    """POST /api/auth/login and return the full response."""
    return session.post(
        f"{base_url}{LOGIN_ENDPOINT}",
        json={"email": email, "password": password},
    )

# ===========================================================================
# GENERATED TEST CASES START BELOW
# Rules:
# 1. Use 'accessToken' (camelCase) for token assertions/extractions.
# 2. Response structure: {"success": True, "accessToken": "...", "user": {...}}
# 3. Use fixtures: auth_headers (Superadmin), merchant_headers, customer_headers.
# 4. Clean up any data created during tests.
# ===========================================================================

# ---------------------------------------------------------------------------
# EXAMPLE: Valid Login (AI will replace this with specific feature tests)
# ---------------------------------------------------------------------------
@pytest.mark.smoke
@pytest.mark.regression
def test_login_successful_structure_check(requests_session, base_url):
    """Verify login returns the correct data contract."""
    resp = login(requests_session, base_url,
                 TEST_USERS["customer"]["email"],
                 TEST_USERS["customer"]["password"])
    
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    data = resp.json()
    
    # Asserting the dynamic contract keys
    assert data.get("success") is True
    assert "accessToken" in data, "Property 'accessToken' missing from response"
    assert "user" in data, "User object missing from response"
    assert data["user"]["email"] == TEST_USERS["customer"]["email"]

# ---------------------------------------------------------------------------
# EXAMPLE: Authenticated Action
# ---------------------------------------------------------------------------
@pytest.mark.regression
def test_logout_with_bearer_token(requests_session, base_url, customer_headers):
    """Verify logout works using the customer_headers fixture."""
    resp = requests_session.post(
        f"{base_url}{LOGOUT_ENDPOINT}",
        headers=customer_headers,
    )
    assert resp.status_code == 200, f"Logout failed: {resp.text}"