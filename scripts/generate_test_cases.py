#!/usr/bin/env python3
"""
generate_tests.py
Professional Gherkin generator using the 2026 Google GenAI SDK.
"""

import argparse
from html import parser
import os
import re
import sys
from pathlib import Path

try:
    from google import genai
except ImportError:
    print("ERROR: google-genai package not installed.")
    print("       Run: pip install google-genai")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------
PROMPT_TEMPLATE = """Act as a Principal SDET. Analyze the feature spec and generate exactly 5 professional-grade Gherkin test cases.

CONSTRAINTS:
1. QUANTITY: Generate ONLY 5 scenarios in total.
2. PRIORITY: Select the 5 most critical flows (e.g., 1 Happy Path, 2 Negative/Validation, 1 Role-based, and 1 Edge Case).
3. STYLE: Use Declarative Gherkin (business behavior, not UI clicks).
4. DRY: Use Background for common setup.
5. OUTPUT: Return ONLY the raw .test_case.md file content. No markdown fences.

--- FEATURE SPEC START ---
{feature_spec}
--- FEATURE SPEC END ---"""

def read_feature_spec(path: str) -> str:
    file = Path(path)
    if not file.exists():
        print(f"ERROR: Input file not found: {path}")
        sys.exit(1)
    return file.read_text(encoding="utf-8")

def generate_feature_file(feature_spec: str, model_id: str) -> str:
    # Use GEMINI_API_KEY as the standard environment variable
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable is not set.")
        sys.exit(1)

    # Initialize client
    client = genai.Client(api_key=api_key)

    print(f"  Calling Gemini API (model: {model_id})...")

    prompt = PROMPT_TEMPLATE.format(feature_spec=feature_spec)
    
    try:
        # Standard call for text generation
        response = client.models.generate_content(
            model=model_id,
            contents=prompt
        )
        
        # Access the text property directly
        if not response.text:
            print("ERROR: API returned an empty response.")
            sys.exit(1)
            
        raw = response.text.strip()

        # Clean up common model behaviors (code fences)
        raw = re.sub(r"\s*```$", "", raw)

        return raw.strip()

    except Exception as e:
        print(f"ERROR during API call: {e}")
        print("Tip: Ensure your API key is valid and you are using a supported model ID.")
        sys.exit(1)

def write_output(content: str, path: str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    print(f"  Written to: {out}")

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Gherkin files using Gemini.")
    parser.add_argument("--input", default="requirements/LOGIN_FEATURES.md", help="Input markdown spec")
    parser.add_argument("--output", default="tests/test_cases/login.test_case.md", help="Output .test_case.md file")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Model ID")
    parser.add_argument("--dry-run", action="store_true", help="Preview prompt without calling API")
    args = parser.parse_args()

    print(f"\n[generate_tests.py]")
    print(f"  Input  : {args.input}")
    print(f"  Output : {args.output}")

    feature_spec = read_feature_spec(args.input)
    
    if args.dry_run:
        print("\n--- DRY RUN: PROMPT PREVIEW ---")
        print(PROMPT_TEMPLATE.format(feature_spec=feature_spec[:200] + "..."))
        return

    gherkin_output = generate_feature_file(feature_spec, model_id=args.model)
    write_output(gherkin_output, args.output)
    print("\nDone. Review the generated .test_case.md file.\n")

if __name__ == "__main__":
    main()