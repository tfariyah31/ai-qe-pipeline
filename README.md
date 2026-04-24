# TestMart AI-QE Pipeline

> An end-to-end **AI-Orchestrated Quality Engineering System** — from feature specifications to rated, enriched, and executable pytest scripts. Six purpose-built AI agents with hard rules, skills contracts, cross-run memory, and per-run decision logs replace a linear LLM script pipeline.

---

## What changed

The original pipeline called an LLM at each step. This version **engineers AI agents** — each agent has a defined identity, hard constraints it cannot violate, a capability contract, memory of prior runs, and an audit trail written after every execution.

| Dimension | Original | Engineered agents |
|---|---|---|
| LLM usage | One call per step | One call per scenario (prevents truncation) |
| Rules | Prompt suggestions | `RULES.md` baked into system prompt — violations are caught |
| Capabilities | Implicit | `SKILLS.md` — explicit I/O contract + cannot-do list |
| Memory | None | Cross-run JSON store per agent |
| Audit trail | None | Decision log per agent per run |
| Confidence | None | 0.0–1.0 gate — low confidence escalates to human review |
| Arithmetic | LLM | Weighted formula recalculated in Python after every LLM call |
| Rate limiting | None | Per-scenario TPM delays, 429-aware retry-after handling |

---

## Agent pipeline

```
requirements/LOGIN_FEATURES.md + openapi.json
        │
        ▼
[1] SpecAnalystAgent          
Reads the feature spec and extracts intent, scope, risks before generation starts
        │
        │
        │ login_spec_analysis.json
        ▼
[2] GherkinAuthorAgent    
Writes Gherkin scenarios, constrained by rules 
        │
        │
        │ login.test_case.md + login.manifest.json
        ▼
[3] RatingJudgeAgent    
Autonomously scores scenarios using the weighted formula — human can override
        │
        │
        │ login_ratings.json
        ▼
[4] EnrichmentAgent
Tags, prioritizes, and decides what gets dropped — with reasoning           
        │
        │
        │ login.enriched.md + login.enrichment_summary.json
        ▼
[5] ScriptForgeAgent          
Generates pytest scripts with memory of past patterns
        │
        │
        │ tests/api/test_login_api.py
        ▼
[6] OrchestratorAgent        
 Routes between agents, detects failures, retries or escalates
        │
        │
        │ logs/run_{id}/pipeline_summary.log
        ▼
pytest tests/api/test_login_api.py -v -m smoke
```
---

## The six engineering constructs

Every agent is built with six constructs that make it auditable, bounded, and improvable.

### 1. `RULES.md` — hard constraints
Injected verbatim into the system prompt. Not suggestions — violations are caught. Examples:
- `GherkinAuthorAgent`: never write a scenario for an endpoint not in `openapi.json`
- `RatingJudgeAgent`: every score must include a one-sentence justification citing the scenario text
- `ScriptForgeAgent`: never use undefined constants; always assert status code before body fields

### 2. `SKILLS.md` — capability contract
Declares what the agent can do, cannot do, its exact input/output schema, and what it writes to memory. Downstream agents know exactly what to expect. If the output schema changes, `SKILLS.md` is the source of truth.

### 3. Memory — cross-run learning
Each agent maintains a rolling JSON store (`agent_memory/{agent}_memory.json`, max 50 entries). Examples of what persists:
- `GherkinAuthorAgent`: recurring gaps — endpoints that were in the spec analysis but missing from prior Gherkin outputs. Injected as reminders on the next run.
- `ScriptForgeAgent`: working import blocks, auth header patterns, fixture names that succeeded. Never reinvented from scratch.
- `RatingJudgeAgent`: average score distribution across runs — detects scoring drift and injects a calibration warning if scores shift by more than 0.5.

### 4. Decision log — per-run audit trail
After every run, each agent writes `logs/run_{timestamp}/{agent}_decision.log` containing: inputs received, rules applied, decisions made, confidence score, and what was flagged for human review. Every pipeline run is fully inspectable.

### 5. Confidence gate — autonomous escalation
Every agent outputs a `confidence` float (0.0–1.0). Below the threshold set in `agent_config.yaml`, the agent writes to `human_review/human_review_queue.json` and marks `needs_human_review: true`. The pipeline continues — human review is asynchronous. The orchestrator never pauses; it logs the escalation prominently at the end of the run.

