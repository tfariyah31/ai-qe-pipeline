"""
agents/gherkin_author/gherkin_author_agent.py
=============================================
GherkinAuthorAgent — Agent 2 of 6

Reads spec_analysis.json (from SpecAnalystAgent) and the original
feature spec, then writes Gherkin scenarios + a JSON manifest.

Input:
    feature_name       — e.g. "login"
    spec_analysis_path — path to login_spec_analysis.json
    spec_path          — path to LOGIN_FEATURES.md

Output:
    tests/test_cases/{feature}.test_case.md   — Gherkin scenarios
    tests/test_cases/{feature}.manifest.json  — scenario manifest
    Decision log → logs/run_{id}/gherkin_author_decision.log
    Memory entry → agent_memory/gherkin_author_memory.json
"""

import json
import re
from pathlib import Path

from agents.base_agent import AgentBase


SYSTEM_PROMPT = """
You are GherkinAuthorAgent — Agent 2 in a QE pipeline.

ROLE:
Write Gherkin BDD test scenarios from a structured spec analysis.
You are disciplined: creative enough to cover edge cases,
strict enough to never invent what isn't in the spec.

RULES (hard constraints — never violate):
R5:  Every scenario MUST map to an endpoint in the spec_analysis endpoints list.
R6:  Every scenario MUST have Given / When / Then. No exceptions.
R7:  The "When" step MUST reference a real HTTP method + path from the analysis
     (e.g. "When I POST to /api/auth/login"). Never invent paths.
R8:  The "Then" step MUST include a concrete assertion — status code, response
     field, or error message. Vague assertions like "Then it works" are FORBIDDEN.
R9:  Write at least 1 negative or edge case scenario per endpoint.
R10: Do not exceed 15 scenarios total. If the spec needs more, flag it.
R11: Scenario titles must be unique.
R12: You MUST write a tag line immediately before EVERY Scenario keyword.
     Use @smoke for happy path and high-frequency flows.
     Use @regression for negative, edge case, and error flows.
     Format — the tag must be on its own line before Scenario:
       @smoke
       Scenario: Successful login
         Given ...
     A Scenario with no tag above it is a RULE VIOLATION.
     Do NOT assign P0/P1/P2 — that is EnrichmentAgent's job.
R13: Never copy-paste spec text verbatim. Rewrite in BDD voice.

OUTPUT FORMAT — return a JSON object with two keys:

{
  "gherkin": "string — the full Gherkin markdown content",
  "manifest": {
    "feature_name": "string",
    "total_scenarios": <integer>,
    "scenarios": [
      {
        "title":       "string",
        "tag":         "@smoke or @regression",
        "endpoint":    "METHOD /path",
        "spec_source": "string",
        "type":        "happy_path | negative | edge_case"
      }
    ],
    "confidence": <float 0.0-1.0>,
    "flagged": ["string"]
  }
}
"""


