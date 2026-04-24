# SKILLS.md — ScriptForgeAgent

Declares what this agent can do, what it cannot do, and its exact I/O contract.

---

## Capabilities
- Convert enriched Gherkin scenarios into runnable pytest test functions
- Read openapi.json to extract exact endpoint paths, HTTP methods, and schemas
- Read conftest.py to discover available fixtures — never invent them
- Apply correct pytest markers (@pytest.mark.smoke / @pytest.mark.regression)
- Assert both status codes and response body fields per the Then step
- Load fixture + auth patterns from memory to avoid reinventing per run
- Generate module-level docstrings with feature name, run_id, agent attribution
- Produce a JSON test manifest mapping every function to its scenario + endpoint
- Flag unconvertible scenarios rather than silently skipping them

## Cannot Do
- Modify Gherkin scenarios or ratings
- Run pytest or execute any code
- Access the live backend
- Invent fixture names not present in conftest.py
- Generate UI/Selenium/Playwright tests — API tests only

## Tools / Libraries Used
- `groq` SDK (llama-3.3-70b-versatile — code generation needs full model)
- Standard Python `json`, `pathlib`, `re`

---

## Input Contract
```json
{
  "feature_name":   "string",
  "enriched_path":  "string — path to login.enriched.md",
  "openapi_path":   "string — path to openapi.json",
  "conftest_path":  "string — path to tests/conftest.py"
}
```

## Output Contract — two files produced:

### 1. Pytest script: `tests/api/test_{feature}_api.py`
```python
\"\"\"
TestMart AI-QE Pipeline — Auto-generated pytest suite
Feature  : Login
Run ID   : 20240115_143022
Agent    : ScriptForgeAgent (llama-3.3-70b-versatile)
Source   : tests/test_cases/login.enriched.md
\"\"\"

import pytest
import requests

BASE_URL = "http://localhost:5001"


@pytest.mark.smoke
def test_successful_login_with_valid_credentials(customer_token, base_url):
    \"\"\"Scenario: Successful login with valid credentials | P0 | POST /api/auth/login\"\"\"
    response = requests.post(
        f"{base_url}/api/auth/login",
        json={"email": "customer@test.com", "password": "CustomerPass123!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "accessToken" in data
    assert isinstance(data["accessToken"], str)


@pytest.mark.regression
def test_login_fails_with_incorrect_password(base_url):
    \"\"\"Scenario: Login fails with incorrect password | P2 | POST /api/auth/login\"\"\"
    response = requests.post(
        f"{base_url}/api/auth/login",
        json={"email": "customer@test.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    data = response.json()
    assert "error" in data or "message" in data
```

### 2. Test manifest: `tests/api/test_{feature}_manifest.json`
```json
{
  "feature_name":  "string",
  "run_id":        "string",
  "script_path":   "string",
  "total_tests":   "integer",
  "tests": [
    {
      "function_name":   "string",
      "scenario_title":  "string",
      "marker":          "smoke | regression",
      "priority":        "P0 | P1 | P2",
      "endpoint":        "METHOD /path",
      "fixtures_used":   ["string"],
      "assert_count":    "integer"
    }
  ],
  "unconvertible": [
    {
      "scenario_title": "string",
      "reason":         "string"
    }
  ],
  "confidence": "float 0.0–1.0",
  "flagged":    ["string"]
}
```

## Memory Written After Each Run
```json
{
  "summary":           "string — one line summary",
  "feature_name":      "string",
  "total_tests":       "integer",
  "fixtures_used":     ["string"],
  "working_patterns": {
    "auth_header":     "string — working auth pattern",
    "base_url_fixture":"string — fixture name for base URL",
    "import_block":    "string — standard import block that worked"
  },
  "unconvertible_count": "integer"
}
```