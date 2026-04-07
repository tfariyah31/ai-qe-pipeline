# TestMart AI-QE Pipeline

> An end-to-end AI-assisted QA workflow demonstrating how to effectively leverage AI-generated test case outputs, from feature specifications to rated, enriched, and executable pytest scripts.

## Workflow Overview
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

## How the Rating works

AI-generated tests are a first draft, not the final output. The rating step enforces quality gates across five API-focused dimensions and aligns with the test plan before any test is allowed to proceed.

### Weighted Risk Scoring
Weighted Average model is used to calculate the final Risk Score. This ensures that business-critical factors have a higher impact on the test priority than technical specificities.

| Dimension | Weight| What it checks |
|---|---|---|
| Business Impact | 1.5 | Does failure here break the business? |
| Frequency of Use | 1.2 | How often do real users exercise this flow? |
| Failure Probability | 1.3 | How likely is this to break? (complex logic, frequent changes) |
| Dependency Impact | 1.0 | How many features break if this fails? |
| Assertion specificity | 0.5 | Are Then steps precise enough to verify? |

```
Risk Score = [ (Impact × 1.5) + (Frequency × 1.2) + (Probability × 1.3) + (Dependency × 1.0) + (Assertion × 0.5) ] / 5.5
```

### Quality Gates & Priority Mapping

Scenarios scoring below threshold or marked `reject` are dropped before enrichment. Remaining tests are tagged based on their weighted score:

| Score | Priority | Tag |
|---|---|---|
| 4.5 – 5.0 | P0 Critical Path | `@smoke` |
| 4.0 – 4.4 | P1 High Risk | `@smoke` |
| 3.0 – 3.9 | P2 Medium Risk | `@regression` |
| < 3.0 | Drop | rejected, not enriched |

All decisions are logged in `ratings/login_ratings.json` and summarised in your terminal after each rating session.

---

## Backend Setup

The TestMart backend must be running on `localhost:5001` before executing any pytest scripts.

### 1. Install dependencies
```bash
cd backend
npm install
```

### 2. Configure environment variables

Create a `.env` file inside the `backend` folder:
```env
PORT=5001
MONGO_URI=mongodb://localhost:27017/mywebapp
JWT_SECRET=your_secret_key_here
REFRESH_SECRET=your_refresh_secret
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
```

> If using MongoDB Atlas, replace `MONGO_URI` with your cloud connection string.

### 3. Start the backend server
```bash
node server.js
```

### 4. Seed test users

In a separate terminal:
```bash
cd backend
node seedUser.js
```

This creates the default test accounts that `conftest.py` uses for authentication fixtures:

| Role | Email | Password |
|---|---|---|
| Super Admin | superadmin@test.com | Str0ng!Pass#2024 |
| Merchant | merchant@test.com | MerchantPass123! |
| Customer | customer@test.com | CustomerPass123! |
| Blocked | blocked@test.com | BlockedPass123! |

> Seed data must be loaded before running any pytest suite — fixtures in `conftest.py` authenticate as these users at session start.

---

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


---

## Author

**Tasnim Fariyah**

[![GitHub](https://img.shields.io/badge/GitHub-tfariyah31-181717?logo=github)](https://github.com/tfariyah31)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-tasnim--fariyah-0A66C2?logo=linkedin)](https://www.linkedin.com/in/tasnim-fariyah/)
