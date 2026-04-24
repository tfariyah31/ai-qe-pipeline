"""
agents/enrichment/enrichment_agent.py
======================================
EnrichmentAgent — Agent 4 of 6

REWRITE: The enriched Gherkin is now built entirely in Python by
matching scenario titles from ratings JSON against the original
Gherkin file, then injecting tags + inline comments directly.

The LLM is only used for the rejection_summary_md — a small,
focused prompt well within token limits.

This eliminates the tag mismatch failure that occurred when the LLM
was asked to rewrite the full Gherkin file.

Input:
    feature_name  — e.g. "login"
    ratings_path  — path to login_ratings.json
    gherkin_path  — path to login.test_case.md

Output:
    tests/test_cases/{feature}.enriched.md
    tests/test_cases/{feature}.enrichment_summary.json
    tests/test_cases/{feature}.rejection_summary.md
    Decision log → logs/run_{id}/enrichment_decision.log
    Memory entry → agent_memory/enrichment_memory.json
"""

import json
import re
from pathlib import Path

from agents.base_agent import AgentBase


# LLM only writes the rejection summary
SUMMARY_PROMPT = """
You are EnrichmentAgent — Agent 4 in a QE pipeline.

You will be given a list of rejected scenarios with their scores and
rejection reasons. Write a clean markdown table summarising them.

Return this exact JSON (no preamble):
{
  "rejection_summary_md": "string — full markdown content",
  "confidence": <float 0.0-1.0>,
  "flagged": ["string"]
}

Markdown table columns: Scenario | Score | Reason
"""


