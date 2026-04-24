"""
TestMart AI-QE Pipeline — Auto-generated pytest suite
Feature  : Login
Run ID   : 20260412_051118
Agent    : ScriptForgeAgent (llama-3.1-8b-instant)
"""
import pytest
import requests
from conftest import LOGIN_ENDPOINT
from conftest import LOGOUT_ENDPOINT

@pytest.mark.smoke
def test_successful_login(base_url, auth_headers, test_users_data):
    # test_users_data provides raw dict access for users
    payload = {'email': test_users_data['superadmin']['email'], 'password': test_users_data['superadmin']['password']}
    response = requests.post(f'{base_url}{LOGIN_ENDPOINT}', headers=auth_headers, json=payload)
    assert response.status_code == 200
    assert 'accessToken' in response.json()

@pytest.mark.smoke
def test_invalid_login_credentials(base_url, test_users_data, auth_headers):
    # test_users_data provides raw dict access for users
    payload = {'email': test_users_data['customer']['email'], 'password': 'InvalidPassword'}
    response = requests.post(f'{base_url}{LOGIN_ENDPOINT}', json=payload, headers=auth_headers)
    assert response.status_code == 401
    assert 'error' in response.json()

@pytest.mark.smoke
def test_successful_token_refresh(base_url, auth_tokens):
    # auth_tokens provides raw dict access for tokens
    payload = {'refreshToken': auth_tokens['refreshToken']}
    response = requests.post(f'{base_url}/api/auth/refresh', json=payload)
    assert response.status_code == 200
    assert 'accessToken' in response.json()