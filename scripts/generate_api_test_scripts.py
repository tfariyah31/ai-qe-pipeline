#!/usr/bin/env python3
import time
import argparse
from email import parser
import json
import os
import re
import sys
from pathlib import Path
from google import genai

def minify_openapi(spec_json):
    """
    Recursively removes metadata from the OpenAPI spec to stay under 
    Free Tier Token-Per-Minute (TPM) limits.
    """
    if isinstance(spec_json, dict):
        # Drop metadata that doesn't impact test generation logic
        keys_to_drop = [
            "description", "example", "summary", "externalDocs", 
            "tags", "info", "servers", "contact", "license"
        ]
        for key in keys_to_drop:
            spec_json.pop(key, None)
        # Recurse through nested objects
        for key in list(spec_json.keys()):
            minify_openapi(spec_json[key])
    elif isinstance(spec_json, list):
        for item in spec_json:
            minify_openapi(item)
    return spec_json

def clean_code(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```[a-zA-Z]*\s*\n?", "", raw)
    raw = re.sub(r"\s*```\s*$", "", raw)
    return raw.strip()

def get_token_key_from_spec(spec_text: str) -> str:
    """Parses the OpenAPI spec to find the dynamic key name for the access token."""
    try:
        spec = json.loads(spec_text)
        # Target the login success response properties
        properties = spec['paths']['/api/auth/login']['post']['responses']['200']['content']['application/json']['schema']['properties']
        
        # Priority logic: find a key with 'token' but not 'refresh'
        for key in properties.keys():
            if "token" in key.lower() and "refresh" not in key.lower():
                return key
        return "accessToken" # Default fallback
    except Exception:
        return "accessToken"

def call_gemini(prompt: str, model_id: str) -> str:
    """Calls Gemini API with exponential backoff for 429 errors."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable not set.")
        sys.exit(1)
    
    client = genai.Client(api_key=api_key)
    
    for attempt in range(3):
        try:
            response = client.models.generate_content(model=model_id, contents=prompt)
            return clean_code(response.text)
        except Exception as e:
            if "429" in str(e):
                # Free tier rate limits are strict; wait significantly
                wait_time = 50 + (attempt * 20) 
                print(f"  ⚠️ Rate limit (429) hit. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"ERROR calling Gemini: {e}")
                sys.exit(1)
    
    print("ERROR: Exceeded retry attempts for Gemini API.")
    sys.exit(1)

# Prompt updated to include the dynamically discovered token key
API_TEST_PROMPT = """Act as an expert SDET. I will provide a Gherkin feature file. Scan the features and generate exactly 1 pytest function, but ONLY for a scenario tagged with @smoke. If multiple @smoke scenarios exist, pick the one with the highest priority. If no @smoke tags are found, do not generate any code.

DATA CONTRACT RULES (CRITICAL):
1. Use the key '{token_key}' for all access token extractions as defined in the OpenAPI spec.
2. Use 'refreshToken' for refresh token extractions.
3. Your app returns a response matching this structure: {{"success": true, "{token_key}": "...", "user": {{...}}}}

TEMPLATE TO FOLLOW:
{template}

OPENAPI SPEC:
{openapi_spec}

GHERKIN FEATURE SCENARIOS:
{feature_content}

RULES:
- Use fixtures from conftest.py (auth_headers, merchant_headers, customer_headers).
- Do NOT re-define fixtures or constants found in the template.
- Assert status codes and validate the response body against the OpenAPI schema.
- Output ONLY raw Python code."""

def main():
    parser = argparse.ArgumentParser(description="Generate API tests using Gemini.")
    parser.add_argument("--spec", default="docs/openapi.json")
    parser.add_argument("--feature", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--template", default="scripts/test_template.py")
    parser.add_argument("--model", default="gemini-2.5-flash")
    args = parser.parse_args()

    
# 1. Load Feature and Template
    feature_text = Path(args.feature).read_text()
    template_text = Path(args.template).read_text()

    # 2. Load and Minify OpenAPI Spec
    try:
        with open(args.spec, 'r') as f:
            raw_spec = json.load(f)
    except Exception as e:
        print(f"ERROR: Could not read OpenAPI spec at {args.spec}: {e}")
        sys.exit(1)

    minified_spec_dict = minify_openapi(raw_spec)
    
    # 3. Dynamic Key Discovery
    dynamic_token_key = get_token_key_from_spec(minified_spec_dict)

    # 4. Prompt Generation
    spec_text = json.dumps(minified_spec_dict, indent=None) # Compact JSON string
    prompt = API_TEST_PROMPT.format(
        token_key=dynamic_token_key,
        template=template_text,
        openapi_spec=spec_text,
        feature_content=feature_text
    )

    # 5. Call API
    print(f"  [SDET Agent] Generating tests for {args.feature}...")
    code = call_gemini(prompt, args.model)
    
    # 6. Save Output
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(code)
    print(f"  [SDET Agent] Success! Saved to: {args.output}")

if __name__ == "__main__":
    main()