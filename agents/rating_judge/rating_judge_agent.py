"""
agents/rating_judge/rating_judge_agent.py
==========================================
RatingJudgeAgent — Agent 3 of 6

Fully autonomous scorer. Reads the Gherkin manifest and spec analysis,
scores every scenario using the exact weighted formula, applies quality
gates, and writes ratings to ratings/{feature}_ratings.json.

Low-confidence scores are escalated to human_review_queue.json.
Human override scores in rating_overrides.json are applied before scoring.
The pipeline is never paused — escalation is asynchronous.

Input:
    feature_name       — e.g. "login"
    manifest_path      — path to login.manifest.json
    spec_analysis_path — path to login_spec_analysis.json

Output:
    ratings/{feature}_ratings.json
    Decision log → logs/run_{id}/rating_judge_decision.log
    Memory entry → agent_memory/rating_judge_memory.json
"""

import json
from pathlib import Path

from agents.base_agent import AgentBase


# ── Per-scenario scoring prompt ─────────────────────────────
# One LLM call per scenario — avoids token truncation on large suites.
# The weighted formula is always recalculated in Python after the call.
SCENARIO_SCORE_PROMPT = """
You are RatingJudgeAgent. Score ONE Gherkin scenario using a weighted risk formula.

DIMENSIONS (score each 1.0–5.0):
- business_impact:       Does failure here break the business? (1=cosmetic, 5=auth/revenue down)
- frequency_of_use:      How often do real users hit this flow? (1=rare, 5=every session)
- failure_probability:   How likely is this to break? (1=very stable, 5=complex/changes often)
- dependency_impact:     How many features break if this fails? (1=isolated, 5=cascades everywhere)
- assertion_specificity: How precise are the Then steps? (1=vague, 5=exact status+field+value checked)

RULES:
R6: All scores must be 1.0–5.0. No scores outside this range.
R8: Write ONE sentence justification per dimension. Cite the scenario text — no vague phrases.
R9: If assertion_specificity < 2.0, set vague_assertion to true.

OUTPUT — return ONLY this JSON (no preamble):
{
  "title": "string",
  "endpoint": "string",
  "scores": {
    "business_impact":       <float 1.0-5.0>,
    "frequency_of_use":      <float 1.0-5.0>,
    "failure_probability":   <float 1.0-5.0>,
    "dependency_impact":     <float 1.0-5.0>,
    "assertion_specificity": <float 1.0-5.0>
  },
  "justifications": {
    "business_impact":       "string",
    "frequency_of_use":      "string",
    "failure_probability":   "string",
    "dependency_impact":     "string",
    "assertion_specificity": "string"
  },
  "vague_assertion": <boolean>,
  "confidence": <float 0.0-1.0>
}
"""


