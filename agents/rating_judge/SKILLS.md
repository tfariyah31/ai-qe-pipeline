# SKILLS.md — RatingJudgeAgent

Declares what this agent can do, what it cannot do, and its exact I/O contract.

---

## Capabilities
- Score every Gherkin scenario across 5 weighted dimensions
- Apply the exact weighted risk formula used by the TestMart QE team
- Write one-sentence justifications for every dimension score
- Apply quality gates and assign pass/reject verdicts
- Map passing scenarios to priority tiers (P0/P1/P2)
- Detect vague Then steps (assertion_specificity < 2.0) and flag them
- Check and apply human override scores from rating_overrides.json
- Escalate low-confidence scores to human_review_queue.json
- Write ratings to ratings/login_ratings.json (same format as original pipeline)
- Track score distribution history in memory to detect drift across runs

## Cannot Do
- Generate or modify Gherkin scenarios
- Add tags or priority labels to the enriched file (EnrichmentAgent's job)
- Generate pytest scripts
- Interact with the user during scoring — fully autonomous

## Tools / Libraries Used
- `groq` SDK (llama-3.3-70b-versatile)
- Standard Python `json`, `pathlib`

---

## Weighted Scoring Formula
```
Risk Score = [
  (Business Impact    × 1.5) +
  (Frequency of Use   × 1.2) +
  (Failure Probability× 1.3) +
  (Dependency Impact  × 1.0) +
  (Assertion Specificity× 0.5)
] / 5.5
```

## Dimension Definitions
| Dimension            | Weight | What it checks                                      |
|----------------------|--------|-----------------------------------------------------|
| Business Impact      | 1.5    | Does failure here break the business?               |
| Frequency of Use     | 1.2    | How often do real users exercise this flow?         |
| Failure Probability  | 1.3    | How likely is this to break? (complexity, churn)    |
| Dependency Impact    | 1.0    | How many features break if this fails?              |
| Assertion Specificity| 0.5    | Are Then steps precise enough to actually verify?   |

## Priority Mapping
| Score     | Priority | Tag         |
|-----------|----------|-------------|
| 4.5–5.0   | P0       | @smoke      |
| 4.0–4.4   | P1       | @smoke      |
| 3.0–3.9   | P2       | @regression |
| < 3.0     | reject   | dropped     |

---

## Input Contract
```json
{
  "feature_name":       "string",
  "manifest_path":      "string — path to login.manifest.json",
  "spec_analysis_path": "string — path to login_spec_analysis.json"
}
```

## Output Contract — ratings/{feature}_ratings.json
```json
{
  "feature_name": "string",
  "run_id":       "string",
  "total_scored": "integer",
  "pass_count":   "integer",
  "reject_count": "integer",
  "pass_rate":    "float — percentage",
  "scenarios": [
    {
      "title":          "string",
      "endpoint":       "string",
      "human_override": "boolean",
      "scores": {
        "business_impact":      "float 1.0–5.0",
        "frequency_of_use":     "float 1.0–5.0",
        "failure_probability":  "float 1.0–5.0",
        "dependency_impact":    "float 1.0–5.0",
        "assertion_specificity":"float 1.0–5.0"
      },
      "justifications": {
        "business_impact":      "string — one sentence citing the scenario",
        "frequency_of_use":     "string",
        "failure_probability":  "string",
        "dependency_impact":    "string",
        "assertion_specificity":"string"
      },
      "weighted_score":  "float",
      "verdict":         "pass | reject",
      "priority":        "P0 | P1 | P2 | null",
      "rejection_reason":"string | null"
    }
  ],
  "escalated_for_human_review": ["string — scenario titles"],
  "confidence": "float 0.0–1.0",
  "flagged":    ["string"]
}
```

## Memory Written After Each Run
```json
{
  "summary":          "string — one line summary",
  "feature_name":     "string",
  "pass_rate":        "float",
  "avg_score":        "float",
  "reject_count":     "integer",
  "escalated_count":  "integer",
  "score_distribution": {
    "P0": "integer",
    "P1": "integer",
    "P2": "integer",
    "reject": "integer"
  }
}
```