#!/usr/bin/env python3
"""
generate_tests.py
Reads a feature spec markdown file and uses the Google Gemini API (free tier)
to generate professional Gherkin .feature files.

Usage:
    python generate_tests.py                          # uses defaults
    python generate_tests.py --input docs/AUTH_FEATURES.md --output tests/features/auth.feature
    python generate_tests.py --input docs/CART_FEATURES.md --output tests/features/cart.feature

Setup:
    1. Get a FREE Gemini API key at: https://aistudio.google.com/app/apikey
       (No credit card required)
    2. pip install google-generativeai
    3. export GEMINI_API_KEY=your_key_here
"""

import argparse
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
# Prompt template
# ---------------------------------------------------------------------------
PROMPT_TEMPLATE = """Act as a Principal SDET and BDD Specialist with 15+ years of experience in test automation. Your goal is to analyze the feature specification below and generate professional-grade Gherkin test cases.

CONSTRAINTS & GUIDELINES:
1. Analyze the feature spec and extract all user roles and all user actions.
2. Declarative Style: Write scenarios based on business behavior, not UI implementation.
   Use "When the user authenticates" instead of "When the user types into the username field and clicks login."
3. Scenario Coverage: For every feature, include:
   - Happy Path (Golden path)
   - Negative Scenarios (Error handling/Validation)
   - Role-based authorization
   - API/backend validation where applicable
   - Edge Case (Boundary values, race conditions, or state-specific issues)
4. DRY Principle: Use Background sections for common setup steps across scenarios.
5. Data Driven: Use Scenario Outline with Examples tables where the logic is the same but input data varies.
6. Key flows to test: Authentication (login/logout) and Authorization.
7. Tagging: Categorize scenarios using tags (e.g., @smoke, @regression, @security).
8. Output Format: Return ONLY the raw .feature file content.
   No explanation, no markdown code fences, no preamble. Just the Gherkin.

--- FEATURE SPEC START ---
{feature_spec}
--- FEATURE SPEC END ---"""


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------
def read_feature_spec(path: str) -> str:
    file = Path(path)
    if not file.exists():
        print(f"ERROR: Input file not found: {path}")
        sys.exit(1)
    return file.read_text(encoding="utf-8")


def generate_feature_file(feature_spec: str, model: str = "gemini-1.5-flash") -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable is not set.")
        print("       Get a free key at: https://aistudio.google.com/app/apikey")
        sys.exit(1)

    genai.configure(api_key=api_key)

    print(f"  Calling Gemini API (model: {model})...")

    gemini_model = genai.GenerativeModel(model)
    prompt = PROMPT_TEMPLATE.format(feature_spec=feature_spec)
    response = gemini_model.generate_content(prompt)

    raw = response.text.strip()

    # Strip markdown code fences if the model adds them despite instructions
    raw = re.sub(r"^```(?:gherkin|cucumber)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)

    return raw.strip()


def write_output(content: str, path: str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    print(f"  Written to: {out}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Gherkin .feature files from a markdown feature spec using Gemini (free)."
    )
    parser.add_argument(
        "--input",
        default="docs/AUTH_FEATURES.md",
        help="Path to the feature spec markdown file (default: docs/AUTH_FEATURES.md)",
    )
    parser.add_argument(
        "--output",
        default="tests/features/auth.feature",
        help="Path to write the generated .feature file (default: tests/features/auth.feature)",
    )
    parser.add_argument(
        "--model",
        default="gemini-1.5-flash",
        help="Gemini model to use (default: gemini-1.5-flash — free tier)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the prompt that would be sent without calling the API",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print(f"\n[generate_tests.py]")
    print(f"  Input  : {args.input}")
    print(f"  Output : {args.output}")

    feature_spec = read_feature_spec(args.input)
    print(f"  Spec loaded: {len(feature_spec)} chars")

    if args.dry_run:
        print("\n--- DRY RUN: Prompt that would be sent ---")
        preview = PROMPT_TEMPLATE.format(feature_spec=feature_spec[:400] + "...[truncated]")
        print(preview)
        print("------------------------------------------\n")
        return

    gherkin_output = generate_feature_file(feature_spec, model=args.model)
    write_output(gherkin_output, args.output)
    print(f"  Output size: {len(gherkin_output)} chars")
    print("\nDone. Review the generated .feature file before committing.\n")


if __name__ == "__main__":
    main()