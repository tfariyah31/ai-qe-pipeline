# AI-QE Pipeline

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)![Groq](https://img.shields.io/badge/Groq-LLaMA_3-F55036?style=flat)![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=flat&logo=streamlit&logoColor=white)![CI](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?style=flat&logo=githubactions&logoColor=white)

> **An end-to-end AI-orchestrated quality engineering system** — from a feature spec to rated, enriched, and executable pytest scripts. Six purpose-built AI agents with hard rules, capability contracts, cross-run memory, confidence gates, and a live Streamlit dashboard replace a linear LLM script pipeline.

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

## Architecture

```
Feature Spec + OpenAPI Contract
          │
          ▼
┌─────────────────────┐
│  SpecAnalystAgent   │  Extracts intent, scope & risks before generation
│  llama-3.3-70b      │
└──────────┬──────────┘
           │ login_spec_analysis.json
           ▼
┌─────────────────────┐
│ GherkinAuthorAgent  │  Writes Gherkin scenarios — constrained by RULES.md
│  llama-3.3-70b      │
└──────────┬──────────┘
           │ login.test_case.md + login.manifest.json
           ▼
┌─────────────────────┐
│  RatingJudgeAgent   │  Scores 5 risk dimensions — formula recalculated in Python
│  llama-3.1-8b       │
└──────────┬──────────┘
           │ login_ratings.json
           ▼
┌─────────────────────┐
│  EnrichmentAgent    │  Tags @smoke/@regression, drops low-risk, reasons in writing
│  llama-3.1-8b       │
└──────────┬──────────┘
           │ login.enriched.md
           ▼
┌─────────────────────┐
│  ScriptForgeAgent   │  Generates executable pytest — verifies imports + assert count
│  llama-3.1-8b       │
└──────────┬──────────┘
           │ tests/api/test_login_api.py
           ▼
┌─────────────────────┐
│ OrchestratorAgent   │  Routes between agents, retries on failure, escalates
│  llama-3.1-8b       │
└──────────┬──────────┘
           │ logs/run_{id}/pipeline_summary.log
           ▼
  pytest tests/api/test_login_api.py -v -m smoke
```

---

## Six Engineering Constructs

Every agent is built with six constructs that make it auditable, bounded, and improvable — not just prompted.

### 1. `RULES.md` — Hard Constraints
Injected verbatim into the system prompt. Not suggestions — violations are caught at runtime.
- `GherkinAuthorAgent`: never write a scenario for an endpoint not in `openapi.json`
- `RatingJudgeAgent`: every score must include a one-sentence justification citing the scenario text
- `ScriptForgeAgent`: never use undefined constants; always assert status code before body fields

### 2. `SKILLS.md` — Capability Contract
Declares exactly what the agent can do, cannot do, its input/output schema, and what it writes to memory. Downstream agents know exactly what to expect — if the output schema changes, `SKILLS.md` is the source of truth.

### 3. Cross-Run Memory
Each agent maintains a rolling JSON store (`agent_memory/{agent}_memory.json`, max 50 entries).
- `GherkinAuthorAgent` tracks recurring gaps — endpoints in the spec but missing from prior outputs. Injected as reminders on the next run.
- `ScriptForgeAgent` remembers working import blocks, auth header patterns, and fixture names that succeeded. Never reinvented from scratch.
- `RatingJudgeAgent` detects scoring drift — if average scores shift by more than 0.5 across runs, a calibration warning is injected.

### 4. Decision Log — Per-Run Audit Trail
After every run each agent writes `logs/run_{timestamp}/{agent}_decision.log` containing: inputs received, rules applied, decisions made, confidence score, and what was flagged for human review. Every pipeline run is fully inspectable.

### 5. Confidence Gate — Autonomous Escalation
Every agent outputs a `confidence` float (0.0–1.0). Below the threshold set in `agent_config.yaml`, the agent writes to `human_review/human_review_queue.json` and marks `needs_human_review: true`. The pipeline continues — human review is asynchronous. The orchestrator never pauses; it logs the escalation prominently.

### 6. Python-Verified Arithmetic
`RatingJudgeAgent` scores 5 dimensions per scenario, but the weighted formula is **always recalculated in Python** after the LLM responds — never trusted from the LLM output. `EnrichmentAgent` builds the enriched Gherkin in Python by parsing and injecting tags directly. `ScriptForgeAgent` verifies import statements and assert counts after generation.

---

## Weighted Risk Scoring

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

| Score | Priority | Tag | Suite |
|---|---|---|---|
| 4.5–5.0 | P0 Critical | `@smoke` | smoke |
| 4.0–4.4 | P1 High | `@smoke` | smoke |
| 3.0–3.9 | P2 Medium | `@regression` | regression |
| < 3.0 | Dropped | rejected | not generated |

P0 count is capped at 20% of passing scenarios — enforced in Python before the LLM call.

---

## Live Dashboard

A Streamlit dashboard provides a real-time view of the pipeline as it runs.

**Features:**
- 6 agent cards update live — `Waiting → Running → Complete / Escalated`
- Confidence score and duration shown per agent
- Live log stream as each agent writes its decision log
- Human review queue viewer with inline score override form
- Results tabs after completion: Gherkin viewer, pytest viewer, risk score bar chart
- Stop pipeline button — terminates subprocess cleanly

> 📸 *Screenshots coming soon*

---

## CI — GitHub Actions

| Workflow | Trigger | What it does |
|---|---|---|
| `ai_qe_pipeline.yml` | Push to `requirements/**_FEATURES.md` | Runs all 5 agents via Orchestrator, commits generated tests, uploads logs as artifacts |
| `run_tests.yml` | After pipeline completes OR push to `tests/api/` | Starts MongoDB + Node backend, seeds users, runs `pytest -m smoke` then `pytest -m regression` |

**Required secret:** `GROQ_API_KEY` — add in `Settings → Secrets and variables → Actions`.

---

## Project Structure

```
AI-QE-Pipeline/
│
├── agents/
│   ├── base_agent.py                  # Shared base: Groq client, memory, confidence gate, decision log
│   ├── spec_analyst/
│   │   ├── RULES.md                   # Hard constraints
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
├── streamlit_app/                     # Live dashboard
│   ├── app.py
│   ├── pipeline_runner.py
│   └── components/
│       ├── sidebar.py
│       ├── agent_status.py
│       ├── log_viewer.py
│       ├── review_queue.py
│       └── results_tabs.py
│
├── agent_config.yaml                  # Model, temperature, thresholds per agent
├── agent_memory/                      # Cross-run memory per agent (JSON, rolling 50 entries)
├── human_review/
│   ├── human_review_queue.json        # Escalated items — SDET reviews after run
│   └── rating_overrides.json         # Manual score overrides before next run
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
│   ├── LOGIN_FEATURES.md              # Feature spec — pipeline input
│   ├── openapi.json                   # API contract
│   └── login_spec_analysis.json      # SpecAnalystAgent output
│
├── tests/
│   ├── conftest.py
│   ├── test_cases/
│   │   ├── login.test_case.md
│   │   ├── login.manifest.json
│   │   ├── login.enriched.md
│   │   ├── login.enrichment_summary.json
│   │   └── login.rejection_summary.md
│   └── api/
│       └── test_login_api.py
│
├── ratings/
│   └── login_ratings.json
│
├── .github/workflows/
│   ├── ai_qe_pipeline.yml
│   └── run_tests.yml
│
└── backend/                           # TestMart Node.js backend
```

---

## Quick Start

```bash
# 1. Clone and activate venv
git clone https://github.com/tfariyah31/ai-qe-pipeline.git
cd ai-qe-pipeline
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

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

### Run the Live Dashboard

```bash
python -m streamlit run streamlit_app/app.py
```

### Run Agents Individually

```bash
python -m agents.spec_analyst.spec_analyst_agent
python -m agents.gherkin_author.gherkin_author_agent
python -m agents.rating_judge.rating_judge_agent
python -m agents.enrichment.enrichment_agent
python -m agents.script_forge.script_forge_agent
```

---

## Human Review Flow

After each pipeline run, check `human_review/human_review_queue.json` for items agents escalated. To override a score before re-running:

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

## Backend Setup

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

**Tasnim Fariyah** — 14 years in QA engineering, now building AI-powered quality systems.

[![GitHub](https://img.shields.io/badge/GitHub-tfariyah31-181717?logo=github)](https://github.com/tfariyah31)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-tasnim--fariyah-0A66C2?logo=linkedin)](https://www.linkedin.com/in/tasnim-fariyah/)