class RatingJudgeAgent(AgentBase):

    WEIGHTS = {
        "business_impact":       1.5,
        "frequency_of_use":      1.2,
        "failure_probability":   1.3,
        "dependency_impact":     1.0,
        "assertion_specificity": 0.5,
    }
    WEIGHT_SUM = sum(WEIGHTS.values())   # 5.5

    def __init__(self, run_id: str):
        super().__init__(agent_name="rating_judge", run_id=run_id)
        self.escalation_cfg = self.agent_cfg.get("escalation", {})
        self.override_path  = Path(
            self.escalation_cfg.get(
                "override_path", "human_review/rating_overrides.json"
            )
        )

    # ── Public entry point ────────────────────────────────────

    def run(self, input_data: dict) -> dict:
        """
        Args:
            input_data = {
                "feature_name":       "login",
                "manifest_path":      "tests/test_cases/login.manifest.json",
                "spec_analysis_path": "requirements/login_spec_analysis.json"
            }
        Returns:
            {
                "output":     { "ratings_path": str, "ratings": dict },
                "confidence": float,
                "flagged":    list,
                "agent":      "rating_judge"
            }
        """
        feature_name       = input_data["feature_name"]
        manifest_path      = Path(input_data["manifest_path"])
        spec_analysis_path = Path(input_data["spec_analysis_path"])

        self.logger.info(f"[RatingJudgeAgent] Scoring scenarios for: {feature_name}")

        # ── R1/R2/R3: Validate inputs ─────────────────────────
        missing = [p for p in [manifest_path, spec_analysis_path] if not p.exists()]
        if missing:
            raise FileNotFoundError(
                f"[RatingJudgeAgent] R3 violated — missing files: {missing}"
            )

        manifest      = self.read_json(manifest_path)
        spec_analysis = self.read_json(spec_analysis_path)

        # ── R4: Load human overrides ──────────────────────────
        overrides = self._load_overrides()

        # ── Memory + drift ────────────────────────────────────
        memory_entries = self.load_memory()
        drift_warning  = self._detect_score_drift(memory_entries)

        # ── Build compact risk context (not full spec dump) ───
        risk_context = self._build_risk_context(spec_analysis, drift_warning)

        # ── Read steps from Gherkin file directly ─────────────
        # The manifest has no steps field — we parse them from
        # the test_case.md so RatingJudge can score assertions properly.
        gherkin_path = Path(
            input_data.get(
                "gherkin_path",
                f"tests/test_cases/{feature_name}.test_case.md"
            )
        )
        gherkin_steps = self._parse_gherkin_steps(gherkin_path)

        # ── Score each scenario with a separate LLM call ──────
        scenarios_input = manifest.get("scenarios", [])
        # Merge steps into scenario dicts from manifest
        for s in scenarios_input:
            title = s.get("title", "")
            if title in gherkin_steps:
                s["steps"] = gherkin_steps[title]
        self.logger.info(
            f"[RatingJudgeAgent] Scoring {len(scenarios_input)} scenarios individually"
        )

        scored_scenarios = []
        escalated        = []
        all_flagged      = []

        # Delay between scenario calls to stay within 12,000 TPM limit.
        # Each call ~1000 tokens. At 12,000 TPM we get ~12 calls/min.
        # 6s between calls = 10 calls/min — safe buffer.
        per_scenario_delay = 6   # seconds

        for idx, scenario in enumerate(scenarios_input):
            if idx > 0:
                self.logger.info(
                    f"[RatingJudgeAgent] Waiting {per_scenario_delay}s "
                    f"(TPM cooldown between scenarios)..."
                )
                import time
                time.sleep(per_scenario_delay)

            title    = scenario.get("title", "")
            endpoint = scenario.get("endpoint", "unknown")

            # Check for human override first
            if title in overrides:
                override = overrides[title]
                scores   = override["scores"]
                ws       = self._apply_formula(scores)
                verdict, priority = self._verdict_and_priority(ws)
                scored_scenarios.append({
                    "title":          title,
                    "endpoint":       endpoint,
                    "human_override": True,
                    "scores":         scores,
                    "justifications": {d: "Human override applied" for d in scores},
                    "weighted_score": ws,
                    "verdict":        verdict,
                    "priority":       priority,
                    "rejection_reason": None if verdict == "pass" else f"Score {ws:.2f} < 3.0",
                    "vague_assertion": False,
                })
                self.logger.info(f"[RatingJudgeAgent] Override applied: {title}")
                continue

            scored = self._score_one_scenario(scenario, risk_context)
            if scored is None:
                all_flagged.append(f"Failed to score: {title} — skipped")
                continue

            # Recalculate formula in Python — never trust LLM arithmetic
            scores  = scored.get("scores", {})
            ws      = self._apply_formula(scores)
            verdict, priority = self._verdict_and_priority(ws)

            entry = {
                "title":           title,
                "endpoint":        endpoint,
                "human_override":  False,
                "scores":          scores,
                "justifications":  scored.get("justifications", {}),
                "weighted_score":  ws,
                "verdict":         verdict,
                "priority":        priority,
                "rejection_reason": None if verdict == "pass" else f"Score {ws:.2f} below 3.0 threshold",
                "vague_assertion": scored.get("vague_assertion", False),
            }

            # R9: Flag vague assertions
            if scored.get("vague_assertion") or scores.get("assertion_specificity", 5.0) < 2.0:
                escalated.append(title)
                all_flagged.append(
                    f"R9: '{title}' has vague assertion "
                    f"(specificity={scores.get('assertion_specificity')})"
                )

            scored_scenarios.append(entry)

        # ── Assemble ratings object ───────────────────────────
        pass_count   = sum(1 for s in scored_scenarios if s["verdict"] == "pass")
        reject_count = len(scored_scenarios) - pass_count
        pass_rate    = round(pass_count / len(scored_scenarios) * 100, 1) if scored_scenarios else 0

        # R10: Warn if pass rate > 80%
        if pass_rate > 80:
            all_flagged.append(
                f"R10 WARNING: Pass rate {pass_rate}% > 80% — review for leniency bias"
            )

        # Confidence: 0.85 base, reduced if escalations exist
        confidence = 0.85 if not escalated else 0.80

        raw_ratings = {
            "feature_name":               feature_name,
            "run_id":                     self.run_id,
            "total_scored":               len(scored_scenarios),
            "pass_count":                 pass_count,
            "reject_count":               reject_count,
            "pass_rate":                  pass_rate,
            "scenarios":                  scored_scenarios,
            "escalated_for_human_review": escalated,
            "confidence":                 confidence,
            "flagged":                    all_flagged,
        }

        # ── Write ratings JSON ────────────────────────────────
        ratings_dir  = Path(self.paths["ratings_dir"])
        ratings_path = ratings_dir / f"{feature_name}_ratings.json"
        self.write_json(ratings_path, raw_ratings)
        self.logger.info(f"[RatingJudgeAgent] Ratings written → {ratings_path}")

        # ── Build result + confidence gate ────────────────────
        confidence = raw_ratings.get("confidence", 0.0)
        flagged    = raw_ratings.get("flagged", [])

        result = {
            "output": {
                "ratings_path": str(ratings_path),
                "ratings":      raw_ratings,
            },
            "confidence": confidence,
            "flagged":    flagged,
            "agent":      self.agent_name,
        }
        result = self.confidence_gate(result)

        # ── Decision log ─────────────────────────────────────
        distribution = self._score_distribution(raw_ratings)
        self.write_decision_log(
            inputs={
                "feature_name":  feature_name,
                "manifest_path": str(manifest_path),
                "override_count":len(overrides),
            },
            rules_applied=[
                "R5: All scenarios scored",
                "R7: Weighted formula verified and recalculated in code",
                "R8: One-sentence justifications required per dimension",
                "R9: assertion_specificity < 2.0 flagged for human review",
                f"R10: Pass rate {raw_ratings.get('pass_rate', 0):.1f}% — {'OK' if raw_ratings.get('pass_rate', 0) <= 80 else 'WARNING: exceeds 80%'}",
                "R11: Score < 3.0 → reject enforced",
                "R12: Priority mapping applied",
                f"R4: {len(overrides)} human override(s) applied",
            ],
            decisions=[
                f"Scored {raw_ratings.get('total_scored', 0)} scenarios",
                f"Pass: {raw_ratings.get('pass_count', 0)} | Reject: {raw_ratings.get('reject_count', 0)}",
                f"Distribution: {distribution}",
                f"Escalated: {raw_ratings.get('escalated_for_human_review', [])}",
                f"Confidence: {confidence}",
            ],
            result=result,
        )

        # ── Save memory ───────────────────────────────────────
        scenarios    = raw_ratings.get("scenarios", [])
        avg_score    = (
            sum(s.get("weighted_score", 0) for s in scenarios) / len(scenarios)
            if scenarios else 0
        )
        self.save_memory({
            "summary": (
                f"Scored {raw_ratings.get('total_scored',0)} scenarios for '{feature_name}' | "
                f"pass_rate={raw_ratings.get('pass_rate',0):.1f}% | "
                f"avg_score={avg_score:.2f} | "
                f"confidence={confidence}"
            ),
            "feature_name":     feature_name,
            "pass_rate":        raw_ratings.get("pass_rate", 0),
            "avg_score":        round(avg_score, 2),
            "reject_count":     raw_ratings.get("reject_count", 0),
            "escalated_count":  len(raw_ratings.get("escalated_for_human_review", [])),
            "score_distribution": distribution,
        })

        return result

    # ── Helpers ───────────────────────────────────────────────


    def _parse_gherkin_steps(self, gherkin_path) -> dict:
        """
        Parse steps from the Gherkin test_case.md file.
        Returns dict: {scenario_title: [step_strings]}
        Used to populate steps in manifest scenarios for scoring.
        """
        import re
        result = {}
        if not gherkin_path.exists():
            self.logger.warning(
                f"[RatingJudgeAgent] Gherkin file not found: {gherkin_path}"
            )
            return result

        content    = self.read_file(gherkin_path)
        lines      = content.splitlines()
        i          = 0
        while i < len(lines):
            stripped = lines[i].strip()
            if re.match(r"Scenario(?:\s+Outline)?:", stripped):
                title = re.sub(r"^Scenario(?:\s+Outline)?:\s*", "", stripped)
                steps = []
                i += 1
                while i < len(lines):
                    ns = lines[i].strip()
                    if (ns.startswith("@")
                            or re.match(r"Scenario", ns)
                            or ns.startswith("Feature:")
                            or ns.startswith("# Priority:")):
                        break
                    if ns and not ns.startswith("#"):
                        steps.append(ns)
                    i += 1
                result[title] = steps
                continue
            i += 1
        self.logger.info(
            f"[RatingJudgeAgent] Parsed steps for {len(result)} scenarios from Gherkin"
        )
        return result

    def _build_risk_context(self, spec_analysis: dict, drift_warning: str) -> str:
        """
        Build a compact risk context string from spec analysis.
        Injects only the risk areas and ambiguities — not the full JSON.
        This keeps per-scenario prompts small and within TPM limits.
        """
        risk_areas = spec_analysis.get("risk_areas", [])
        ambiguous  = spec_analysis.get("ambiguous_requirements", [])

        lines = ["FEATURE RISK CONTEXT:"]
        for r in risk_areas[:5]:   # top 5 risks only
            lines.append("  RISK [" + r.get("severity","?") + "]: " + r.get("area",""))
        for a in ambiguous[:3]:    # top 3 ambiguities
            lines.append("  AMBIGUOUS: " + a.get("description",""))
        if drift_warning:
            lines.append(drift_warning)
        return "\n".join(lines)

    def _score_one_scenario(self, scenario: dict, risk_context: str) -> dict | None:
        """
        Score a single scenario with one focused LLM call.
        Returns the raw score dict or None on failure.
        """
        title    = scenario.get("title", "")
        endpoint = scenario.get("endpoint", "unknown")
        steps    = scenario.get("steps", [])
        steps_text = "\n".join("  " + s for s in steps) if steps else "  (no steps available)"

        user_prompt = (
            risk_context + "\n\n"
            "SCENARIO TO SCORE:\n"
            "Title   : " + title + "\n"
            "Endpoint: " + endpoint + "\n"
            "Steps:\n" + steps_text + "\n\n"
            "Score this scenario on all 5 dimensions. "
            "Write one justification sentence per dimension citing the steps above. "
            "Return the JSON object."
        )
        try:
            result = self.call_llm_json(SCENARIO_SCORE_PROMPT, user_prompt)
            result["title"]    = title
            result["endpoint"] = endpoint
            return result
        except Exception as e:
            self.logger.error(
                "[RatingJudgeAgent] Failed scoring '" + title + "': " + str(e)
            )
            return None

    def _load_overrides(self) -> dict:
        """Load human rating overrides. Returns dict keyed by scenario title."""
        if not self.override_path.exists():
            return {}
        try:
            data = self.read_json(self.override_path)
            # Expected format: [{"title": "...", "scores": {...}, "reason": "..."}]
            return {item["title"]: item for item in data}
        except Exception as e:
            self.logger.warning(f"[RatingJudgeAgent] Could not load overrides: {e}")
            return {}

    def _apply_formula(self, scores: dict) -> float:
        """Recalculate weighted score from raw dimension scores."""
        weighted_sum = sum(
            scores.get(dim, 0) * weight
            for dim, weight in self.WEIGHTS.items()
        )
        return round(weighted_sum / self.WEIGHT_SUM, 3)

    def _verdict_and_priority(self, weighted_score: float) -> tuple[str, str | None]:
        if weighted_score >= 4.5:
            return "pass", "P0"
        elif weighted_score >= 4.0:
            return "pass", "P1"
        elif weighted_score >= 3.0:
            return "pass", "P2"
        else:
            return "reject", None

    def _verify_and_recalculate(self, ratings: dict, overrides: dict) -> dict:
        """
        Recalculate weighted_score from raw scores in code (not trusting LLM math).
        Apply human overrides where present.
        Enforce verdict + priority from recalculated score.
        """
        escalated = []

        for scenario in ratings.get("scenarios", []):
            title = scenario.get("title", "")

            # Apply human override if present
            if title in overrides:
                override = overrides[title]
                scenario["scores"]          = override["scores"]
                scenario["human_override"]  = True
                self.logger.info(f"[RatingJudgeAgent] Override applied: {title}")
            else:
                scenario["human_override"] = False

            # Recalculate score in code — never trust LLM arithmetic
            scores = scenario.get("scores", {})
            recalculated = self._apply_formula(scores)
            scenario["weighted_score"] = recalculated

            # Enforce verdict + priority
            verdict, priority = self._verdict_and_priority(recalculated)
            scenario["verdict"]  = verdict
            scenario["priority"] = priority

            if verdict == "reject" and not scenario.get("rejection_reason"):
                scenario["rejection_reason"] = (
                    f"Weighted score {recalculated:.2f} below minimum threshold of 3.0"
                )

            # R9: Flag vague assertions
            if scores.get("assertion_specificity", 5.0) < 2.0:
                escalated.append(title)
                flagged = ratings.get("flagged", [])
                flagged.append(
                    f"R9: '{title}' has vague assertion (specificity={scores.get('assertion_specificity')})"
                )
                ratings["flagged"] = flagged

        # R19: Also escalate any scenario the LLM flagged
        llm_escalated = ratings.get("escalated_for_human_review", [])
        all_escalated = list(set(escalated + llm_escalated))
        ratings["escalated_for_human_review"] = all_escalated

        return ratings

    def _check_pass_rate(self, ratings: dict) -> dict:
        """R10: If pass rate > 80%, add a warning flag."""
        scenarios    = ratings.get("scenarios", [])
        total        = len(scenarios)
        pass_count   = sum(1 for s in scenarios if s.get("verdict") == "pass")
        reject_count = total - pass_count
        pass_rate    = round((pass_count / total * 100) if total else 0, 1)

        ratings["total_scored"] = total
        ratings["pass_count"]   = pass_count
        ratings["reject_count"] = reject_count
        ratings["pass_rate"]    = pass_rate

        if pass_rate > 80:
            flagged = ratings.get("flagged", [])
            flagged.append(
                f"R10 WARNING: Pass rate is {pass_rate}% — exceeds 80% threshold. "
                f"Review scores for leniency bias."
            )
            ratings["flagged"]    = flagged
            ratings["confidence"] = min(ratings.get("confidence", 1.0), 0.70)
            self.logger.warning(
                f"[RatingJudgeAgent] R10 triggered: pass rate {pass_rate}% > 80%"
            )

        return ratings

    def _score_distribution(self, ratings: dict) -> dict:
        dist = {"P0": 0, "P1": 0, "P2": 0, "reject": 0}
        for s in ratings.get("scenarios", []):
            p = s.get("priority") or "reject"
            if p in dist:
                dist[p] += 1
        return dist

    def _detect_score_drift(self, memory_entries: list) -> str:
        """
        Compare avg_score across last 3 runs and warn if drift > 0.5.
        Injects warning into prompt so LLM is aware of historical baseline.
        """
        recent = [
            e.get("avg_score", 0)
            for e in memory_entries[-3:]
            if "avg_score" in e
        ]
        if len(recent) < 2:
            return ""

        drift = max(recent) - min(recent)
        if drift > 0.5:
            return (
                f"\nSCORE DRIFT WARNING: Average scores across recent runs "
                f"varied by {drift:.2f} ({recent}). "
                f"Be consistent with your scoring baseline.\n"
            )
        return ""


# ── CLI entry point ───────────────────────────────────────────
if __name__ == "__main__":
    import sys
    from datetime import datetime

    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    agent = RatingJudgeAgent(run_id=run_id)
    result = agent.run({
        "feature_name":       "login",
        "manifest_path":      "tests/test_cases/login.manifest.json",
        "spec_analysis_path": "requirements/login_spec_analysis.json",
        "gherkin_path":       "tests/test_cases/login.test_case.md",
    })

    ratings = result["output"]["ratings"]
    print("\n=== RatingJudgeAgent Result ===")
    print(f"Total scored : {ratings.get('total_scored')}")
    print(f"Pass         : {ratings.get('pass_count')}  |  Reject: {ratings.get('reject_count')}")
    print(f"Pass rate    : {ratings.get('pass_rate')}%")
    print(f"Escalated    : {ratings.get('escalated_for_human_review')}")
    print(f"Confidence   : {result['confidence']}")
    print(f"Flagged      : {result['flagged']}")
    print(f"Human review : {result['needs_human_review']}")
    print(f"Ratings file : {result['output']['ratings_path']}")