class GherkinAuthorAgent(AgentBase):

    def __init__(self, run_id: str):
        super().__init__(agent_name="gherkin_author", run_id=run_id)
        self.max_scenarios = (
            self.agent_cfg
            .get("limits", {})
            .get("max_scenarios_per_feature", 15)
        )

    def run(self, input_data: dict) -> dict:
        """
        Args:
            input_data = {
                "feature_name":       "login",
                "spec_analysis_path": "requirements/login_spec_analysis.json",
                "spec_path":          "requirements/LOGIN_FEATURES.md"
            }
        Returns:
            {
                "output":     { "gherkin_path": str, "manifest_path": str, "manifest": dict },
                "confidence": float,
                "flagged":    list,
                "agent":      "gherkin_author"
            }
        """
        feature_name       = input_data["feature_name"]
        spec_analysis_path = Path(input_data["spec_analysis_path"])
        spec_path          = Path(input_data["spec_path"])

        self.logger.info(f"[GherkinAuthorAgent] Writing scenarios for: {feature_name}")

        # ── R1/R3: Validate inputs ────────────────────────────
        missing = [p for p in [spec_analysis_path, spec_path] if not p.exists()]
        if missing:
            raise FileNotFoundError(
                f"[GherkinAuthorAgent] R3 violated — missing files: {missing}"
            )

        # ── Load inputs ──────────────────────────────────────
        spec_analysis = self.read_json(spec_analysis_path)
        spec_content  = self.read_file(spec_path)

        # ── R4: Load memory for recurring gaps ───────────────
        memory_entries = self.load_memory()
        memory_context = self.format_memory_for_prompt(memory_entries)

        # ── Extract memory gaps to inject as reminders ────────
        recurring_gaps = []
        for entry in memory_entries[-3:]:           # last 3 runs
            recurring_gaps.extend(entry.get("recurring_gaps", []))
        gap_reminder = ""
        if recurring_gaps:
            gap_reminder = (
                "\nRECURRING GAPS FROM PRIOR RUNS — address these:\n"
                + "\n".join(f"  • {g}" for g in set(recurring_gaps))
            )

        # ── Build user prompt ────────────────────────────────
        user_prompt = f"""
{memory_context}
{gap_reminder}

FEATURE NAME: {feature_name}
MAX SCENARIOS ALLOWED: {self.max_scenarios}

=== SPEC ANALYSIS (from SpecAnalystAgent) ===
{json.dumps(spec_analysis, indent=2)}

=== ORIGINAL FEATURE SPEC ===
{spec_content}

Write Gherkin scenarios following your rules exactly.
Cover every endpoint in the spec analysis.
Include at least 1 negative/edge case per endpoint.
Return the JSON object with "gherkin" and "manifest" keys.
"""

        # ── Call LLM (JSON mode) ─────────────────────────────
        raw_result = self.call_llm_json(SYSTEM_PROMPT, user_prompt)

        gherkin_content = raw_result.get("gherkin", "")
        manifest        = raw_result.get("manifest", {})
        total_scenarios = manifest.get("total_scenarios", 0)
        confidence      = manifest.get("confidence", 0.0)
        flagged         = manifest.get("flagged", [])

        # ── R10: Enforce scenario cap ─────────────────────────
        if total_scenarios > self.max_scenarios:
            flagged.append(
                f"R10 violation: {total_scenarios} scenarios generated, "
                f"max is {self.max_scenarios}. Human approval required."
            )
            self.logger.warning(
                f"[GherkinAuthorAgent] Scenario cap exceeded: "
                f"{total_scenarios} > {self.max_scenarios}"
            )
            confidence = min(confidence, 0.60)      # force escalation

        manifest["flagged"]    = flagged
        manifest["confidence"] = confidence

        # ── Write Gherkin file ───────────────────────────────
        test_cases_dir = Path(self.paths["test_cases_dir"])
        gherkin_path   = test_cases_dir / f"{feature_name}.test_case.md"
        manifest_path  = test_cases_dir / f"{feature_name}.manifest.json"

        self.write_file(gherkin_path, gherkin_content)
        self.write_json(manifest_path, manifest)

        self.logger.info(
            f"[GherkinAuthorAgent] Gherkin → {gherkin_path} | "
            f"Manifest → {manifest_path}"
        )

        # ── Build result + confidence gate ────────────────────
        result = {
            "output": {
                "gherkin_path":  str(gherkin_path),
                "manifest_path": str(manifest_path),
                "manifest":      manifest,
            },
            "confidence": confidence,
            "flagged":    flagged,
            "agent":      self.agent_name,
        }
        result = self.confidence_gate(result)

        # ── Decision log ─────────────────────────────────────
        endpoints_covered = list({
            s.get("endpoint", "") for s in manifest.get("scenarios", [])
        })
        self.write_decision_log(
            inputs={
                "feature_name":       feature_name,
                "spec_analysis_path": str(spec_analysis_path),
                "spec_path":          str(spec_path),
            },
            rules_applied=[
                "R5: Scenarios mapped to spec_analysis endpoints only",
                "R6: Given/When/Then enforced via prompt",
                "R7: HTTP method+path referenced in When step",
                "R8: Concrete assertions required in Then step",
                "R9: At least 1 negative/edge case per endpoint",
                f"R10: Scenario cap {self.max_scenarios} {'respected' if total_scenarios <= self.max_scenarios else 'EXCEEDED — flagged'}",
                "R12: @smoke/@regression tags applied",
                f"R4: Memory gaps injected: {len(recurring_gaps)} recurring issues addressed",
            ],
            decisions=[
                f"Generated {total_scenarios} scenarios",
                f"Endpoints covered: {endpoints_covered}",
                f"Confidence: {confidence}",
                f"Flagged: {flagged}",
            ],
            result=result,
        )

        # ── Save memory ───────────────────────────────────────
        # Detect gaps: endpoints in analysis not covered in scenarios
        analysis_endpoints = {
            f"{e['method']} {e['path']}"
            for e in spec_analysis.get("endpoints", [])
        }
        covered_endpoints = set(endpoints_covered)
        gaps = list(analysis_endpoints - covered_endpoints)

        self.save_memory({
            "summary": (
                f"Wrote {total_scenarios} scenarios for '{feature_name}' | "
                f"confidence={confidence} | gaps={gaps}"
            ),
            "feature_name":         feature_name,
            "total_scenarios":      total_scenarios,
            "endpoints_covered":    list(covered_endpoints),
            "recurring_gaps":       gaps,
            "patterns_that_worked": [
                s["title"] for s in manifest.get("scenarios", [])
                if s.get("type") == "edge_case"
            ],
        })

        return result


# ── CLI entry point ───────────────────────────────────────────
if __name__ == "__main__":
    import sys
    from datetime import datetime

    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    agent = GherkinAuthorAgent(run_id=run_id)
    result = agent.run({
        "feature_name":       "login",
        "spec_analysis_path": "requirements/login_spec_analysis.json",
        "spec_path":          "requirements/LOGIN_FEATURES.md",
    })

    print("\n=== GherkinAuthorAgent Result ===")
    print(f"Gherkin  → {result['output']['gherkin_path']}")
    print(f"Manifest → {result['output']['manifest_path']}")
    print(f"Confidence        : {result['confidence']}")
    print(f"Flagged           : {result['flagged']}")
    print(f"Human review needed: {result['needs_human_review']}")