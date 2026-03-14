#!/usr/bin/env python3
"""
generate_api_tests.py
Reads docs/openapi.json and an optional .feature file, then uses the
Google Gemini API (free tier) to generate pytest API test scripts.

Usage:
    python scripts/generate_api_tests.py                        # uses defaults
    python scripts/generate_api_tests.py --spec docs/openapi.json
    python scripts/generate_api_tests.py --spec docs/openapi.json \
        --feature tests/features/auth.feature \
        --output tests/api/test_auth.py

Setup:
    1. Get a FREE Gemini API key at: https://aistudio.google.com/app/apikey
    2. pip install google-generativeai
    3. export GEMINI_API_KEY=your_key_here

Project structure after running:
    TestMart/
    ├── docs/
    │   └── openapi.json               <- input: your Swagger export
    ├── tests/
    │   ├── features/
    │   │   └── auth.feature           <- optional input: guides scenario coverage
    │   ├── api/
    │   │   ├── conftest.py            <- generated: shared fixtures (base_url, headers)
    │   │   └── test_auth.py           <- generated: pytest API test script
    │   └── ...
    └── scripts/
        └── generate_api_tests.py      <- this file
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    import google.generativeai as genai
except ImportError:
    print("ERROR: google-generativeai package not installed.")
    print("       Run: pip install google-generativeai")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

CONFTEST_PROMPT = """You are a senior SDET. Generate a pytest conftest.py file for API testing.

Requirements:
- A `base_url` fixture returning "http://localhost:5000"
- A `headers` fixture with Content-Type: application/json
- An `auth_headers` fixture that calls POST /api/auth/login with admin credentials
  and returns Authorization: Bearer <token> headers
- A `test_user` fixture with seeded test credentials for each role:
  super_admin, merchant, customer
- Use pytest fixtures with appropriate scope (session or function)
- Include a requests.Session fixture for connection reuse
- Add a health-check fixture that skips all tests if the server is not running

Output ONLY raw Python code. No markdown fences, no explanation."""


API_TEST_PROMPT = """You are a senior SDET with 15+ years experience writing pytest API test suites.

Generate a complete, automation-ready pytest test script based on:
1. The OpenAPI spec below (defines endpoints, request/response shapes)
2. The Gherkin feature file below (defines scenario coverage required)

REQUIREMENTS:
- Use the `requests` library — no httpx or other clients
- Use fixtures from conftest.py: base_url, headers, auth_headers, test_user
- Structure: one test class per endpoint group (e.g. TestAuthLogin, TestAuthLogout)
- Coverage for every endpoint in the spec:
    * Happy path with valid data
    * Negative: invalid credentials / bad input
    * Auth: missing token, expired token, wrong role
    * Edge cases: empty fields, SQL injection strings, very long inputs
- Use parametrize for data-driven scenarios matching Scenario Outlines in the feature file
- Add clear docstrings describing what each test validates
- Assert both status codes AND response body fields
- Tag tests with pytest markers: @pytest.mark.smoke, @pytest.mark.regression, @pytest.mark.security
- Include a module-level docstring explaining what this test file covers

Output ONLY raw Python code. No markdown fences, no explanation.

--- OPENAPI SPEC ---
{openapi_spec}

--- GHERKIN FEATURE FILE ---
{feature_content}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_json(path: str) -> dict:
    file = Path(path)
    if not file.exists():
        print(f"ERROR: File not found: {path}")
        sys.exit(1)
    with file.open(encoding="utf-8") as f:
        return json.load(f)


def read_text(path: str) -> str:
    file = Path(path)
    if not file.exists():
        print(f"WARNING: Optional file not found: {path} — skipping")
        return "(No feature file provided — generate full coverage from the OpenAPI spec alone)"
    return file.read_text(encoding="utf-8")


def clean_code(raw: str) -> str:
    """Strip markdown fences if the model adds them despite instructions."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:python)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def write_output(content: str, path: str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    print(f"  Written: {out}")


def call_gemini(prompt: str, model_name: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable is not set.")
        print("       Get a free key at: https://aistudio.google.com/app/apikey")
        sys.exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)
    return clean_code(response.text)


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

def generate_conftest(output_dir: str, model: str) -> None:
    print("\n  Generating conftest.py...")
    code = call_gemini(CONFTEST_PROMPT, model)
    write_output(code, os.path.join(output_dir, "conftest.py"))


def generate_api_tests(
    openapi_spec: dict,
    feature_content: str,
    output_path: str,
    model: str,
) -> None:
    print("\n  Generating pytest API test script...")

    # Pass a compact JSON string to keep token count down
    spec_str = json.dumps(openapi_spec, indent=2)

    prompt = API_TEST_PROMPT.format(
        openapi_spec=spec_str,
        feature_content=feature_content,
    )

    code = call_gemini(prompt, model)
    write_output(code, output_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate pytest API tests from OpenAPI spec using Gemini (free)."
    )
    parser.add_argument(
        "--spec",
        default="docs/openapi.json",
        help="Path to OpenAPI JSON file (default: docs/openapi.json)",
    )
    parser.add_argument(
        "--feature",
        default="tests/features/auth.feature",
        help="Path to Gherkin .feature file for scenario guidance (optional)",
    )
    parser.add_argument(
        "--output",
        default="tests/api/test_auth.py",
        help="Path to write the generated pytest file (default: tests/api/test_auth.py)",
    )
    parser.add_argument(
        "--skip-conftest",
        action="store_true",
        help="Skip generating conftest.py (use if you already have one)",
    )
    parser.add_argument(
        "--model",
        default="gemini-1.5-flash",
        help="Gemini model to use (default: gemini-1.5-flash — free tier)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without calling the API",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print("\n[generate_api_tests.py]")
    print(f"  Spec    : {args.spec}")
    print(f"  Feature : {args.feature}")
    print(f"  Output  : {args.output}")
    print(f"  Model   : {args.model}")

    openapi_spec = read_json(args.spec)
    feature_content = read_text(args.feature)

    if args.dry_run:
        print("\n--- DRY RUN ---")
        print(f"  OpenAPI spec loaded: {len(json.dumps(openapi_spec))} chars")
        print(f"  Feature file loaded: {len(feature_content)} chars")
        print("  Would generate:")
        if not args.skip_conftest:
            output_dir = str(Path(args.output).parent)
            print(f"    {output_dir}/conftest.py")
        print(f"    {args.output}")
        print("---------------\n")
        return

    # Generate conftest.py once per output directory
    if not args.skip_conftest:
        output_dir = str(Path(args.output).parent)
        conftest_path = os.path.join(output_dir, "conftest.py")
        if Path(conftest_path).exists():
            print(f"\n  conftest.py already exists — skipping (use --skip-conftest to suppress this message)")
        else:
            generate_conftest(output_dir, args.model)

    # Generate the test script
    generate_api_tests(
        openapi_spec=openapi_spec,
        feature_content=feature_content,
        output_path=args.output,
        model=args.model,
    )

    print("\nDone.")
    print("Next steps:")
    print("  1. pip install pytest requests")
    print("  2. Start your backend: node backend/server.js")
    print(f"  3. Run tests: pytest {args.output} -v")
    print()


if __name__ == "__main__":
    main()