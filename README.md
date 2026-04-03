# TestMart AI-QE Pipeline

> An end-to-end AI-assisted QA workflow demonstrating how to effectively leverage AI-generated test outputs—from feature specifications to rated, enriched, and executable pytest scripts.

## Pipeline Overview
```
requirements/LOGIN_FEATURES.md
        │
        ▼
[1] generate_test_cases.py        ← Gemini 2.5 Flash generates Gherkin/Local LLM
        │
        ▼
tests/test_cases/login.test_case.md
        │
        ▼
[2] rate_tests.py                 ← Tester scores quality across 5 dimensions
        │
        ▼
ratings/login_ratings.json
        │
        ▼
[3] enrich_tests.py               ← tags (@smoke/@regression) + priority (P0/P1/P2)
        │
        ▼
tests/test_cases/login.enriched.md
        │
        ▼
[4] setup_test_infra.py           ← generates conftest.py + pytest.ini
        │
        ▼
[5] generate_api_test_scripts.py  ← Gemini generates pytest from enriched md + openapi.json
        │
        ▼
tests/api/test_login_api.py       ← runnable pytest suite
```

## Why the Rating Step Exists

AI-generated tests are a first draft, not the final output. The rating step enforces quality gates across five API-focused dimensions and aligns with the test plan before any test is allowed to proceed.

Weighted Risk Scoring
Weighted Average model is used to calculate the final Risk Score. This ensures that business-critical factors have a higher impact on the test priority than technical specificities.

| Dimension | Weight| What it checks |
|---|---|---|
| Business Impact | 1.5 | Does failure here break the business? |
| Frequency of Use | 1.2 | How often do real users exercise this flow? |
| Failure Probability | 1.3 | How likely is this to break? (complex logic, frequent changes) |
| Dependency Impact | 1.0 | How many features break if this fails? |
| Assertion specificity | 0.5 | Are Then steps precise enough to verify? |

Risk Score = [ (Impact × 1.5) + (Frequency × 1.2) + (Probability × 1.3) + (Dependency × 1.0) + (Assertion × 0.5) ] / 5.5

Quality Gates & Priority Mapping

Scenarios scoring below a threshold or marked reject are dropped before enrichment. The remaining tests are tagged based on their weighted score:

P0 (4.5 - 5.0): Critical Path. Automatically tagged @smoke.

P1 (4.0 - 4.4): High Risk. Included in @smoke pipeline.

P2 (3.0 - 3.9): Medium Risk. Tagged @regression (if approved).

Drop (< 3.0): Low risk or redundant.

All decisions are logged in ratings/login_ratings.json and summarized in your terminal after each rating session.

## Quick Start
```bash
# 1. Clone and activate venv
python3 -m venv venv && source venv/bin/activate
pip install pytest requests google-genai

# 2. Set your Gemini API key
export GEMINI_API_KEY=your_key_here

# 3. Run the full pipeline
./scripts/run_pipeline.sh {feature_name}

# 4. Run generated tests (backend must be running on localhost:5001)
pytest tests/api/test_login_api.py -v
```

## Project Structure
```
AI-QE-Pipeline/
├── requirements/
│   └── LOGIN_FEATURES.md          # feature spec — pipeline input
│   └── openapi.json               # API contract
│   
├── tests/
│   ├── conftest.py                # shared fixtures (auto-generated)
│   ├── test_cases/
│   │   ├── login.test_case.md     # AI first draft
│   │   ├── login.enriched.md      # rated + tagged + prioritised
│   └── api/
│       └── test_login_api.py      # final runnable pytest
├── ratings/
│   └── login_ratings.json         # quality scores provided by a Tester
└── scripts/
    ├── generate_test_cases.py     # step 1 — Gemini Gherkin generation
    ├── rate_tests.py              # step 2 — interactive SDET rating
    ├── enrich_tests.py            # step 3 — tag + prioritise
    ├── setup_test_infra.py        # step 4 — conftest + pytest.ini
    ├── generate_api_test_scripts.py # step 5 — Gemini pytest generation
    └── run_pipeline.sh            # runs steps 2–5 locally
```

## CI — GitHub Actions

| Workflow | Trigger | What it does |
|---|---|---|
| `generate_testcases.yml` | Push to `requirements/**_FEATURES.md` | Runs Gemini generation (step 1) |

> Steps 2–3 (rating + enrichment) are intentionally local — they require
> a Tester's judgment.