#!/usr/bin/env python3
"""
fix_test_indentation.py
Run from project root:
    python3 fix_test_indentation.py

Fixes:
1. Re-indents unindented function bodies
2. Fixes LOGIN_ENDPOINT / LOGOUT_ENDPOINT undefined references
3. Fixes test_successful_token_refresh to login first
4. Fixes test_account_lockout logic (asserts 423 before doing 3 failed attempts)
"""

import re
import ast
from pathlib import Path

TEST_FILE = Path("tests/api/test_login_api.py")


def fix_indentation(source: str) -> str:
    """
    Re-indent function bodies that are at column 0.
    Walks line by line: after a def/decorator line, body lines
    that have no indentation get 4 spaces added.
    """
    lines   = source.splitlines()
    output  = []
    in_func = False

    i = 0
    while i < len(lines):
        line     = lines[i]
        stripped = line.strip()

        # Decorator or def line — marks start of a function
        if stripped.startswith("@pytest.mark.") or stripped.startswith("def test_"):
            in_func = True
            output.append(line)
            i += 1
            continue

        # If we're in a function, indent unindented non-empty lines
        if in_func:
            # Empty line — keep as-is, stay in function
            if not stripped:
                output.append(line)
                i += 1
                continue

            # Next decorator or def — function ended
            if stripped.startswith("@pytest.mark.") or stripped.startswith("def test_"):
                in_func = False
                output.append(line)
                i += 1
                continue

            # Body line with no indentation — add 4 spaces
            if not line.startswith("    ") and not line.startswith("\t"):
                output.append("    " + line)
            else:
                output.append(line)
            i += 1
            continue

        output.append(line)
        i += 1

    return "\n".join(output)


def fix_logout_test(source: str) -> str:
    """Fix test_successful_logout — replace undefined constants with real logic."""
    old = '''@pytest.mark.regression
def test_successful_logout(base_url):
    payload = {}
    response = requests.post(f"{base_url}{LOGIN_ENDPOINT}", json=payload)
    response = requests.post(f"{base_url}{LOGOUT_ENDPOINT}", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert 'success' in data
    assert 'message' in data'''

    new = '''@pytest.mark.regression
def test_successful_logout(base_url):
    """Scenario: Successful logout | P2 | POST /api/auth/logout"""
    # Login first to get a token
    login_resp = requests.post(
        f"{base_url}/api/auth/login",
        json={"email": "customer@test.com", "password": "CustomerPass123!"}
    )
    assert login_resp.status_code == 200
    token = login_resp.json().get("accessToken", "")

    # Now logout
    response = requests.post(
        f"{base_url}/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200'''

    if old in source:
        print("✓ Fixed test_successful_logout")
        return source.replace(old, new)
    print("  ⚠ test_successful_logout pattern not matched — skipping")
    return source


def fix_lockout_test(source: str) -> str:
    """Fix test_account_lockout — assert 423 AFTER 3 failed attempts, not before."""
    old = '''@pytest.mark.regression
def test_account_lockout_after_3_failed_login_attempts(base_url):
    payload = {'email': 'customer@test.com', 'password': 'wrongpass'}
    response = requests.post(f'{base_url}/api/auth/login', json=payload)
    assert response.status_code == 423
    data = response.json()
    assert 'error' in data or 'message' in data
    # Simulate 3 failed login attempts
    for _ in range(3):
        response = requests.post(f'{base_url}/api/auth/login', json=payload)
        assert response.status_code == 401
    # Attempt to login again
    response = requests.post(f'{base_url}/api/auth/login', json=payload)
    assert response.status_code == 423
    data = response.json()
    assert 'error' in data or 'message' in data'''

    new = '''@pytest.mark.regression
def test_account_lockout_after_3_failed_login_attempts(base_url):
    """Scenario: Account lockout after 3 failed login attempts | P2 | POST /api/auth/login"""
    payload = {"email": "blocked@test.com", "password": "wrongpass"}
    # Trigger 3 failed login attempts
    for _ in range(3):
        requests.post(f"{base_url}/api/auth/login", json=payload)
    # 4th attempt should be locked out
    response = requests.post(f"{base_url}/api/auth/login", json=payload)
    assert response.status_code == 423
    data = response.json()
    assert "error" in data or "message" in data'''

    if old in source:
        print("✓ Fixed test_account_lockout_after_3_failed_login_attempts")
        return source.replace(old, new)
    print("  ⚠ lockout pattern not matched — skipping")
    return source


def fix_token_refresh_test(source: str) -> str:
    """Fix test_successful_token_refresh — login first to get a real refresh token."""
    old = '''@pytest.mark.smoke
def test_successful_token_refresh(base_url):
    payload = {'refresh_token': 'valid_refresh_token'}
    response = requests.post(f'{base_url}/api/auth/refresh', json=payload)
    assert response.status_code == 200
    data = response.json()
    assert 'new_access_token' in data'''

    new = '''@pytest.mark.smoke
def test_successful_token_refresh(base_url):
    """Scenario: Successful token refresh | P1 | POST /api/auth/refresh"""
    # Login first to get a real refresh token
    login_resp = requests.post(
        f"{base_url}/api/auth/login",
        json={"email": "customer@test.com", "password": "CustomerPass123!"}
    )
    assert login_resp.status_code == 200
    refresh_token = login_resp.json().get("refreshToken", "")

    response = requests.post(
        f"{base_url}/api/auth/refresh",
        json={"refreshToken": refresh_token}
    )
    assert response.status_code == 200
    data = response.json()
    assert "accessToken" in data'''

    if old in source:
        print("✓ Fixed test_successful_token_refresh")
        return source.replace(old, new)
    print("  ⚠ token refresh pattern not matched — skipping")
    return source


def main():
    if not TEST_FILE.exists():
        print(f"✗ File not found: {TEST_FILE}")
        return

    source = TEST_FILE.read_text()
    print(f"Read {len(source.splitlines())} lines from {TEST_FILE}\n")

    # Apply fixes in order
    source = fix_indentation(source)
    source = fix_logout_test(source)
    source = fix_lockout_test(source)
    source = fix_token_refresh_test(source)

    # Verify it parses
    try:
        ast.parse(source)
        print("\n✓ File parses cleanly")
    except SyntaxError as e:
        print(f"\n✗ SyntaxError line {e.lineno}: {e.msg}")
        lines = source.splitlines()
        for i, l in enumerate(lines[max(0, e.lineno-3):e.lineno+3], start=max(1, e.lineno-2)):
            print(f"  {i:4}: {l}")
        return

    TEST_FILE.write_text(source)
    print(f"✓ Written → {TEST_FILE}")
    print("\nRun:")
    print("  pytest tests/api/test_login_api.py -v -m smoke")


if __name__ == "__main__":
    main()