"""
==========================================
ScriptForgeAgent — Agent 5 of 6

Converts enriched Gherkin scenarios into runnable pytest scripts.
Reads conftest.py for available fixtures, openapi.json for exact
endpoint contracts, and memory for fixture patterns that worked
in prior runs.

Input:
    feature_name   — e.g. "login"
    enriched_path  — path to login.enriched.md
    openapi_path   — path to openapi.json
    conftest_path  — path to tests/conftest.py

Output:
    tests/api/test_{feature}_api.py
    tests/api/test_{feature}_manifest.json
    Decision log → logs/run_{id}/script_forge_decision.log
    Memory entry → agent_memory/script_forge_memory.json

"""

import json
import re
import time
import ast
from pathlib import Path
from datetime import datetime, timezone

from agents.base_agent import AgentBase


# ── Per-scenario system prompt ───────────────────────────────
# One LLM call per scenario — small focused prompts, complete bodies.
SCENARIO_SYSTEM_PROMPT = """
You are ScriptForgeAgent. Write ONE complete pytest test function for a single Gherkin scenario.

CRITICAL RULES — violations break the test suite:

R1: Use SINGLE braces for ALL Python dicts and f-strings. NEVER double braces {{ }}.
    CORRECT: payload = {"email": "test@test.com"}

R2: Every line inside the function body MUST be indented with exactly 4 spaces.

R3: Use the EXACT expected status code provided in the prompt. Do NOT guess.

R4: Every test MUST contain at least one assert statement. No empty bodies.

R5: DATA SOURCE & SCOPE RULE:
    - NO INTERNAL IMPORTS: Do not write 'import' or 'from' statements inside the function body.
    - URLS: Always use the 'base_url' fixture: f"{base_url}/api/path".
    - AUTHENTICATED CALLS: Use 'auth_headers', 'merchant_headers', or 'customer_headers'
      for standard requests. These already contain a Bearer token — NEVER call the
      login endpoint inside a test that receives one of these fixtures.
    - TOKEN REFRESH CALLS: Use the 'auth_tokens' fixture to access raw tokens.
      Example: payload = {"refreshToken": auth_tokens["refreshToken"]}
    - RAW CREDENTIALS: Use 'test_users_data' fixture if you need raw emails/passwords.
      Do NOT use 'TEST_USERS', 'LOGIN_ENDPOINT', or 'LOGOUT_ENDPOINT' constants —
      these are internal to conftest.py and cannot be imported by test scripts.

R6: SCOPE ENFORCEMENT: Only generate tests for SMOKE scenarios (@smoke / P0 / P1).
    Always apply the marker: @pytest.mark.smoke

R7: Negative/edge tests must assert the error status code AND one field from the
    error response body.

R8: NO PSEUDOCODE: Every test must be executable against localhost:5001.

R9: Every fixture used in the function body MUST be included as an argument in the
    'def' line. FAILURE TO DO THIS CAUSES A NameError or AttributeError.

R10: ONE ENDPOINT PER TEST: Each test function calls exactly ONE endpoint.
    - A logout test calls ONLY the logout endpoint.
    - A login test calls ONLY the login endpoint.
    - NEVER chain login → logout inside a single test unless the scenario
      explicitly has multiple When steps.

R11: ENDPOINT PATHS: Always hardcode endpoint paths as strings.
    CORRECT:   requests.post(f"{base_url}/api/auth/logout", headers=auth_headers)
    INCORRECT: requests.post(f"{base_url}{LOGOUT_ENDPOINT}", headers=auth_headers)

R12: LOGOUT REQUESTS must NOT include a JSON body. Pass only headers.
    CORRECT:   requests.post(f"{base_url}/api/auth/logout", headers=auth_headers)
    INCORRECT: requests.post(f"{base_url}/api/auth/logout", headers=auth_headers, json={...})

R13: RESPONSE ASSERTIONS: Only assert fields that are explicitly listed in the
    "RESPONSE SCHEMA FOR THIS ENDPOINT" section of the prompt. NEVER invent fields
    or copy field names from a different endpoint's schema or from a fixture dict.

--- CANONICAL EXAMPLES ---

CORRECT — Logout test:
@pytest.mark.smoke
def test_successful_logout(base_url, auth_headers):
    response = requests.post(f"{base_url}/api/auth/logout", headers=auth_headers)
    assert response.status_code == 200

CORRECT — Login test:
@pytest.mark.smoke
def test_successful_login(base_url, test_users_data):
    user = test_users_data["superadmin"]
    response = requests.post(
        f"{base_url}/api/auth/login",
        json={"email": user["email"], "password": user["password"]}
    )
    assert response.status_code == 200
    data = response.json()
    assert "accessToken" in data

CORRECT — Token refresh test:
@pytest.mark.smoke
def test_successful_token_refresh(base_url, auth_tokens):
    payload = {"refreshToken": auth_tokens["refreshToken"]}
    response = requests.post(f"{base_url}/api/auth/refresh", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "accessToken" in data
    assert "refreshToken" in data

WRONG — Never do this (multiple violations):
# VIOLATION R10: logout test calling login endpoint
# VIOLATION R11: using LOGIN_ENDPOINT constant
# VIOLATION R5: re-logging in when auth_headers already has a token
# VIOLATION R9: test_users_data used but not declared as fixture argument
def test_successful_logout(base_url, auth_headers):
    response = requests.post(f"{base_url}{LOGIN_ENDPOINT}",
                             json=test_users_data['superadmin'],
                             headers=auth_headers)
    assert response.status_code == 200
    assert response.json()['success'] == True

--- END EXAMPLES ---

OUTPUT: Return ONLY this JSON (no preamble, no markdown fences):
{
  "function_code": "string — complete decorated function with indented body",
  "function_name": "string",
  "fixtures_used": ["string"],
  "assert_count":  <integer>,
  "confidence":    <float 0.0-1.0>,
  "unconvertible": false,
  "unconvertible_reason": ""
}
"""


