# SKILLS.md — SpecAnalystAgent

Declares what this agent can do, what it cannot do, and its exact I/O contract.

---

## Capabilities
- Parse markdown feature specification files
- Parse OpenAPI 3.x JSON contracts
- Identify feature intent and user flows
- Identify risk areas (security, data integrity, auth, edge cases)
- Map spec requirements to API endpoints
- Flag ambiguous or contradictory requirements
- Recommend scenario count per endpoint based on complexity
- Produce a structured JSON analysis consumed by all downstream agents

## Cannot Do
- Generate Gherkin scenarios (that is GherkinAuthorAgent's job)
- Score or rate test cases
- Write pytest code
- Make assumptions about unstated business rules

## Tools / Libraries Used
- `groq` SDK (llama-3.3-70b-versatile)
- Standard Python `json`, `pathlib`

---

## Input Contract
```json
{
  "feature_name": "string — e.g. login",
  "spec_path":    "string — path to LOGIN_FEATURES.md",
  "openapi_path": "string — path to openapi.json"
}
```

## Output Contract
```json
{
  "feature_name":   "string",
  "feature_intent": "string — one paragraph summary of what this feature does",
  "endpoints": [
    {
      "method":             "GET | POST | PUT | DELETE | PATCH",
      "path":               "string — exact path from openapi.json",
      "summary":            "string — what this endpoint does",
      "recommended_scenarios": "integer 2–8",
      "risk_level":         "LOW | MEDIUM | HIGH | CRITICAL"
    }
  ],
  "risk_areas": [
    {
      "area":        "string — e.g. Token expiry not handled",
      "severity":    "LOW | MEDIUM | HIGH | CRITICAL",
      "spec_source": "string — quote or line reference from spec"
    }
  ],
  "ambiguous_requirements": [
    {
      "description": "string — what is unclear",
      "spec_source": "string — where in the spec"
    }
  ],
  "recommended_total_scenarios": "integer",
  "confidence": "float 0.0–1.0",
  "flagged": ["string — list of concerns if confidence < 0.75"]
}
```

## Memory Written After Each Run
```json
{
  "summary": "string — one line: what was analysed and key findings",
  "feature_name": "string",
  "endpoint_count": "integer",
  "risk_area_count": "integer",
  "ambiguous_count": "integer",
  "confidence": "float"
}
```