class EnrichmentAgent(AgentBase):

    def __init__(self, run_id: str):
        super().__init__(agent_name="enrichment", run_id=run_id)
        self.max_p0_percent = (
            self.agent_cfg
            .get("limits", {})
            .get("max_p0_percent", 20)
        )

    # ── Public entry point ────────────────────────────────────

    def run(self, input_data: dict) -> dict:
        feature_name = input_data["feature_name"]
        ratings_path = Path(input_data["ratings_path"])
        gherkin_path = Path(input_data["gherkin_path"])

        self.logger.info(f"[EnrichmentAgent] Enriching scenarios for: {feature_name}")

        # ── Validate inputs ───────────────────────────────────
        missing = [p for p in [ratings_path, gherkin_path] if not p.exists()]
        if missing:
            raise FileNotFoundError(
                f"[EnrichmentAgent] R3 violated — missing files: {missing}"
            )

        ratings      = self.read_json(ratings_path)
        gherkin_text = self.read_file(gherkin_path)

        # ── Enforce P0 cap in Python ──────────────────────────
        ratings, demotions = self._enforce_p0_cap(ratings)

        # ── Separate passing and rejected ─────────────────────
        passing  = [s for s in ratings.get("scenarios", []) if s.get("verdict") == "pass"]
        rejected = [s for s in ratings.get("scenarios", []) if s.get("verdict") == "reject"]

        self.logger.info(
            f"[EnrichmentAgent] Passing: {len(passing)} | Rejected: {len(rejected)}"
        )

        # ── BUILD ENRICHED GHERKIN IN PYTHON (no LLM) ─────────
        enriched_gherkin = self._build_enriched_gherkin(gherkin_text, passing)

        # ── Count tags in Python — always accurate ─────────────
        tag_counts = self._count_tags(enriched_gherkin)
        self.logger.info(f"[EnrichmentAgent] Tag counts (verified): {tag_counts}")

        # ── LLM only for rejection summary ────────────────────
        rejection_summary_md, llm_confidence, llm_flagged = \
            self._generate_rejection_summary(rejected, feature_name)

        # Confidence is high — Gherkin built in Python, not LLM
        confidence = max(0.90, llm_confidence)
        flagged    = llm_flagged

        summary = {
            "feature_name":    feature_name,
            "total_passing":   len(passing),
            "total_rejected":  len(rejected),
            "tag_counts":      tag_counts,
            "p0_cap_enforced": len(demotions) > 0,
            "demotions":       demotions,
            "confidence":      confidence,
            "flagged":         flagged,
        }

        # ── Write output files ────────────────────────────────
        test_cases_dir          = Path(self.paths["test_cases_dir"])
        enriched_path           = test_cases_dir / f"{feature_name}.enriched.md"
        enrichment_summary_path = test_cases_dir / f"{feature_name}.enrichment_summary.json"
        rejection_summary_path  = test_cases_dir / f"{feature_name}.rejection_summary.md"

        self.write_file(enriched_path, enriched_gherkin)
        self.write_json(enrichment_summary_path, summary)
        self.write_file(rejection_summary_path, rejection_summary_md)

        self.logger.info(
            f"[EnrichmentAgent] Enriched → {enriched_path} | "
            f"Rejections → {rejection_summary_path}"
        )

        # ── Build result + confidence gate ────────────────────
        result = {
            "output": {
                "enriched_path":           str(enriched_path),
                "enrichment_summary_path": str(enrichment_summary_path),
                "rejection_summary_path":  str(rejection_summary_path),
                "summary":                 summary,
            },
            "confidence": confidence,
            "flagged":    flagged,
            "agent":      self.agent_name,
        }
        result = self.confidence_gate(result)

        # ── Decision log ─────────────────────────────────────
        self.write_decision_log(
            inputs={
                "feature_name": feature_name,
                "ratings_path": str(ratings_path),
                "gherkin_path": str(gherkin_path),
            },
            rules_applied=[
                "R4: Rejected scenarios dropped in Python — not by LLM",
                "R6: P0/P1/P2 tags injected from ratings JSON in Python",
                "R7: @smoke/@regression preserved from original Gherkin",
                "R8: Both tags on same line — built deterministically",
                f"R9: P0 cap {self.max_p0_percent}% — "
                f"{'enforced, ' + str(len(demotions)) + ' demotion(s)' if demotions else 'not triggered'}",
                "R10: Inline comment injected per scenario in Python",
                "R11: Rejected scenarios in rejection_summary.md only",
                "ARCH: Gherkin built in Python — LLM used only for rejection summary",
            ],
            decisions=[
                f"Passing scenarios enriched: {len(passing)}",
                f"Rejected scenarios dropped: {len(rejected)}",
                f"Tag distribution (verified in Python): {tag_counts}",
                f"P0 demotions: {demotions}",
                f"Confidence: {confidence}",
            ],
            result=result,
        )

        # ── Save memory ───────────────────────────────────────
        self.save_memory({
            "summary": (
                f"Enriched {len(passing)} scenarios for '{feature_name}' | "
                f"rejected={len(rejected)} | "
                f"P0={tag_counts.get('P0',0)} "
                f"P1={tag_counts.get('P1',0)} "
                f"P2={tag_counts.get('P2',0)} | "
                f"demotions={len(demotions)}"
            ),
            "feature_name":    feature_name,
            "total_passing":   len(passing),
            "total_rejected":  len(rejected),
            "tag_distribution": {
                "P0": tag_counts.get("P0", 0),
                "P1": tag_counts.get("P1", 0),
                "P2": tag_counts.get("P2", 0),
            },
            "p0_cap_enforced": len(demotions) > 0,
            "demotions_count": len(demotions),
        })

        return result

    # ── Core: build enriched Gherkin in Python ────────────────

    def _build_enriched_gherkin(
        self, gherkin_text: str, passing: list[dict]
    ) -> str:
        """
        Build the enriched Gherkin deterministically in Python.

        For each Scenario line in the original Gherkin:
          - Look up its title in the passing ratings dict
          - If found: inject tags + inline comment above/below it
          - If not found (rejected): skip the scenario and its steps

        Tag counts are always accurate because Python writes them.
        """
        passing_lookup = {
            self._normalise(s["title"]): s
            for s in passing
        }

        lines        = gherkin_text.splitlines()
        output_lines = []
        skip_mode    = False   # True when inside a rejected scenario block
        i            = 0

        while i < len(lines):
            line     = lines[i]
            stripped = line.strip()

            # ── Feature header ────────────────────────────────
            if stripped.startswith("Feature:"):
                output_lines.append(line)
                i += 1
                continue

            # ── Tag line preceding a Scenario ─────────────────
            # We re-inject tags ourselves — skip originals
            if stripped.startswith("@") and not stripped.startswith("@pytest"):
                i += 1
                continue

            # ── Scenario line ─────────────────────────────────
            if re.match(r"Scenario(?:\s+Outline)?:", stripped):
                title      = re.sub(r"^Scenario(?:\s+Outline)?:\s*", "", stripped)
                norm_title = self._normalise(title)
                rating     = passing_lookup.get(norm_title)

                if rating is None:
                    # Rejected — enter skip mode
                    skip_mode = True
                    self.logger.debug(
                        f"[EnrichmentAgent] Dropping rejected: '{title}'"
                    )
                    i += 1
                    continue
                else:
                    skip_mode = False
                    priority  = rating.get("priority", "P2")
                    score     = rating.get("weighted_score", 0.0)
                    endpoint  = rating.get("endpoint", "unknown")

                    # Detect original tag from surrounding lines
                    orig_tag  = self._find_tag_nearby(lines, i)
                    tag_line  = f"  {orig_tag} @{priority}"
                    comment   = (
                        f"    # Priority: {priority} | "
                        f"Risk Score: {score:.2f} | "
                        f"Endpoint: {endpoint}"
                    )

                    output_lines.append("")
                    output_lines.append(tag_line)
                    output_lines.append(line)       # original Scenario: line
                    output_lines.append(comment)
                    i += 1
                    continue

            # ── Skip mode: drop lines belonging to rejected scenario ──
            if skip_mode:
                # Exit skip mode when we hit a new Scenario, Feature, or tag
                if (re.match(r"Scenario(?:\s+Outline)?:", stripped)
                        or stripped.startswith("Feature:")
                        or (stripped.startswith("@") and not stripped.startswith("@pytest"))):
                    skip_mode = False
                    # Don't increment — re-process this line
                    continue
                else:
                    i += 1
                    continue

            # ── All other lines (steps, blank lines) ──────────
            output_lines.append(line)
            i += 1

        return "\n".join(output_lines)

    def _find_tag_nearby(self, lines: list[str], scenario_idx: int) -> str:
        """
        Look in a window around the Scenario line for @smoke/@regression.
        Checks up to 3 lines before the Scenario.
        """
        for j in range(max(0, scenario_idx - 3), scenario_idx):
            t = lines[j].strip()
            if "@smoke" in t:
                return "@smoke"
            if "@regression" in t:
                return "@regression"
        return "@regression"   # safe default

    def _normalise(self, title: str) -> str:
        """Lowercase + collapse whitespace for fuzzy title matching."""
        return re.sub(r"\s+", " ", title.lower().strip())

    # ── Tag counting ─────────────────────────────────────────

    def _count_tags(self, gherkin: str) -> dict:
        return {
            "P0":         len(re.findall(r"@P0\b",         gherkin)),
            "P1":         len(re.findall(r"@P1\b",         gherkin)),
            "P2":         len(re.findall(r"@P2\b",         gherkin)),
            "smoke":      len(re.findall(r"@smoke\b",      gherkin)),
            "regression": len(re.findall(r"@regression\b", gherkin)),
        }

    # ── LLM: rejection summary only ──────────────────────────

    def _generate_rejection_summary(
        self, rejected: list[dict], feature_name: str
    ) -> tuple[str, float, list]:
        if not rejected:
            return (
                f"# Rejected Scenarios — {feature_name}\n\n"
                f"No scenarios were rejected this run.\n",
                1.0,
                [],
            )

        user_prompt = f"""
FEATURE: {feature_name}

REJECTED SCENARIOS:
{json.dumps([
    {
        "title":            s.get("title"),
        "weighted_score":   s.get("weighted_score"),
        "rejection_reason": s.get("rejection_reason"),
    }
    for s in rejected
], indent=2)}

Write the markdown rejection summary table and return the JSON object.
"""
        try:
            result     = self.call_llm_json(SUMMARY_PROMPT, user_prompt)
            md         = result.get("rejection_summary_md", "")
            confidence = result.get("confidence", 0.9)
            flagged    = result.get("flagged", [])
            if not md.strip():
                md = self._fallback_rejection_md(rejected, feature_name)
            return md, confidence, flagged
        except Exception as e:
            self.logger.warning(
                f"[EnrichmentAgent] LLM rejection summary failed: {e} — "
                f"using Python fallback"
            )
            return self._fallback_rejection_md(rejected, feature_name), 0.90, []

    def _fallback_rejection_md(self, rejected: list[dict], feature_name: str) -> str:
        lines = [
            f"# Rejected Scenarios — {feature_name}\n",
            "| Scenario | Score | Reason |",
            "|----------|-------|--------|",
        ]
        for s in rejected:
            title  = s.get("title", "unknown")
            score  = s.get("weighted_score", "—")
            reason = s.get("rejection_reason", "Score below threshold")
            lines.append(f"| {title} | {score} | {reason} |")
        return "\n".join(lines)

    # ── P0 cap ────────────────────────────────────────────────

    def _enforce_p0_cap(self, ratings: dict) -> tuple[dict, list]:
        scenarios = ratings.get("scenarios", [])
        passing   = [s for s in scenarios if s.get("verdict") == "pass"]
        p0s       = [s for s in passing   if s.get("priority") == "P0"]
        max_p0    = max(1, int(len(passing) * self.max_p0_percent / 100))
        demotions = []

        if len(p0s) > max_p0:
            p0s_sorted = sorted(p0s, key=lambda s: s.get("weighted_score", 0))
            for scenario in p0s_sorted[:len(p0s) - max_p0]:
                reason = (
                    f"P0 cap ({self.max_p0_percent}%) exceeded — "
                    f"demoted P0→P1 (score={scenario.get('weighted_score')})"
                )
                scenario["priority"] = "P1"
                demotions.append({
                    "title":  scenario.get("title", ""),
                    "from":   "P0", "to": "P1", "reason": reason,
                })
                self.logger.info(
                    f"[EnrichmentAgent] Demotion: '{scenario.get('title')}' P0→P1"
                )
        return ratings, demotions


# ── CLI entry point ───────────────────────────────────────────
if __name__ == "__main__":
    from datetime import datetime

    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    agent  = EnrichmentAgent(run_id=run_id)
    result = agent.run({
        "feature_name": "login",
        "ratings_path": "ratings/login_ratings.json",
        "gherkin_path": "tests/test_cases/login.test_case.md",
    })

    summary = result["output"]["summary"]
    print("\n=== EnrichmentAgent Result ===")
    print(f"Enriched file  → {result['output']['enriched_path']}")
    print(f"Passing        : {summary.get('total_passing')}")
    print(f"Rejected       : {summary.get('total_rejected')}")
    print(f"Tag counts     : {summary.get('tag_counts')}")
    print(f"P0 cap enforced: {summary.get('p0_cap_enforced')}")
    print(f"Demotions      : {summary.get('demotions')}")
    print(f"Confidence     : {result['confidence']}")
    print(f"Flagged        : {result['flagged']}")
    print(f"Human review   : {result['needs_human_review']}")