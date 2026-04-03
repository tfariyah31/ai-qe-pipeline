#!/bin/bash

set -e

# --- Configuration & Dynamic Paths ---
# Provide the feature name as the first argument (default: login)
BASE_NAME="${1:-login}"

# Derived Paths
FEATURE_FILE="tests/test_cases/${BASE_NAME}.test_case.md"
ENRICHED_FILE="tests/test_cases/${BASE_NAME}.test_case.enriched.md"
RATINGS_FILE="ratings/${BASE_NAME}_ratings.json"
OUTPUT_FILE="tests/api/test_${BASE_NAME}_api.py"

# Static Config
SPEC_FILE="requirements/openapi.json"
TEMPLATE_FILE="scripts/test_template.py"

echo ""
echo "========================================"
echo "  TestMart AI-QE Pipeline: $BASE_NAME"
echo "========================================"
echo ""

# Step 1 — Rate
echo "STEP 1: Rate generated test cases"
echo "----------------------------------------"
# Assuming rate_tests.py generates the ratings file based on the feature name
python3 scripts/rate_tests.py "$FEATURE_FILE"

# Step 2 — Enrich
echo ""
echo "STEP 2: Enrich with tags + priority"
echo "----------------------------------------"
python3 scripts/enrich_tests.py "$RATINGS_FILE" "$FEATURE_FILE"

# Step 3 — Setup test infra (conftest + pytest.ini)
echo ""
echo "STEP 3: Setup test infrastructure"
echo "----------------------------------------"
python3 scripts/setup_test_infra.py \
  --spec "$SPEC_FILE" \
  --tests-dir tests

# Step 4 — Generate pytest scripts
echo ""
echo "STEP 4: Generate API test scripts"
echo "----------------------------------------"
python3 scripts/generate_api_test_scripts.py \
  --spec "$SPEC_FILE" \
  --feature "$ENRICHED_FILE" \
  --output "$OUTPUT_FILE" \
  --template "$TEMPLATE_FILE" \
  --model gemini-2.5-flash

echo ""
echo "========================================"
echo "  Pipeline complete"
echo "========================================"
echo "  Base Name: $BASE_NAME"
echo "  Rated    : $RATINGS_FILE"
echo "  Enriched : $ENRICHED_FILE"
echo "  Tests    : $OUTPUT_FILE"
echo ""
echo "  Run tests: pytest $OUTPUT_FILE -v"
echo ""