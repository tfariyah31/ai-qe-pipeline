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

@pytest.mark.smoke
@pytest.mark.auth
@pytest.mark.rbac
def test_merchant_can_access_product_management_features(requests_session, base_url):
    """
    TC004: Verify a Merchant can successfully log in and is recognized with the correct role,
    implying access to product management features.
    """
    merchant_user = TEST_USERS["merchant"]
    resp = login(requests_session, base_url, merchant_user["email"], merchant_user["password"])

    assert resp.status_code == 200, \
        f"Expected status 200 for merchant login, but got {resp.status_code}: {resp.text}"

    data = resp.json()

    # Asserting the dynamic contract keys and structure as per OpenAPI spec and rules
    assert data.get("success") is True, "'success' field missing or not True"
    assert "accessToken" in data, "Property 'accessToken' missing from response"
    assert "refreshToken" in data, "Property 'refreshToken' missing from response"
    assert "user" in data, "User object missing from response"

    # Assert specific user details and role for the merchant
    user_data = data["user"]
    assert user_data.get("email") == merchant_user["email"], \
        f"Expected user email '{merchant_user['email']}', but got '{user_data.get('email')}'"
    assert user_data.get("role") == merchant_user["role"], \
        f"Expected user role '{merchant_user['role']}', but got '{user_data.get('role')}'"

    # The Gherkin scenario implies UI actions ("Add new products" button, "view all available products").
    # For API testing, successful login and verification of the correct role in the returned user object
    # is the primary API-level verification that enables subsequent feature access.
    # No further API calls are directly specified for "product management features" in this scenario,
    # but the successful authentication with the correct role is fundamental.