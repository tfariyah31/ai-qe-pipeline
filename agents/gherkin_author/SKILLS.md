# SKILLS.md — GherkinAuthorAgent

Declares what this agent can do, what it cannot do, and its exact I/O contract.

---

## Capabilities
- Read and interpret a spec_analysis.json produced by SpecAnalystAgent
- Write well-formed Gherkin (Given/When/Then) scenarios in BDD style
- Cover happy path, negative, and edge cases per endpoint
- Tag scenarios with @smoke or @regression
- Produce a JSON manifest mapping each scenario to its endpoint + spec source
- Load and apply memory from prior runs to avoid repeating known gaps

## Cannot Do
- Score or rate scenarios (that is RatingJudgeAgent's job)
- Assign P0/P1/P2 priority (that is EnrichmentAgent's job)
- Generate pytest code (that is ScriptForgeAgent's job)
- Invent endpoints not in spec_analysis.json
- Exceed the max_scenarios_per_feature limit without flagging

## Tools / Libraries Used
- `groq` SDK (llama-3.3-70b-versatile)
- Standard Python `json`, `pathlib`, `re`

---

## Input Contract
```json
{
  "feature_name":      "string — e.g. login",
  "spec_analysis_path":"string — path to login_spec_analysis.json",
  "spec_path":         "string — path to LOGIN_FEATURES.md"
}
```

## Output Contract — Two files produced:

### 1. Gherkin markdown: `tests/test_cases/{feature}.test_case.md`
```gherkin
Feature: Login

  @smoke
  Scenario: Successful login with valid credentials
    Given the TestMart API is running on localhost:5001
    When I POST to /api/auth/login with valid email and password
    Then the response status is 200
    And the response body contains a JWT access token

  @regression
  Scenario: Login fails with incorrect password
    Given the TestMart API is running on localhost:5001
    When I POST to /api/auth/login with a valid email and wrong password
    Then the response status is 401
    And the response body contains error "Invalid credentials"
```

### 2. JSON manifest: `tests/test_cases/{feature}.manifest.json`
```json
{
  "feature_name": "string",
  "total_scenarios": "integer",
  "scenarios": [
    {
      "title":       "string — scenario title",
      "tag":         "@smoke | @regression",
      "endpoint":    "METHOD /path",
      "spec_source": "string — requirement this covers",
      "type":        "happy_path | negative | edge_case"
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
  "total_scenarios":   "integer",
  "endpoints_covered": ["string"],
  "recurring_gaps":    ["string — gaps noticed this run"],
  "patterns_that_worked": ["string"]
}
```