### 6. Formula recalculated in Python
`RatingJudgeAgent` scores 5 dimensions per scenario, but the weighted formula is always recalculated in Python after the LLM responds — never trusted from the LLM output. `EnrichmentAgent` builds the entire enriched Gherkin file in Python by parsing and injecting tags directly — the LLM only writes the rejection summary. `ScriptForgeAgent` verifies import statements and assert counts after generation.

---

## Weighted risk scoring

The same formula as before — now applied autonomously by `RatingJudgeAgent` with one LLM call per scenario (prevents token truncation on large suites).

| Dimension | Weight | What it checks |
|---|---|---|
| Business Impact | 1.5 | Does failure here break the business? |
| Frequency of Use | 1.2 | How often do real users exercise this flow? |
| Failure Probability | 1.3 | How likely is this to break? |
| Dependency Impact | 1.0 | How many features break if this fails? |
| Assertion Specificity | 0.5 | Are Then steps precise enough to verify? |

```
Risk Score = [(Impact×1.5) + (Frequency×1.2) + (Probability×1.3) + (Dependency×1.0) + (Assertion×0.5)] / 5.5
```

### Priority mapping

| Score | Priority | Tag | Suite |
|---|---|---|---|
| 4.5–5.0 | P0 Critical | `@smoke` | smoke |
| 4.0–4.4 | P1 High | `@smoke` | smoke |
| 3.0–3.9 | P2 Medium | `@regression` | regression |
| < 3.0 | Drop | rejected | not generated |

P0 count is capped at 20% of passing scenarios — enforced in Python before the LLM call, not by prompt.

---

## Project structure

```
AI-QE-Pipeline/
│
├── agents/
│   ├── base_agent.py                  # shared base: Groq client, memory, confidence gate, decision log
│   ├── spec_analyst/
│   │   ├── RULES.md                   # hard constraints
│   │   ├── SKILLS.md                  # I/O contract
│   │   └── spec_analyst_agent.py
│   ├── gherkin_author/
│   │   ├── RULES.md
│   │   ├── SKILLS.md
│   │   └── gherkin_author_agent.py
│   ├── rating_judge/
│   │   ├── RULES.md
│   │   ├── SKILLS.md
│   │   └── rating_judge_agent.py
│   ├── enrichment/
│   │   ├── RULES.md
│   │   ├── SKILLS.md
│   │   └── enrichment_agent.py
│   ├── script_forge/
│   │   ├── RULES.md
│   │   ├── SKILLS.md
│   │   └── script_forge_agent.py
│   └── orchestrator/
│       ├── RULES.md
│       ├── SKILLS.md
│       └── orchestrator_agent.py
│
├── agent_config.yaml                  # model, temperature, thresholds per agent
├── agent_memory/                      # cross-run memory per agent (JSON, rolling 50 entries)
├── human_review/
│   ├── human_review_queue.json        # escalated items — SDET reviews after run
│   └── rating_overrides.json         # optional: manual score overrides before next run
│
├── logs/
│   └── run_{timestamp}/
│       ├── spec_analyst_decision.log
│       ├── gherkin_author_decision.log
│       ├── rating_judge_decision.log
│       ├── enrichment_decision.log
│       ├── script_forge_decision.log
│       └── pipeline_summary.log
│
├── requirements/
│   ├── LOGIN_FEATURES.md              # feature spec — pipeline input
│   ├── openapi.json                   # API contract
│   └── login_spec_analysis.json      # SpecAnalystAgent output (committed)
│
├── tests/
│   ├── conftest.py                    # shared fixtures
│   ├── test_cases/
│   │   ├── login.test_case.md         # GherkinAuthorAgent output
│   │   ├── login.manifest.json        # scenario manifest
│   │   ├── login.enriched.md          # EnrichmentAgent output — tagged + prioritised
│   │   ├── login.enrichment_summary.json
│   │   └── login.rejection_summary.md
│   └── api/
│       ├── test_login_api.py          # ScriptForgeAgent output — runnable pytest
│       └── test_login_manifest.json
│
├── ratings/
│   └── login_ratings.json            # RatingJudgeAgent output — all scores + justifications
│
├── .github/workflows/
│   ├── ai_qe_pipeline.yml            # triggers on push to requirements/**_FEATURES.md
│   └── run_tests.yml                 # triggers after pipeline — starts backend, runs pytest
│
└── backend/                          # TestMart Node.js backend (unchanged)
```

