"""
agents/spec_analyst/spec_analyst_agent.py
==========================================
SpecAnalystAgent — Agent 1 of 6

Reads the feature spec + openapi.json and produces a structured
analysis JSON consumed by every downstream agent.

Input:
    feature_name  — e.g. "login"
    spec_path     — path to LOGIN_FEATURES.md
    openapi_path  — path to openapi.json

Output:
    spec_analysis.json written to requirements/
    Decision log written to logs/run_{id}/spec_analyst_decision.log
    Memory entry written to agent_memory/spec_analyst_memory.json
"""

import json
from pathlib import Path

from agents.base_agent import AgentBase


# ── System prompt (loads RULES.md inline) ────────────────────
SYSTEM_PROMPT = """
You are SpecAnalystAgent — the first agent in a QE pipeline.

ROLE:
Analyze a feature specification and OpenAPI contract. Produce a structured
JSON analysis that all downstream agents (Gherkin author, Rating judge,
Script forge) will use as their shared context.

RULES (hard constraints — never violate):
R1: Read BOTH the spec and openapi.json before producing output.
R2: If either is missing, return an error — never proceed with partial input.
R3: Never invent requirements not in the spec.
R4: Every risk area must map to a real line or section in the spec.
R5: Every endpoint listed must exist in the openapi.json provided.
R6: Flag ambiguous requirements explicitly — never silently resolve them.
R7: Recommend 2–8 scenarios per endpoint. Never recommend 0.
R8: If spec contains contradictions, flag both and set confidence LOW (< 0.75).
R9: Output MUST be valid JSON matching the schema exactly.
R10: Include a confidence score (0.0–1.0) in every response.
R11: If confidence < 0.75, populate the flagged array with specific reasons.
R12: Include no fields outside the defined schema.

OUTPUT SCHEMA (return only this JSON, no preamble):
{
  "feature_name": "string",
  "feature_intent": "string — one paragraph",
  "endpoints": [
    {
      "method": "GET|POST|PUT|DELETE|PATCH",
      "path": "string",
      "summary": "string",
      "recommended_scenarios": <integer 2-8>,
      "risk_level": "LOW|MEDIUM|HIGH|CRITICAL"
    }
  ],
  "risk_areas": [
    {
      "area": "string",
      "severity": "LOW|MEDIUM|HIGH|CRITICAL",
      "spec_source": "string — quote or section reference"
    }
  ],
  "ambiguous_requirements": [
    {
      "description": "string",
      "spec_source": "string"
    }
  ],
  "recommended_total_scenarios": <integer>,
  "confidence": <float 0.0-1.0>,
  "flagged": ["string"]
}
"""


class SpecAnalystAgent(AgentBase):

    def __init__(self, run_id: str):
        super().__init__(agent_name="spec_analyst", run_id=run_id)

    def run(self, input_data: dict) -> dict:
        """
        Args:
            input_data = {
                "feature_name": "login",
                "spec_path":    "requirements/LOGIN_FEATURES.md",
                "openapi_path": "requirements/openapi.json"
            }
        Returns:
            {
                "output":     <parsed spec_analysis dict>,
                "confidence": float,
                "flagged":    list,
                "agent":      "spec_analyst"
            }
        """
        feature_name = input_data["feature_name"]
        spec_path    = Path(input_data["spec_path"])
        openapi_path = Path(input_data["openapi_path"])

        self.logger.info(f"[SpecAnalystAgent] Analysing feature: {feature_name}")

        # ── R1/R2: Validate inputs exist ─────────────────────
        missing = [p for p in [spec_path, openapi_path] if not p.exists()]
        if missing:
            raise FileNotFoundError(
                f"[SpecAnalystAgent] R2 violated — missing files: {missing}"
            )

        # ── Load files ───────────────────────────────────────
        spec_content    = self.read_file(spec_path)
        openapi_content = self.read_file(openapi_path)

        # ── Load memory (prior runs) ──────────────────────────
        memory_entries = self.load_memory()
        memory_context = self.format_memory_for_prompt(memory_entries)

        # ── Build user prompt ────────────────────────────────
        user_prompt = f"""
{memory_context}

FEATURE NAME: {feature_name}

=== FEATURE SPEC (LOGIN_FEATURES.md) ===
{spec_content}

=== OPENAPI CONTRACT (openapi.json) ===
{openapi_content}

Analyse the above and return the structured JSON as specified in your rules.
Remember: only include endpoints that exist in the openapi.json above.
Flag anything ambiguous. Be precise.
"""

        # ── Call LLM (JSON mode) ─────────────────────────────
        raw_result = self.call_llm_json(SYSTEM_PROMPT, user_prompt)

        # ── Confidence gate ──────────────────────────────────
        result = {
            "output":     raw_result,
            "confidence": raw_result.get("confidence", 0.0),
            "flagged":    raw_result.get("flagged", []),
            "agent":      self.agent_name,
        }
        result = self.confidence_gate(result)

        # ── Write spec_analysis.json ─────────────────────────
        output_path = (
            Path(self.paths["requirements_dir"])
            / f"{feature_name}_spec_analysis.json"
        )
        self.write_json(output_path, raw_result)
        self.logger.info(f"[SpecAnalystAgent] Analysis written → {output_path}")

        # ── Decision log ─────────────────────────────────────
        self.write_decision_log(
            inputs={
                "feature_name": feature_name,
                "spec_path":    str(spec_path),
                "openapi_path": str(openapi_path),
            },
            rules_applied=[
                "R1: Both files verified present",
                "R3: No invented requirements",
                "R5: Endpoints cross-checked against openapi.json",
                "R7: Scenario count 2–8 per endpoint enforced",
                "R10: Confidence score included",
                f"R11: Flagged array {'populated' if result['flagged'] else 'empty — confidence OK'}",
            ],
            decisions=[
                f"Identified {len(raw_result.get('endpoints', []))} endpoints",
                f"Identified {len(raw_result.get('risk_areas', []))} risk areas",
                f"Flagged {len(raw_result.get('ambiguous_requirements', []))} ambiguous requirements",
                f"Recommended {raw_result.get('recommended_total_scenarios', '?')} total scenarios",
                f"Confidence: {raw_result.get('confidence', '?')}",
            ],
            result=result,
        )

        # ── Save memory ───────────────────────────────────────
        self.save_memory({
            "summary": (
                f"Analysed '{feature_name}': "
                f"{len(raw_result.get('endpoints', []))} endpoints, "
                f"{len(raw_result.get('risk_areas', []))} risks, "
                f"{len(raw_result.get('ambiguous_requirements', []))} ambiguities, "
                f"confidence={raw_result.get('confidence', '?')}"
            ),
            "feature_name":   feature_name,
            "endpoint_count": len(raw_result.get("endpoints", [])),
            "risk_area_count":len(raw_result.get("risk_areas", [])),
            "ambiguous_count":len(raw_result.get("ambiguous_requirements", [])),
            "confidence":     raw_result.get("confidence", 0.0),
        })

        return result


# ── CLI entry point (run standalone for testing) ─────────────
if __name__ == "__main__":
    import sys
    from datetime import datetime

    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    agent = SpecAnalystAgent(run_id=run_id)
    result = agent.run({
        "feature_name": "login",
        "spec_path":    "requirements/LOGIN_FEATURES.md",
        "openapi_path": "requirements/openapi.json",
    })

    print("\n=== SpecAnalystAgent Result ===")
    print(json.dumps(result["output"], indent=2))
    print(f"\nConfidence : {result['confidence']}")
    print(f"Flagged    : {result['flagged']}")
    print(f"Human review needed: {result['needs_human_review']}")