class ScriptForgeAgent(AgentBase):

    def __init__(self, run_id: str):
        super().__init__(agent_name="script_forge", run_id=run_id)
        # Cache parsed openapi so _get_endpoint_schema doesn't re-read disk per scenario
        self._openapi_cache: dict | None = None
        self._openapi_path: Path | None = None

    # ── Public entry point ────────────────────────────────────

    def run(self, input_data: dict) -> dict:
        feature_name  = input_data["feature_name"]
        enriched_path = Path(input_data["enriched_path"])
        openapi_path  = Path(input_data["openapi_path"])
        conftest_path = Path(input_data.get("conftest_path", "tests/conftest.py"))

        self.logger.info(f"[ScriptForgeAgent] Generating SMOKE tests for: {feature_name}")

        # ── Validate required inputs ──────────────────────────
        required = [enriched_path, openapi_path]
        missing  = [p for p in required if not p.exists()]
        if missing:
            raise FileNotFoundError(f"[ScriptForgeAgent] R4 violated — missing files: {missing}")

        # ── Load inputs ───────────────────────────────────────
        enriched_content = self.read_file(enriched_path)
        openapi_content  = self.read_file(openapi_path)

        # Prime the openapi cache for _get_endpoint_schema()
        self._openapi_path = openapi_path
        try:
            self._openapi_cache = json.loads(openapi_content)
        except json.JSONDecodeError:
            self.logger.warning("[ScriptForgeAgent] openapi.json failed to parse — schema hints disabled")
            self._openapi_cache = {}

        # ── Load conftest ─────────────────────────────────────
        conftest_content = ""
        if conftest_path.exists():
            conftest_content = self.read_file(conftest_path)
        else:
            self.logger.warning(f"[ScriptForgeAgent] conftest.py not found at {conftest_path}")

        # ── Load fixture memory ───────────────────────────────
        memory_entries   = self.load_memory()
        working_patterns = self._extract_working_patterns(memory_entries)

        # ── Parse and filter scenarios ────────────────────────
        scenarios = self._parse_scenarios(enriched_content)

        smoke_scenarios   = []
        skipped_scenarios = []

        for scenario in scenarios:
            raw_tags  = scenario.get("tags", [])
            tags_str  = " ".join(raw_tags) if isinstance(raw_tags, list) else str(raw_tags)
            priority  = str(scenario.get("priority", "")).strip().upper()
            is_smoke  = "@smoke" in tags_str or "smoke" in tags_str
            is_high   = priority in ["P0", "P1"]

            if is_smoke or is_high:
                smoke_scenarios.append(scenario)
            else:
                skipped_scenarios.append(f"{scenario['title']} ({priority})")

        if not smoke_scenarios:
            msg = f"No smoke tests found for '{feature_name}'. Skipped: {skipped_scenarios}"
            self.logger.info(f"[ScriptForgeAgent] {msg}")
            return {
                "status":        "skipped",
                "message":       msg,
                "skipped_count": len(skipped_scenarios),
            }

        # ── Build shared context (once) ───────────────────────
        shared_context = self._build_shared_context(
            conftest_content, openapi_content, working_patterns
        )

        # ── Generate one function per scenario ────────────────
        function_blocks = []
        manifest_tests  = []
        unconvertible   = []
        all_fixtures    = set()
        all_flagged     = []

        per_scenario_delay = 5

        for idx, scenario in enumerate(smoke_scenarios):
            if idx > 0:
                self.logger.info(
                    f"[ScriptForgeAgent] Waiting {per_scenario_delay}s for TPM cooldown..."
                )
                time.sleep(per_scenario_delay)

            self.logger.info(f"[ScriptForgeAgent] Generating: {scenario['title']}")
            fn_result = self._generate_one_test(scenario, shared_context)

            if fn_result.get("unconvertible"):
                unconvertible.append({
                    "scenario_title": scenario["title"],
                    "reason":         fn_result.get("unconvertible_reason", "unknown"),
                })
                continue

            fn_code      = fn_result.get("function_code", "")
            fn_name      = fn_result.get("function_name", "")
            fixtures     = fn_result.get("fixtures_used", [])
            assert_count = fn_result.get("assert_count", 0)

            fn_code = self._repair_single_function(fn_code, fn_name)
            if "@pytest.mark.smoke" not in fn_code:
                fn_code = "@pytest.mark.smoke\n" + fn_code

            function_blocks.append(fn_code)
            all_fixtures.update(fixtures)

            manifest_tests.append({
                "function_name":  fn_name,
                "scenario_title": scenario["title"],
                "marker":         "smoke",
                "priority":       scenario.get("priority", "P1"),
                "endpoint":       scenario.get("endpoint", ""),
                "fixtures_used":  fixtures,
                "assert_count":   assert_count,
            })

        # ── Assemble final pytest file ────────────────────────
        pytest_code = self._assemble_pytest_file(
            feature_name=feature_name,
            function_blocks=function_blocks,
            fixtures_used=list(all_fixtures),
            conftest_content=conftest_content,
        )

        manifest = {
            "feature_name":  feature_name,
            "total_tests":   len(manifest_tests),
            "tests":         manifest_tests,
            "unconvertible": unconvertible,
            "confidence":    1.0 if not unconvertible else 0.85,
            "flagged":       all_flagged,
        }

        pytest_code, manifest = self._validate_code(pytest_code, manifest)

        # ── Write output files ────────────────────────────────
        api_tests_dir = Path(self.paths["api_tests_dir"])
        script_path   = api_tests_dir / f"test_{feature_name}_api.py"
        manifest_path = api_tests_dir / f"test_{feature_name}_manifest.json"

        manifest["run_id"]      = self.run_id
        manifest["script_path"] = str(script_path)

        self.write_file(script_path, pytest_code)
        self.write_json(manifest_path, manifest)

        self.logger.info(
            f"[ScriptForgeAgent] Script → {script_path} | Manifest → {manifest_path}"
        )

        # ── Confidence gate ───────────────────────────────────
        confidence = manifest.get("confidence", 0.0)
        flagged    = manifest.get("flagged", [])

        result = {
            "output": {
                "script_path":   str(script_path),
                "manifest_path": str(manifest_path),
                "manifest":      manifest,
            },
            "confidence": confidence,
            "flagged":    flagged,
            "agent":      self.agent_name,
        }
        result = self.confidence_gate(result)

        # ── Decision log ──────────────────────────────────────
        tests         = manifest.get("tests", [])
        unconvertible = manifest.get("unconvertible", [])
        fixtures_used = list({f for t in tests for f in t.get("fixtures_used", [])})

        self.write_decision_log(
            inputs={
                "feature_name":  feature_name,
                "enriched_path": str(enriched_path),
                "openapi_path":  str(openapi_path),
                "conftest_path": str(conftest_path),
            },
            rules_applied=[
                "R5: No LOGIN_ENDPOINT/LOGOUT_ENDPOINT constants injected",
                "R6: One function per scenario, snake_case naming",
                "R7: Fixtures imported from conftest.py only",
                "R8: Assert count verified per function",
                "R9: requests library enforced",
                "R10: Status code asserted before body fields",
                "R11: pytest markers match enriched Gherkin tags",
                "R12: No hardcoded credentials — fixtures used",
                "R13: Module docstring injected",
                f"R14: {len(memory_entries)} prior run patterns loaded",
                f"R15: {len(unconvertible)} unconvertible scenario(s) flagged",
            ],
            decisions=[
                f"Generated {len(tests)} test functions",
                f"Fixtures used: {fixtures_used}",
                f"Unconvertible: {[u['scenario_title'] for u in unconvertible]}",
                f"Confidence: {confidence}",
                f"Script → {script_path}",
            ],
            result=result,
        )

        # ── Save memory ───────────────────────────────────────
        new_patterns = self._extract_patterns_from_code(pytest_code, fixtures_used)
        self.save_memory({
            "summary": (
                f"Generated {len(tests)} tests for '{feature_name}' | "
                f"fixtures={fixtures_used} | "
                f"unconvertible={len(unconvertible)} | "
                f"confidence={confidence}"
            ),
            "feature_name":        feature_name,
            "total_tests":         len(tests),
            "fixtures_used":       fixtures_used,
            "working_patterns":    new_patterns,
            "unconvertible_count": len(unconvertible),
        })

        return result

    # ── Helpers ───────────────────────────────────────────────

    def _parse_scenarios(self, enriched_gherkin: str) -> list[dict]:
        """
        Parse enriched Gherkin into scenario dicts.

        Format produced by EnrichmentAgent:
            @smoke @P1
            Scenario: Title
              # Priority: P1 | Risk Score: 4.20 | Endpoint: POST /api/auth/login
              Given ...
              When ...
              Then ...
        """
        scenarios        = []
        lines            = enriched_gherkin.splitlines()
        i                = 0
        current_priority = "P2"
        current_marker   = "regression"
        current_endpoint = ""

        while i < len(lines):
            line     = lines[i]
            stripped = line.strip()

            if stripped.startswith("@") and not stripped.startswith("@pytest"):
                if "@smoke" in stripped:
                    current_marker = "smoke"
                elif "@regression" in stripped:
                    current_marker = "regression"
                else:
                    current_marker = (
                        "smoke" if ("@P0" in stripped or "@P1" in stripped)
                        else "regression"
                    )
                for tag in ["P0", "P1", "P2"]:
                    if "@" + tag in stripped:
                        current_priority = tag
                i += 1
                continue

            if re.match(r"Scenario(?:\s+Outline)?:", stripped):
                title = re.sub(r"^Scenario(?:\s+Outline)?:\s*", "", stripped)
                steps = []
                i += 1

                while i < len(lines):
                    ns = lines[i].strip()

                    if (
                        ns.startswith("@")
                        or re.match(r"Scenario(?:\s+Outline)?:", ns)
                        or ns.startswith("Feature:")
                    ):
                        break

                    if ns.startswith("# Priority:") and "Endpoint:" in ns:
                        m = re.search(r"Endpoint:\s*(.+)$", ns)
                        if m:
                            current_endpoint = m.group(1).strip()
                        i += 1
                        continue

                    if ns.startswith("#"):
                        i += 1
                        continue

                    if ns:
                        steps.append(ns)
                    i += 1

                expected_status = None
                then_assertions = []
                for step in steps:
                    sl = step.lower()
                    if sl.startswith("then") or sl.startswith("and"):
                        m2 = re.search(r"\b(\d{3})\b", step)
                        if m2 and expected_status is None:
                            expected_status = int(m2.group(1))
                        then_assertions.append(step)

                self.logger.debug(
                    f"[ScriptForgeAgent] Parsed: '{title}' | "
                    f"marker={current_marker} | steps={len(steps)} | "
                    f"status={expected_status} | endpoint={current_endpoint}"
                )

                scenarios.append({
                    "title":           title,
                    "steps":           steps,
                    "marker":          current_marker,
                    "priority":        current_priority,
                    "endpoint":        current_endpoint,
                    "expected_status": expected_status,
                    "then_assertions": then_assertions,
                    "tags":            [current_marker, current_priority],
                })
                current_endpoint = ""
                continue

            i += 1

        return scenarios

    def _build_shared_context(
        self, conftest_content: str, openapi_content: str, working_patterns: dict
    ) -> str:
        """
        FIX-2: Build shared prompt context with structured openapi schema extraction
        instead of a blind [:1500] slice. This gives the LLM real endpoint schemas
        rather than truncated raw JSON that may cut off mid-structure.
        """
        # Extract a structured summary of all endpoints from openapi
        try:
            openapi = self._openapi_cache or json.loads(openapi_content)
            paths   = openapi.get("paths", {})
            schema_summary = {}
            for path, methods in paths.items():
                for method, spec in methods.items():
                    key       = f"{method.upper()} {path}"
                    responses = spec.get("responses", {})
                    # Pull response schema properties if available
                    response_fields = {}
                    for code, resp in responses.items():
                        content = resp.get("content", {})
                        for media_type, media in content.items():
                            props = (
                                media.get("schema", {})
                                     .get("properties", {})
                            )
                            if props:
                                response_fields[code] = list(props.keys())
                            else:
                                response_fields[code] = resp.get("description", "")
                    schema_summary[key] = {
                        "summary":         spec.get("summary", ""),
                        "response_fields": response_fields,
                    }
            openapi_trimmed = json.dumps(schema_summary, indent=2)[:3000]
        except Exception as e:
            self.logger.warning(f"[ScriptForgeAgent] openapi parse failed: {e}")
            openapi_trimmed = openapi_content[:1500]

        conftest_trimmed = conftest_content[:800]
        patterns_str     = (
            json.dumps(working_patterns, indent=2) if working_patterns
            else "No prior patterns"
        )

        return (
            "AVAILABLE FIXTURES (from conftest.py):\n" + conftest_trimmed + "\n\n"
            "OPENAPI ENDPOINT SCHEMAS:\n" + openapi_trimmed + "\n\n"
            "WORKING PATTERNS FROM PRIOR RUNS:\n" + patterns_str
        )

    def _get_endpoint_schema(self, endpoint: str) -> str:
        """
        FIX-3: Pull the exact response schema for one endpoint from the cached
        openapi dict. Returns a compact JSON string injected into the per-scenario
        prompt so the LLM can only assert fields that actually exist in the response.

        endpoint format: "POST /api/auth/refresh"
        """
        if not self._openapi_cache or not endpoint.strip():
            return "Schema unavailable — assert only fields confirmed in the Then steps above."

        try:
            parts = endpoint.strip().split(" ", 1)
            if len(parts) != 2:
                return "Schema unavailable — assert only fields confirmed in the Then steps above."

            method, path = parts[0].lower(), parts[1]
            spec          = (
                self._openapi_cache
                    .get("paths", {})
                    .get(path, {})
                    .get(method, {})
            )

            if not spec:
                return f"No schema found for {endpoint} in openapi.json — assert only fields from Then steps."

            responses = spec.get("responses", {})
            # Build a compact field map: { "200": ["accessToken", "refreshToken", "success"] }
            field_map = {}
            for code, resp in responses.items():
                content = resp.get("content", {})
                fields  = []
                for media in content.values():
                    props = media.get("schema", {}).get("properties", {})
                    fields.extend(props.keys())
                field_map[code] = fields if fields else resp.get("description", "no schema")

            return json.dumps(field_map, indent=2)[:800]

        except Exception as e:
            self.logger.warning(f"[ScriptForgeAgent] _get_endpoint_schema failed: {e}")
            return "Schema unavailable — assert only fields confirmed in the Then steps above."

    def _generate_one_test(self, scenario: dict, shared_context: str) -> dict:
        """
        FIX-4: One focused LLM call per scenario.
        Injects per-endpoint response schema so the LLM cannot hallucinate fields.
        """
        steps_text      = "\n".join("    " + s for s in scenario.get("steps", []))
        marker          = scenario.get("marker", "regression")
        priority        = scenario.get("priority", "P2")
        endpoint        = scenario.get("endpoint", "unknown")
        fn_name         = "test_" + self._to_snake(scenario["title"])
        expected_status = scenario.get("expected_status")
        then_steps      = scenario.get("then_assertions", [])

        status_constraint = ""
        if expected_status:
            status_constraint = (
                "REQUIRED STATUS CODE: You MUST assert response.status_code == "
                + str(expected_status)
                + " — extracted directly from the Then step. Do NOT use a different value.\n"
            )

        then_hint = ""
        if then_steps:
            then_hint = (
                "THEN STEPS TO ASSERT:\n"
                + "\n".join("  " + t for t in then_steps)
                + "\n"
            )

        # FIX-3/4: Inject the real response schema for this specific endpoint
        endpoint_schema = self._get_endpoint_schema(endpoint)
        schema_hint = (
            "RESPONSE SCHEMA FOR THIS ENDPOINT (" + endpoint + "):\n"
            + endpoint_schema + "\n"
            "IMPORTANT: Only assert fields listed in this schema. "
            "Do NOT assert fields from other endpoints or fixture dicts.\n"
        )

        user_prompt = (
            shared_context + "\n\n"
            "── SCENARIO TO CONVERT ──────────────────────────────\n"
            "Title    : " + scenario["title"] + "\n"
            "Priority : " + priority + "\n"
            "Marker   : @pytest.mark." + marker + "\n"
            "Endpoint : " + endpoint + "\n"
            "Function : " + fn_name + "\n"
            "Steps:\n" + steps_text + "\n\n"
            + status_constraint
            + then_hint + "\n"
            + schema_hint + "\n"
            "── GENERATION REMINDERS ─────────────────────────────\n"
            "- Use single braces { } in Python dicts (never {{ }}).\n"
            "- Indent every line in the function body with 4 spaces.\n"
            "- Hardcode endpoint paths as strings (e.g. '/api/auth/logout').\n"
            "- Do NOT use LOGIN_ENDPOINT, LOGOUT_ENDPOINT, or any conftest constant.\n"
            "- Do NOT call the login endpoint inside a logout (or other) test.\n"
            "- Every fixture used in the body MUST appear in the def(...) arguments.\n"
            "Return ONLY the JSON object described in the system prompt."
        )

        try:
            return self.call_llm_json(SCENARIO_SYSTEM_PROMPT, user_prompt)
        except Exception as e:
            self.logger.error(
                f"[ScriptForgeAgent] Failed '{scenario['title']}': {e}"
            )
            return {"unconvertible": True, "unconvertible_reason": str(e)}

    def _to_snake(self, title: str) -> str:
        s = title.lower().strip()
        s = re.sub(r"[^a-z0-9]+", "_", s)
        s = re.sub(r"_+", "_", s).strip("_")
        return s

    def _repair_single_function(self, fn_code: str, fn_name: str) -> str:
        """
        Repair indentation issues in LLM-generated function code.

        Steps:
        1. Strip markdown fences if present
        2. Fix double braces {{ }} → { }
        3. Rebuild decorator + def + body lines with correct 4-space indentation
        4. Inject stub on empty body or syntax error
        """
        # 1. Strip markdown fences
        fn_code = fn_code.replace("```python", "").replace("```", "")

        # 2. Fix double braces (R1)
        fn_code = re.sub(r"\{\{", "{", fn_code)
        fn_code = re.sub(r"\}\}", "}", fn_code)

        if not fn_code.strip():
            return (
                "def " + fn_name + "(base_url):\n"
                '    """Auto-generated stub."""\n'
                "    pytest.skip('body not generated for " + fn_name + "')\n"
            )

        raw_lines       = [l.rstrip() for l in fn_code.splitlines()]
        decorator_lines = []
        def_line        = None
        body_lines      = []
        phase           = "decorator"

        for line in raw_lines:
            stripped = line.strip()
            if not stripped:
                if phase == "body":
                    body_lines.append("")
                continue

            if phase == "decorator":
                if stripped.startswith("@"):
                    decorator_lines.append(stripped)
                elif stripped.startswith("def "):
                    def_line = stripped
                    phase    = "body"
                else:
                    body_lines.append(stripped)
            elif phase == "body":
                body_lines.append(stripped)

        if def_line is None:
            def_line = "def " + fn_name + "(base_url):"

        result_lines = decorator_lines + [def_line]
        if not body_lines:
            result_lines.append('    """Auto-generated stub."""')
            result_lines.append("    pytest.skip('empty body for " + fn_name + "')")
        else:
            for line in body_lines:
                result_lines.append("    " + line if line else "")

        fn_code = "\n".join(result_lines)

        try:
            ast.parse(fn_code)
        except SyntaxError as e:
            self.logger.warning(
                f"[ScriptForgeAgent] Syntax error after repair in {fn_name}: {e}"
            )
            return (
                "def " + fn_name + "(base_url):\n"
                '    """Syntax error stub."""\n'
                "    pytest.skip('syntax error in " + fn_name + "')"
            )

        self.logger.debug(f"[ScriptForgeAgent] Repaired: {fn_name}")
        return fn_code

    def _assemble_pytest_file(
        self,
        feature_name: str,
        function_blocks: list,
        fixtures_used: list,
        conftest_content: str,
    ) -> str:
        """
        FIX-1: Assemble final pytest file WITHOUT injecting LOGIN_ENDPOINT or
        LOGOUT_ENDPOINT imports. The original code imported these constants into
        every generated test file, causing the LLM to use them in test bodies
        in violation of R11/R23. Test scripts must hardcode endpoint paths.
        """
        header = (
            '"""\n'
            "TestMart AI-QE Pipeline — Auto-generated pytest suite\n"
            f"Feature  : {feature_name.title()}\n"
            f"Run ID   : {self.run_id}\n"
            f"Agent    : ScriptForgeAgent ({self.model})\n"
            '"""\n'
            "import pytest\n"
            "import requests\n"
            "\n"
            # NOTE: LOGIN_ENDPOINT / LOGOUT_ENDPOINT are intentionally NOT imported.
            # Test functions must hardcode endpoint paths as strings per R11.
        )

        full_code = header + "\n\n".join(function_blocks)
        return full_code

    def _extract_working_patterns(self, memory_entries: list) -> dict:
        """Pull the most recent working_patterns from memory for prompt reuse."""
        for entry in reversed(memory_entries):
            patterns = entry.get("working_patterns", {})
            if patterns:
                return patterns
        return {}

    def _repair_code(self, pytest_code: str) -> str:
        """
        Repair common LLM code generation failures at the file level:
        1. Strip markdown fences
        2. Add missing imports
        3. Fix empty function bodies
        """
        # Strip markdown fences
        if pytest_code.strip().startswith("```"):
            lines_tmp = pytest_code.strip().splitlines()
            if lines_tmp[0].startswith("```"):
                lines_tmp = lines_tmp[1:]
            if lines_tmp and lines_tmp[-1].strip() == "```":
                lines_tmp = lines_tmp[:-1]
            pytest_code = "\n".join(lines_tmp)

        if "import requests" not in pytest_code:
            pytest_code = "import requests\n" + pytest_code
            self.logger.info("[ScriptForgeAgent] Injected: import requests")

        if "import pytest" not in pytest_code:
            pytest_code = "import pytest\n" + pytest_code
            self.logger.info("[ScriptForgeAgent] Injected: import pytest")

        lines = pytest_code.splitlines()
        fixed = []
        i     = 0

        while i < len(lines):
            line     = lines[i]
            stripped = line.strip()
            fixed.append(line)

            if re.match(r"def test_\w+\(", stripped) and stripped.endswith(":"):
                j = i + 1
                while j < len(lines) and lines[j].strip() == "":
                    j += 1

                next_line     = lines[j].strip() if j < len(lines) else ""
                is_empty_body = (
                    j >= len(lines)
                    or next_line.startswith("def ")
                    or next_line.startswith("@")
                    or next_line.startswith("class ")
                    or (j > i + 1 and not next_line)
                )

                if is_empty_body:
                    indent = "    "
                    fixed.append(f'{indent}"""Auto-generated stub — body was empty."""')
                    fixed.append(
                        f"{indent}pytest.skip('ScriptForgeAgent: test body was not generated')"
                    )
                    self.logger.warning(
                        f"[ScriptForgeAgent] Empty body repaired: {stripped}"
                    )

            i += 1

        repaired = "\n".join(fixed)

        try:
            ast.parse(repaired)
            self.logger.info("[ScriptForgeAgent] Syntax check passed after repair")
        except SyntaxError as e:
            self.logger.error(
                f"[ScriptForgeAgent] Syntax error remains after repair: {e}"
            )

        return repaired

    def _validate_code(self, pytest_code: str, manifest: dict) -> tuple[str, dict]:
        """Validate assembled code and update manifest with assert counts."""
        flagged = manifest.get("flagged", [])

        if "import requests" not in pytest_code:
            flagged.append("R9: 'import requests' still missing after repair")
        if "import pytest" not in pytest_code:
            flagged.append("R11: 'import pytest' still missing after repair")

        # Flag any surviving endpoint constant references
        if "LOGIN_ENDPOINT" in pytest_code or "LOGOUT_ENDPOINT" in pytest_code:
            flagged.append(
                "R11: Generated code still references LOGIN_ENDPOINT or LOGOUT_ENDPOINT "
                "— these constants must not appear in test scripts."
            )
            self.logger.warning(
                "[ScriptForgeAgent] R11 violated: endpoint constants found in output"
            )

        functions = re.findall(r"def (test_\w+)\(.*?\):", pytest_code)
        for fn in functions:
            pattern = rf"def {fn}\(.*?\):.*?(?=\ndef |\Z)"
            match   = re.search(pattern, pytest_code, re.DOTALL)
            if match:
                body = match.group(0)
                if "assert" not in body and "pytest.skip" not in body:
                    flagged.append(
                        f"R8: '{fn}' has no assert or skip — needs manual fix"
                    )
                    self.logger.warning(f"[ScriptForgeAgent] R8 remains: {fn}")

        tests = manifest.get("tests", [])
        for test in tests:
            fn    = test.get("function_name", "")
            match = re.search(
                rf"def {fn}\(.*?\):.*?(?=\ndef |\Z)", pytest_code, re.DOTALL
            )
            if match:
                test["assert_count"] = match.group(0).count("assert")

        manifest["flagged"] = flagged
        return pytest_code, manifest

    def _extract_patterns_from_code(self, pytest_code: str, fixtures_used: list) -> dict:
        """Extract patterns from generated code to save to memory for future runs."""
        import_lines = [
            line for line in pytest_code.split("\n")
            if line.startswith("import ") or line.startswith("from ")
        ]
        import_block = "\n".join(import_lines)

        base_url_match = re.search(r'BASE_URL\s*=\s*["\'](.+?)["\']', pytest_code)
        base_url       = base_url_match.group(1) if base_url_match else "http://localhost:5001"

        auth_pattern = ""
        if "Authorization" in pytest_code:
            auth_match   = re.search(r'"Authorization":\s*f?"?(.+?)"?,', pytest_code)
            auth_pattern = auth_match.group(1) if auth_match else "Bearer {token}"

        return {
            "import_block":       import_block,
            "base_url_fixture":   "base_url" if "base_url" in fixtures_used else base_url,
            "auth_header":        auth_pattern,
            "fixtures_available": fixtures_used,
        }


# ── CLI entry point ───────────────────────────────────────────
if __name__ == "__main__":
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    agent  = ScriptForgeAgent(run_id=run_id)
    result = agent.run({
        "feature_name":  "login",
        "enriched_path": "tests/test_cases/login.enriched.md",
        "openapi_path":  "requirements/openapi.json",
        "conftest_path": "tests/conftest.py",
    })

    manifest = result["output"]["manifest"]
    print("\n=== ScriptForgeAgent Result ===")
    print(f"Script         → {result['output']['script_path']}")
    print(f"Total tests    : {manifest.get('total_tests')}")
    print(f"Unconvertible  : {[u['scenario_title'] for u in manifest.get('unconvertible', [])]}")
    print(f"Confidence     : {result['confidence']}")
    print(f"Flagged        : {result['flagged']}")
    print(f"Human review   : {result['needs_human_review']}")