---

## Quick start

```bash
# 1. Clone and activate venv
python3 -m venv venv && source venv/bin/activate
pip install groq pyyaml pytest requests pytest-html

# 2. Set your Groq API key (free tier — no credit card required)
export GROQ_API_KEY=your_key_here

# 3. Start the backend (separate terminal)
cd backend && npm install && node server.js

# 4. Seed test users
cd backend && node seedUser.js

# 5. Run the full agent pipeline
python -m agents.orchestrator.orchestrator_agent --feature login

# 6. Run generated tests
pytest tests/api/test_login_api.py -v -m smoke
pytest tests/api/test_login_api.py -v -m regression
```

### Run agents individually (for debugging)

```bash
python -m agents.spec_analyst.spec_analyst_agent
python -m agents.gherkin_author.gherkin_author_agent
python -m agents.rating_judge.rating_judge_agent
python -m agents.enrichment.enrichment_agent
python -m agents.script_forge.script_forge_agent
```

---

## CI — GitHub Actions

| Workflow | Trigger | What it does |
|---|---|---|
| `ai_qe_pipeline.yml` | Push to `requirements/**_FEATURES.md` | Runs all 5 agents via Orchestrator, commits generated tests, uploads logs as artifacts |
| `run_tests.yml` | After pipeline completes OR push to `tests/api/` | Starts MongoDB + Node backend, seeds users, runs `pytest -m smoke` then `pytest -m regression` |

**Required secret:** `GROQ_API_KEY` — add in `Settings → Secrets and variables → Actions`.

### Human review flow

After each pipeline run, check `human_review/human_review_queue.json` for items the agents escalated. To override a RatingJudge score before re-running:

```json
// human_review/rating_overrides.json
[
  {
    "title": "Successful login",
    "scores": {
      "business_impact": 5.0,
      "frequency_of_use": 5.0,
      "failure_probability": 3.0,
      "dependency_impact": 4.0,
      "assertion_specificity": 4.0
    },
    "reason": "SDET override — assertion specificity confirmed high"
  }
]
```

Re-run `RatingJudgeAgent` and it will apply the override, mark `human_override: true` in the ratings JSON, and continue.

---

## LLM model strategy

| Agent | Model | Reason |
|---|---|---|
| SpecAnalystAgent | `llama-3.3-70b-versatile` | Complex spec reasoning |
| GherkinAuthorAgent | `llama-3.3-70b-versatile` | Creative + rule-bound generation |
| RatingJudgeAgent | `llama-3.1-8b-instant` | Structured scoring — formula in Python |
| EnrichmentAgent | `llama-3.1-8b-instant` | Deterministic tagging — Gherkin in Python |
| ScriptForgeAgent | `llama-3.1-8b-instant` | Code gen — repair logic catches errors |
| OrchestratorAgent | `llama-3.1-8b-instant` | Routing only |

All models run on **Groq free tier** (no credit card required). Rate limits: `llama-3.3-70b` = 1,000 req/day, 12,000 TPM. `llama-3.1-8b` = 14,400 req/day, 6,000 TPM. The pipeline adds a 6-second delay between per-scenario LLM calls and a 10-second delay between agents to stay within TPM limits.

Model assignments and all thresholds are configurable in `agent_config.yaml` — no code changes needed.

---

## Backend setup

```
PORT=5001
MONGO_URI=mongodb://localhost:27017/mywebapp
JWT_SECRET=your_secret_key_here
REFRESH_SECRET=your_refresh_secret
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
```

Seed users created by `node seedUser.js`:

| Role | Email | Password |
|---|---|---|
| Super Admin | superadmin@test.com | Str0ng!Pass#2024 |
| Merchant | merchant@test.com | MerchantPass123! |
| Customer | customer@test.com | CustomerPass123! |
| Blocked | blocked@test.com | BlockedPass123! |

---

## Author

**Tasnim Fariyah**

[![GitHub](https://img.shields.io/badge/GitHub-tfariyah31-181717?logo=github)](https://github.com/tfariyah31)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-tasnim--fariyah-0A66C2?logo=linkedin)](https://www.linkedin.com/in/tasnim-fariyah/)
