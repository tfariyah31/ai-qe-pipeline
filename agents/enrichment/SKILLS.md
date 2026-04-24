# SKILLS.md — EnrichmentAgent

Declares what this agent can do, what it cannot do, and its exact I/O contract.

---

## Capabilities
- Read ratings JSON and map priority tiers to Gherkin scenarios
- Apply @P0/@P1/@P2 tags alongside existing @smoke/@regression tags
- Enforce the P0 cap (max 20% of passing scenarios)
- Demote excess P0s to P1 with logged reasons
- Inject inline comment blocks with risk score + endpoint per scenario
- Drop rejected scenarios and write a rejection_summary.md
- Check memory for tag consistency across prior runs on the same feature
- Produce enrichment_summary.json with full counts and demotion decisions

## Cannot Do
- Re-score or re-evaluate scenario quality (RatingJudgeAgent's job)
- Generate pytest scripts (ScriptForgeAgent's job)
- Add new scenarios or modify Gherkin step text
- Override a reject verdict from RatingJudgeAgent

## Tools / Libraries Used
- `groq` SDK (llama-3.1-8b-instant — lightweight, deterministic tagging)
- Standard Python `json`, `pathlib`, `re`

---

## Input Contract
```json
{
  "feature_name":   "string",
  "ratings_path":   "string — path to login_ratings.json",
  "gherkin_path":   "string — path to login.test_case.md"
}
```

## Output Contract — three files produced:

### 1. Enriched Gherkin: `tests/test_cases/{feature}.enriched.md`
```gherkin
Feature: Login

  @smoke @P0
  Scenario: Successful login with valid credentials
    # Priority: P0 | Risk Score: 4.72 | Endpoint: POST /api/auth/login
    Given the TestMart API is running on localhost:5001
    When I POST to /api/auth/login with valid email and password
    Then the response status is 200
    And the response body contains a JWT access token

  @regression @P2
  Scenario: Login with expired token is rejected
    # Priority: P2 | Risk Score: 3.18 | Endpoint: POST /api/auth/login
    Given a JWT token that has expired
    When I POST to /api/auth/login with the expired token
    Then the response status is 401
```

### 2. Enrichment summary: `tests/test_cases/{feature}.enrichment_summary.json`
```json
{
  "feature_name":    "string",
  "total_passing":   "integer",
  "total_rejected":  "integer",
  "tag_counts": {
    "P0": "integer",
    "P1": "integer",
    "P2": "integer",
    "smoke": "integer",
    "regression": "integer"
  },
  "p0_cap_enforced": "boolean",
  "demotions": [
    {
      "title":  "string — scenario title",
      "from":   "P0",
      "to":     "P1",
      "reason": "string"
    }
  ],
  "confidence": "float 0.0–1.0",
  "flagged":    ["string"]
}
```

### 3. Rejection summary: `tests/test_cases/{feature}.rejection_summary.md`
```markdown
# Rejected Scenarios — login

| Scenario | Score | Reason |
|----------|-------|--------|
| Login with SQL injection payload | 2.14 | Score below 3.0 threshold |
```

## Memory Written After Each Run
```json
{
  "summary":         "string — one line summary",
  "feature_name":    "string",
  "total_passing":   "integer",
  "total_rejected":  "integer",
  "tag_distribution":{ "P0": 0, "P1": 0, "P2": 0 },
  "p0_cap_enforced": "boolean",
  "demotions_count": "integer"
}
```