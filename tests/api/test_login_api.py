"""
TestMart AI-QE Pipeline — Auto-generated pytest suite
Feature  : Login
Run ID   : 20260427_152246
Agent    : ScriptForgeAgent (llama-3.1-8b-instant)
"""
from altair.datasets import data
import pytest
import requests

@pytest.mark.smoke
def test_successful_login(base_url, test_users_data):
    user = test_users_data['superadmin']
    response = requests.post(f"{base_url}/api/auth/login", json={"email": user['email'], "password": user['password']})
    assert response.status_code == 200
    data = response.json()
    assert "accessToken" in data
    assert "refreshToken" in data        
    assert "user" in data or "userId" in data  

@pytest.mark.smoke
def test_successful_logout(base_url, auth_headers):
    response = requests.post(f"{base_url}/api/auth/logout", headers=auth_headers)
    assert response.status_code == 200
    assert 'accessToken' not in response.json()

@pytest.mark.smoke
def test_successful_refresh_token(base_url, auth_tokens):
    payload = {'refreshToken': auth_tokens['refreshToken']}
    response = requests.post(f'{base_url}/api/auth/refresh', json=payload)
    assert response.status_code == 200
    assert 'success' in response.json()
    assert 'accessToken' in response.json()
    assert 'refreshToken' in response.json()