# SKILLS.md — OrchestratorAgent

Declares what this agent can do, what it cannot do, and its exact I/O contract.

---

## Capabilities
- Run all 5 pipeline agents in strict sequence
- Pass each agent's output as the next agent's input automatically
- Read confidence scores and apply gate logic per agent_config.yaml
- Retry failed agents up to max_retries with exponential backoff
- Halt the pipeline cleanly on unrecoverable failure
- Write a structured pipeline_summary.log after every run
- Print a human-readable terminal summary at completion
- Report escalated human review items prominently at end of run

## Cannot Do
- Run agents in parallel
- Skip agents or reorder the sequence
- Generate test content itself
- Modify agent outputs between steps

## Tools / Libraries Used
- `groq` SDK (llama-3.1-8b-instant — routing only, minimal tokens)
- Standard Python `json`, `pathlib`, `time`, `sys`
- All 5 agent classes

---

## Input Contract (CLI)
```bash
python -m agents.orchestrator.orchestrator_agent --feature login
# Optional flags:
#   --spec      path/to/FEATURES.md      (default: requirements/{feature}_FEATURES.md)
#   --openapi   path/to/openapi.json     (default: requirements/openapi.json)
#   --conftest  path/to/conftest.py      (default: tests/conftest.py)
```

## Pipeline Data Flow
```
agent_config.yaml
       │
       ▼
[1] SpecAnalystAgent
       │ requirements/{feature}_spec_analysis.json
       ▼
[2] GherkinAuthorAgent
       │ tests/test_cases/{feature}.test_case.md
       │ tests/test_cases/{feature}.manifest.json
       ▼
[3] RatingJudgeAgent
       │ ratings/{feature}_ratings.json
       ▼
[4] EnrichmentAgent
       │ tests/test_cases/{feature}.enriched.md
       │ tests/test_cases/{feature}.enrichment_summary.json
       │ tests/test_cases/{feature}.rejection_summary.md
       ▼
[5] ScriptForgeAgent
       │ tests/api/test_{feature}_api.py
       │ tests/api/test_{feature}_manifest.json
       ▼
logs/run_{id}/pipeline_summary.log
human_review/human_review_queue.json  (if escalations exist)
```

## Pipeline Summary Log Schema
```json
{
  "run_id":       "string",
  "feature_name": "string",
  "started_at":   "ISO timestamp",
  "ended_at":     "ISO timestamp",
  "duration_sec": "float",
  "final_status": "SUCCESS | PARTIAL | FAILED",
  "agents": [
    {
      "name":               "string",
      "status":             "completed | failed | skipped",
      "confidence":         "float",
      "needs_human_review": "boolean",
      "flagged":            ["string"],
      "duration_sec":       "float",
      "output_files":       ["string"]
    }
  ],
  "human_review_items": "integer",
  "human_review_path":  "string",
  "errors":             ["string"]
}
```