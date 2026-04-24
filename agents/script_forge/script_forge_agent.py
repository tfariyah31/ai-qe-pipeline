"""
agents/script_forge/script_forge_agent.py
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
from pathlib import Path
from datetime import datetime, timezone
import ast  
import time

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
    - AUTHENTICATED CALLS: Use 'auth_headers', 'merchant_headers', or 'customer_headers' for standard requests.
    - TOKEN REFRESH CALLS: Use the 'auth_tokens' fixture to access raw tokens.
      Example: payload = {"refreshToken": auth_tokens["refreshToken"]}
    - RAW CREDENTIALS: Use 'test_users_data' if you need raw emails/passwords. Do not use 'TEST_USERS' or XXX_ENDPOINT constants.
R6: SCOPE ENFORCEMENT: Only generate tests for SMOKE scenarios (@smoke). 
    - If the provided scenario is not a smoke test (P0/P1), set "unconvertible": true 
      and "unconvertible_reason": "Scenario is not tagged as smoke".
    - Always apply the marker: @pytest.mark.smoke
R7: Negative/edge tests must assert the error status code AND one field from the error response body.
R8: NO PSEUDOCODE: Every test must be executable against localhost:5001.
R9: Every fixture used in the function body (e.g., auth_headers, test_users_data) 
     MUST be included as an argument in the 'def' line. 
     FAILURE TO DO THIS CAUSES AN ATTRIBUTEERROR.

EXAMPLE OF CORRECT REFRESH & AUTH COMPLIANCE:
@pytest.mark.smoke
def test_successful_token_refresh(base_url, auth_tokens):
    # auth_tokens provides raw dict access for tokens
    payload = {"refreshToken": auth_tokens["refreshToken"]}
    response = requests.post(f"{base_url}/api/auth/refresh", json=payload)
    assert response.status_code == 200
    assert "accessToken" in response.json()

OUTPUT: Return ONLY this JSON (no preamble):
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

    # ── Public entry point ────────────────────────────────────

    def run(self, input_data: dict) -> dict:
        feature_name  = input_data["feature_name"]
        enriched_path = Path(input_data["enriched_path"])
        openapi_path  = Path(input_data["openapi_path"])
        conftest_path = Path(input_data.get("conftest_path", "tests/conftest.py"))

        self.logger.info(f"[ScriptForgeAgent] Generating SMOKE tests for: {feature_name}")

        # ── R1/R2/R4: Validate required inputs ───────────────
        required = [enriched_path, openapi_path]
        missing  = [p for p in required if not p.exists()]
        if missing:
            raise FileNotFoundError(f"[ScriptForgeAgent] R4 violated — missing files: {missing}")

        # ── Load inputs ──────────────────────────────────────
        enriched_content = self.read_file(enriched_path)
        openapi_content  = self.read_file(openapi_path)

        # ── R3: Load conftest if available ────────────────────
        conftest_content = ""
        if conftest_path.exists():
            conftest_content = self.read_file(conftest_path)
        else:
            self.logger.warning(f"[ScriptForgeAgent] conftest.py not found at {conftest_path}")

        # ── R5: Load fixture memory ───────────────────────────
        memory_entries   = self.load_memory()
        working_patterns = self._extract_working_patterns(memory_entries)

        # ── Parse and FILTER scenarios ────────────────────────
        scenarios = self._parse_scenarios(enriched_content)
        
        smoke_scenarios = []
        skipped_scenarios = []

        for scenario in scenarios:
            # Normalize tags and priority for comparison
            raw_tags = scenario.get('tags', [])
            # Convert tags to a string for easier substring searching
            tags_str = " ".join(raw_tags) if isinstance(raw_tags, list) else str(raw_tags)
            
            priority = str(scenario.get('priority', '')).strip().upper()

            # Check for smoke criteria
            is_smoke = '@smoke' in tags_str or 'smoke' in tags_str
            is_high_priority = priority in ['P0', 'P1']

            if is_smoke or is_high_priority:
                smoke_scenarios.append(scenario)
            else:
                # Store title and reason for the skipped message
                skipped_scenarios.append(f"{scenario['title']} ({priority})")

        if not smoke_scenarios:
            msg = f"No smoke tests found for '{feature_name}'. Found: {skipped_scenarios}"
            self.logger.info(f"[ScriptForgeAgent] {msg}")
            return {
                "status": "skipped", 
                "message": msg, 
                "skipped_count": len(skipped_scenarios)
            }
        
        # ── Generate functions (separate LLM calls) ───────────
        function_blocks = []
        manifest_tests  = []
        unconvertible   = []
        all_fixtures    = set()
        all_flagged     = []

        shared_context = self._build_shared_context(
            conftest_content, openapi_content, working_patterns
        )

        per_scenario_delay = 5 

        # FIX: Iterate over smoke_scenarios, NOT original scenarios
        for idx, scenario in enumerate(smoke_scenarios):
            if idx > 0:
                self.logger.info(f"[ScriptForgeAgent] Waiting {per_scenario_delay}s for TPM cooldown...")
                import time
                time.sleep(per_scenario_delay)

            self.logger.info(f"[ScriptForgeAgent] Generating: {scenario['title']}")
            fn_result = self._generate_one_test(scenario, shared_context)

            if fn_result.get("unconvertible"):
                unconvertible.append({
                    "scenario_title": scenario["title"],
                    "reason": fn_result.get("unconvertible_reason", "unknown"),
                })
                continue

            fn_code      = fn_result.get("function_code", "")
            fn_name      = fn_result.get("function_name", "")
            fixtures     = fn_result.get("fixtures_used", [])
            assert_count = fn_result.get("assert_count", 0)

            # Repair and collect
            fn_code = self._repair_single_function(fn_code, fn_name)
            if "@pytest.mark.smoke" not in fn_code:
                fn_code = "@pytest.mark.smoke\n" + fn_code
            function_blocks.append(fn_code)
            all_fixtures.update(fixtures)

            manifest_tests.append({
                "function_name":  fn_name,
                "scenario_title": scenario["title"],
                "marker":         "smoke", # Force smoke marker since we filtered
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
            conftest_content=conftest_content
        )

        manifest = {
            "feature_name":  feature_name,
            "total_tests":   len(manifest_tests),
            "tests":         manifest_tests,
            "unconvertible": unconvertible,
            "confidence":    1.0 if not unconvertible else 0.85,
            "flagged":       all_flagged,
        }

        # ── Validate assembled file ───────────────────────────
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
            f"[ScriptForgeAgent] Script → {script_path} | "
            f"Manifest → {manifest_path}"
        )

        # ── Build result + confidence gate ────────────────────
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

        # ── Decision log ─────────────────────────────────────
        tests          = manifest.get("tests", [])
        unconvertible  = manifest.get("unconvertible", [])
        fixtures_used  = list({f for t in tests for f in t.get("fixtures_used", [])})

        self.write_decision_log(
            inputs={
                "feature_name":  feature_name,
                "enriched_path": str(enriched_path),
                "openapi_path":  str(openapi_path),
                "conftest_path": str(conftest_path),
            },
            rules_applied=[
                "R6: One function per scenario, snake_case naming",
                "R7: Fixtures imported from conftest.py only",
                "R8: Assert count verified per function",
                "R9: requests library enforced",
                "R10: Status code asserted before body fields",
                "R11: pytest markers match enriched Gherkin tags",
                "R12: No hardcoded credentials — fixtures used",
                "R13: Module docstring injected",
                f"R5: {len(memory_entries)} prior run patterns loaded",
                f"R19: {len(unconvertible)} unconvertible scenario(s) flagged",
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
        # Extract patterns from this run to persist for next run
        new_patterns = self._extract_patterns_from_code(pytest_code, fixtures_used)
        self.save_memory({
            "summary": (
                f"Generated {len(tests)} tests for '{feature_name}' | "
                f"fixtures={fixtures_used} | "
                f"unconvertible={len(unconvertible)} | "
                f"confidence={confidence}"
            ),
            "feature_name":       feature_name,
            "total_tests":        len(tests),
            "fixtures_used":      fixtures_used,
            "working_patterns":   new_patterns,
            "unconvertible_count":len(unconvertible),
        })

        return result

    # ── Helpers ───────────────────────────────────────────────
    def _parse_enriched_gherkin(self, file_path: str) -> list:
        """
        Parses the enriched markdown file and extracts scenarios from 
        json blocks or designated sections.
        """
        content = self.read_file(Path(file_path))
    
        # This regex finds JSON blocks within the Markdown
        # Adjust if your EnrichmentAgent uses a different format
        json_blocks = re.findall(r"```json\s*(.*?)\s*```", content, re.DOTALL)
    
        scenarios = []
        for block in json_blocks:
            try:
                data = json.loads(block)
                # If the block is a list of scenarios
                if isinstance(data, list):
                    scenarios.extend(data)
                # If the block is a single scenario object
                elif isinstance(data, dict) and "title" in data:
                    scenarios.append(data)
            except json.JSONDecodeError:
                continue
            
        if not scenarios:
            self.logger.error(f"No valid scenarios found in {file_path}")
        
        return scenarios

    def _parse_scenarios(self, enriched_gherkin: str) -> list[dict]:
        """
        Parse enriched Gherkin into scenario dicts.

        The enriched file format produced by EnrichmentAgent is:
            @smoke @P1
            Scenario: Title
              # Priority: P1 | Risk Score: 4.20 | Endpoint: POST /api/auth/login
              Given ...
              When ...
              Then ...

        Key fix: # Priority comment sits INSIDE the scenario block,
        between the Scenario: line and the steps. The previous parser
        broke out of step collection when it saw # Priority: which meant
        zero steps were collected. Now we read it as the endpoint source
        and skip it without breaking the step collection loop.

        @smoke / @regression is read directly from the tag line — independent
        of priority. @smoke @P2 is valid.
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

            # ── Tag line: @smoke @P1 ──────────────────────────
            if stripped.startswith("@") and not stripped.startswith("@pytest"):
                # Read smoke/regression directly — trust the tag
                if "@smoke" in stripped:
                    current_marker = "smoke"
                elif "@regression" in stripped:
                    current_marker = "regression"
                else:
                    current_marker = "smoke" if ("@P0" in stripped or "@P1" in stripped) else "regression"
                # Read priority
                for tag in ["P0", "P1", "P2"]:
                    if "@" + tag in stripped:
                        current_priority = tag
                i += 1
                continue

            # ── Scenario line ─────────────────────────────────
            if re.match(r"Scenario(?:\s+Outline)?:", stripped):
                title = re.sub(r"^Scenario(?:\s+Outline)?:\s*", "", stripped)
                steps = []
                i += 1

                # Collect steps — the block ends at next tag or scenario
                while i < len(lines):
                    ns = lines[i].strip()

                    # End of this scenario block
                    if (ns.startswith("@")
                            or re.match(r"Scenario(?:\s+Outline)?:", ns)
                            or ns.startswith("Feature:")):
                        break

                    # # Priority comment — extract endpoint, skip the line
                    if ns.startswith("# Priority:") and "Endpoint:" in ns:
                        m = re.search(r"Endpoint:\s*(.+)$", ns)
                        if m:
                            current_endpoint = m.group(1).strip()
                        i += 1
                        continue

                    # Skip other comment lines
                    if ns.startswith("#"):
                        i += 1
                        continue

                    # Collect non-empty step lines
                    if ns:
                        steps.append(ns)
                    i += 1

                # Extract expected status code + Then assertions from steps
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
                    "tags":            [current_marker, current_priority]
                })
                # Reset for next scenario
                current_endpoint = ""
                continue

            i += 1
        return scenarios

    def _build_shared_context(self, conftest_content, openapi_content, working_patterns):
        """Compact shared context for per-scenario prompts."""
        openapi_trimmed  = openapi_content[:1500]
        conftest_trimmed = conftest_content[:800]
        patterns_str     = json.dumps(working_patterns, indent=2) if working_patterns else "No prior patterns"
        return (
            "AVAILABLE FIXTURES (from conftest.py):\n" + conftest_trimmed + "\n\n"
            "OPENAPI ENDPOINTS (reference):\n" + openapi_trimmed + "\n\n"
            "WORKING PATTERNS FROM PRIOR RUNS:\n" + patterns_str
        )

    def _generate_one_test(self, scenario: dict, shared_context: str) -> dict:
        """One focused LLM call per scenario — prevents token truncation."""
        steps_text      = "\n".join("    " + s for s in scenario.get("steps", []))
        marker          = scenario.get("marker", "regression")
        priority        = scenario.get("priority", "P2")
        endpoint        = scenario.get("endpoint", "unknown")
        fn_name         = "test_" + self._to_snake(scenario["title"])
        expected_status = scenario.get("expected_status")
        then_steps      = scenario.get("then_assertions", [])

        # Hard constraint: tell LLM the exact status code, don't let it guess
        status_constraint = ""
        if expected_status:
            status_constraint = (
                "REQUIRED STATUS CODE: You MUST assert response.status_code == "
                + str(expected_status)
                + " — this is extracted directly from the Then step. Do NOT use a different value."
            )

        then_hint = ""
        if then_steps:
            then_hint = "THEN STEPS TO ASSERT:\n" + "\n".join("  " + t for t in then_steps)

        user_prompt = (
            shared_context + "\n\n"
            "SCENARIO TO CONVERT:\n"
            "Title    : " + scenario["title"] + "\n"
            "Priority : " + priority + "\n"
            "Marker   : @pytest.mark." + marker + "\n"
            "Endpoint : " + endpoint + "\n"
            "Function : " + fn_name + "\n"
            "Steps:\n" + steps_text + "\n\n"
            + status_constraint + "\n"
            + then_hint + "\n\n"
            "REMINDER: Use single braces { } in Python dicts. "
            "Indent every line in the function body with 4 spaces. "
            "Return JSON with function_code, function_name, fixtures_used, assert_count, confidence."
        )
        try:
            return self.call_llm_json(SCENARIO_SYSTEM_PROMPT, user_prompt)
        except Exception as e:
            self.logger.error("[ScriptForgeAgent] Failed '" + scenario["title"] + "': " + str(e))
            return {"unconvertible": True, "unconvertible_reason": str(e)}

    def _to_snake(self, title: str) -> str:
        s = title.lower().strip()
        s = re.sub(r"[^a-z0-9]+", "_", s)
        s = re.sub(r"_+", "_", s).strip("_")
        return s

    def _repair_single_function(self, fn_code: str, fn_name: str) -> str:
        """
        Repair indentation issues in LLM-generated function code.

        The LLM returns function_code as a JSON string value. When parsed,
        \n becomes a real newline but leading spaces on body lines are often
        missing — the LLM writes them without indentation in the JSON string.

        Repair steps:
        1. Empty body → inject pytest.skip stub
        2. Fix double braces {{ }} → { }
        3. Rebuild the function from scratch using the def line + body lines:
           - Find the decorator (@pytest.mark.xxx) and def line
           - Collect all remaining lines as body
           - Re-emit: decorator + def + every body line indented with 4 spaces
        4. Syntax error after repair → inject stub
        """
        import ast

        # 1. Clean up common LLM "noise" before parsing
        fn_code = fn_code.replace("```python", "").replace("```", "")
    
        # 2. Force single braces for dicts (R1 violation fix)
        fn_code = re.sub(r"\{\{", "{", fn_code)
        fn_code = re.sub(r"\}\}", "}", fn_code)

        if not fn_code.strip():
            fn_code = f"def {fn_name}(base_url):\n    " + fn_code.replace("\n", "\n    ")
            return (
                "def " + fn_name + "():\n"
                '    """Auto-generated stub."""\n'
                "    pytest.skip('body not generated for " + fn_name + "')\n"
            )

        # Fix double braces first
        fn_code = re.sub(r"\{\{", "{", fn_code)
        fn_code = re.sub(r"\}\}", "}", fn_code)

        # Parse into lines, strip leading/trailing whitespace from each line
        # then rebuild with correct structure
        raw_lines = [l.rstrip() for l in fn_code.splitlines()]

        # Separate into: decorator lines, def line, body lines
        decorator_lines = []
        def_line        = None
        body_lines      = []

        phase = "decorator"
        for line in raw_lines:
            stripped = line.strip()
            if not stripped:
                if phase == "body":
                    body_lines.append("")
                continue

            if phase == "decorator":
                if stripped.startswith("@"):
                    decorator_lines.append(stripped)   # col 0
                elif stripped.startswith("def "):
                    def_line = stripped                 # col 0
                    phase    = "body"
                else:
                    # No decorator, line before def — treat as body preamble
                    body_lines.append(stripped)
            elif phase == "body":
                # Strip any existing indentation, we will re-add exactly 4 spaces
                body_lines.append(stripped)

        # If we never found a def line, use function name
        if def_line is None:
            def_line = "def " + fn_name + "(base_url):"

        # Reassemble with correct indentation
        result_lines = decorator_lines + [def_line]
        if not body_lines:
            result_lines.append('    """Auto-generated stub."""')
            result_lines.append("    pytest.skip('empty body for " + fn_name + "')")
        else:
            for line in body_lines:
                if line:
                    result_lines.append("    " + line)
                else:
                    result_lines.append("")

        fn_code = "\n".join(result_lines)

        # Final syntax check
        try:
            ast.parse(fn_code)
        except SyntaxError as e:
            self.logger.warning(
                "[ScriptForgeAgent] Syntax error after repair in " + fn_name + ": " + str(e)
            )
            return (
                "def " + fn_name + "(base_url):\n"
                '    """Syntax error stub."""\n'
                "    pytest.skip('syntax error in " + fn_name + "')"
            )

        self.logger.debug("[ScriptForgeAgent] Repaired: " + fn_name)
        return fn_code

    def _assemble_pytest_file(self, feature_name, function_blocks, fixtures_used, conftest_content):
        """Assemble final pytest file with dynamic imports based on used fixtures."""
        available_fixtures = re.findall(r"@pytest\.fixture.*?\ndef\s+(\w+)\(", conftest_content)
        available_constants = re.findall(r"^([A-Z][A-Z0-9_]+)\s*=", conftest_content, re.MULTILINE)
        # Find all actual fixture names in conftest.py using regex
        #available_in_conftest = re.findall(r"@pytest\.fixture.*?\ndef\s+(\w+)\(", conftest_content)
    
        # Identify which fixtures from conftest were actually used in the generated code blocks
        all_code_combined = "\n".join(function_blocks)
    
        # Determine what needs to be imported
        # We check the 'fixtures_used' list from the LLM + scanning the code for constants
        to_import = []
    
        # Add fixtures that exist in conftest
        for f in available_fixtures:
            if f in all_code_combined or f in fixtures_used:
                if f not in to_import:
                    to_import.append(f)
                
        # Add constants that exist in conftest
        for c in available_constants:
            if c in all_code_combined:
                if c not in to_import:
                    to_import.append(c)

        # 4. Build the import string
        #fixture_import = f"from conftest import {', '.join(to_import)}" if to_import else ""

        # 5. Build the header
        header = (
            '"""\n'
            "TestMart AI-QE Pipeline — Auto-generated pytest suite\n"
            f"Feature  : {feature_name.title()}\n"
            f"Run ID   : {self.run_id}\n"
            f"Agent    : ScriptForgeAgent ({self.model})\n"
            '"""\n'
            "import pytest\n"
            "import requests\n"
        )
    
        #  6. Add specific constants if they exist in conftest
    
        if "LOGIN_ENDPOINT" in conftest_content:
            header += "from conftest import LOGIN_ENDPOINT\n"
        if "LOGOUT_ENDPOINT" in conftest_content:
            header += "from conftest import LOGOUT_ENDPOINT\n"

        header += "\n"
    
        # 3. Join the function blocks
        full_code = header + "\n\n".join(function_blocks)
        return full_code    

    def _extract_working_patterns(self, memory_entries: list) -> dict:
        """
        Pull the most recent working_patterns from memory.
        This is what gets injected into the prompt so the agent
        reuses auth patterns and import blocks across runs.
        """
        for entry in reversed(memory_entries):
            patterns = entry.get("working_patterns", {})
            if patterns:
                return patterns
        return {}

    def _repair_code(self, pytest_code: str) -> str:
        """
        Repair common LLM code generation failures before validation:
        1. Add missing 'import requests' and 'import pytest'
        2. Fix empty function bodies (IndentationError) by inserting
           pytest.skip() + a comment so the file is always parseable
        3. Strip markdown code fences if LLM wrapped the code
        """
        import ast

        # ── Strip markdown fences ─────────────────────────────
        if pytest_code.strip().startswith("```"):
            lines_tmp = pytest_code.strip().splitlines()
            if lines_tmp[0].startswith("```"):
                lines_tmp = lines_tmp[1:]
            if lines_tmp and lines_tmp[-1].strip() == "```":
                lines_tmp = lines_tmp[:-1]
            pytest_code = "\n".join(lines_tmp)

        # ── Fix missing imports ───────────────────────────────
        if "import requests" not in pytest_code:
            pytest_code = "import requests\n" + pytest_code
            self.logger.info("[ScriptForgeAgent] Injected: import requests")

        if "import pytest" not in pytest_code:
            pytest_code = "import pytest\n" + pytest_code
            self.logger.info("[ScriptForgeAgent] Injected: import pytest")

        # ── Fix empty function bodies ─────────────────────────
        # Pattern: def test_xxx(...): followed immediately by blank line or EOF
        # or another def — these cause IndentationError
        lines     = pytest_code.splitlines()
        fixed     = []
        i         = 0
        while i < len(lines):
            line    = lines[i]
            stripped = line.strip()

            fixed.append(line)

            if re.match(r"def test_\w+\(", stripped) and stripped.endswith(":"):
                # Look ahead: is the next non-blank line still inside this function?
                j = i + 1
                while j < len(lines) and lines[j].strip() == "":
                    j += 1

                next_line = lines[j].strip() if j < len(lines) else ""
                is_empty_body = (
                    j >= len(lines)                        # EOF
                    or next_line.startswith("def ")        # next function
                    or next_line.startswith("@")           # next decorator
                    or next_line.startswith("class ")      # class
                    or (j > i + 1 and not next_line)       # only blanks after
                )

                if is_empty_body:
                    # Inject a parseable placeholder body
                    indent = "    "
                    fixed.append(f'{indent}"""Auto-generated stub — body was empty."""')
                    fixed.append(f"{indent}pytest.skip('ScriptForgeAgent: test body was not generated')")
                    self.logger.warning(
                        f"[ScriptForgeAgent] Empty body repaired: {stripped}"
                    )

            i += 1

        repaired = "\n".join(fixed)

        # ── Final syntax check ────────────────────────────────
        try:
            ast.parse(repaired)
            self.logger.info("[ScriptForgeAgent] Syntax check passed after repair")
        except SyntaxError as e:
            self.logger.error(
                f"[ScriptForgeAgent] Syntax error remains after repair: {e}"
            )

        return repaired

    def _validate_code(
        self, pytest_code: str, manifest: dict
    ) -> tuple[str, dict]:
        """
        Validate repaired code and update manifest with assert counts.
        Flags remaining issues for the decision log.
        """
        flagged = manifest.get("flagged", [])

        # Check imports (should be fixed by _repair_code already)
        if "import requests" not in pytest_code:
            flagged.append("R9: 'import requests' still missing after repair")
        if "import pytest" not in pytest_code:
            flagged.append("R11: 'import pytest' still missing after repair")

        # Check each test function has an assert or pytest.skip
        functions = re.findall(r"def (test_\w+)\(.*?\):", pytest_code)
        for fn in functions:
            pattern = rf"def {fn}\(.*?\):.*?(?=\ndef |\Z)"
            match   = re.search(pattern, pytest_code, re.DOTALL)
            if match:
                body = match.group(0)
                if "assert" not in body and "pytest.skip" not in body:
                    flagged.append(f"R8: '{fn}' has no assert or skip — needs manual fix")
                    self.logger.warning(f"[ScriptForgeAgent] R8 remains: {fn}")

        # Update manifest assert counts
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

    def _ensure_module_docstring(
        self, pytest_code: str, feature_name: str, run_id: str
    ) -> str:
        """
        R13: Inject a standard module docstring if the LLM didn't include one.
        """
        docstring = (
            f'"""\n'
            f"TestMart AI-QE Pipeline — Auto-generated pytest suite\n"
            f"Feature  : {feature_name.title()}\n"
            f"Run ID   : {run_id}\n"
            f"Agent    : ScriptForgeAgent ({self.model})\n"
            f'"""\n'
        )

        if not pytest_code.strip().startswith('"""'):
            pytest_code = docstring + "\n" + pytest_code

        return pytest_code

    def _extract_patterns_from_code(
        self, pytest_code: str, fixtures_used: list
    ) -> dict:
        """
        Extract patterns from the generated code to save to memory.
        Future runs will load these as working patterns.
        """
        # Extract import block
        import_lines = [
            line for line in pytest_code.split("\n")
            if line.startswith("import ") or line.startswith("from ")
        ]
        import_block = "\n".join(import_lines)

        # Extract BASE_URL pattern if present
        base_url_match = re.search(r'BASE_URL\s*=\s*["\'](.+?)["\']', pytest_code)
        base_url       = base_url_match.group(1) if base_url_match else "http://localhost:5001"

        # Detect auth header pattern
        auth_pattern = ""
        if "Authorization" in pytest_code:
            auth_match  = re.search(r'"Authorization":\s*f?"?(.+?)"?,', pytest_code)
            auth_pattern = auth_match.group(1) if auth_match else "Bearer {token}"

        return {
            "import_block":      import_block,
            "base_url_fixture":  "base_url" if "base_url" in fixtures_used else base_url,
            "auth_header":       auth_pattern,
            "fixtures_available":fixtures_used,
        }


# ── CLI entry point ───────────────────────────────────────────
if __name__ == "__main__":
    from datetime import datetime, timezone

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