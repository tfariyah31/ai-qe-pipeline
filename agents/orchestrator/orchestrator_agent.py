"""
==========================================
OrchestratorAgent — Agent 6 of 6

Runs all 5 pipeline agents in sequence. Reads confidence scores,
applies gate logic, retries on failure, halts on unrecoverable error,
and writes pipeline_summary.log.

Usage:
    python -m agents.orchestrator.orchestrator_agent --feature login

    Optional:
    --spec     path/to/LOGIN_FEATURES.md   (default: requirements/{feature}_FEATURES.md)
    --openapi  path/to/openapi.json        (default: requirements/openapi.json)
    --conftest path/to/conftest.py         (default: tests/conftest.py)
"""

import argparse
import json
import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path

import yaml

# ── Agent imports ─────────────────────────────────────────────
from agents.spec_analyst.spec_analyst_agent     import SpecAnalystAgent
from agents.gherkin_author.gherkin_author_agent import GherkinAuthorAgent
from agents.rating_judge.rating_judge_agent     import RatingJudgeAgent
from agents.enrichment.enrichment_agent         import EnrichmentAgent
from agents.script_forge.script_forge_agent     import ScriptForgeAgent

# ── Config ────────────────────────────────────────────────────
CONFIG_PATH = Path("agent_config.yaml")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("OrchestratorAgent")

try:
    from streamlit_app.pipeline_runner import _STOP_EVENT as _UI_STOP
except ImportError:
    _UI_STOP = None

def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


# ── Streamlit signal writer ───────────────────────────────────

def _write_agent_done_signal(
    agent_name: str,
    run_id: str,
    confidence: float = None,
    escalated: bool = False,
):
    """
    Write a small JSON signal file after each agent completes.
    The Streamlit watcher detects these to update agent cards in real time.
    Files are written to: logs/run_{run_id}/.signal_{agentname}
    No-ops silently if run_id is empty (CLI-only runs unaffected).
    """
    if not run_id:
        return
    try:
        signal_dir = Path(f"logs/run_{run_id}")
        signal_dir.mkdir(parents=True, exist_ok=True)
        signal_key  = agent_name.lower().replace("agent", "")
        signal_path = signal_dir / f".signal_{signal_key}"
        signal_path.write_text(
            json.dumps({
                "agent":      agent_name,
                "confidence": confidence,
                "escalated":  escalated,
                "timestamp":  datetime.utcnow().isoformat(),
            }),
            encoding="utf-8",
        )
    except Exception as e:
        # Never let signal writing crash the pipeline
        logger.debug(f"[Orchestrator] Signal write skipped: {e}")


# ── Pipeline runner ───────────────────────────────────────────

class OrchestratorAgent:

    def __init__(self, feature_name: str, spec_path: str,
                 openapi_path: str, conftest_path: str):
        self.feature_name  = feature_name
        self.spec_path     = spec_path
        self.openapi_path  = openapi_path
        self.conftest_path = conftest_path
        self.config        = load_config()
        self.started_at    = datetime.utcnow()

        # ── Pick up run_id from Streamlit env var if present,
        #    otherwise generate our own (CLI runs unchanged)
        env_run_id   = os.environ.get("PIPELINE_RUN_ID", "").strip()
        self.run_id  = env_run_id if env_run_id else self.started_at.strftime("%Y%m%d_%H%M%S")

        self.paths   = self.config["paths"]

        # Pipeline state
        self.agent_results: list[dict] = []
        self.errors:        list[str]  = []
        self.final_status              = "SUCCESS"

        logger.info(
            f"[Orchestrator] Pipeline starting | "
            f"feature={feature_name} | run_id={self.run_id}"
        )

    # ── Main pipeline ─────────────────────────────────────────

    def run(self) -> bool:
        """
        Execute the full pipeline. Returns True on success, False on failure.
        """
        feature = self.feature_name

        # ── Derive paths that agents pass to each other ───────
        spec_analysis_path = f"requirements/{feature}_spec_analysis.json"
        gherkin_path       = f"tests/test_cases/{feature}.test_case.md"
        manifest_path      = f"tests/test_cases/{feature}.manifest.json"
        ratings_path       = f"ratings/{feature}_ratings.json"
        enriched_path      = f"tests/test_cases/{feature}.enriched.md"

        # ── Define pipeline steps ─────────────────────────────
        steps = [
            (
                SpecAnalystAgent,
                {
                    "feature_name": feature,
                    "spec_path":    self.spec_path,
                    "openapi_path": self.openapi_path,
                },
                [spec_analysis_path],
            ),
            (
                GherkinAuthorAgent,
                {
                    "feature_name":       feature,
                    "spec_analysis_path": spec_analysis_path,
                    "spec_path":          self.spec_path,
                },
                [gherkin_path, manifest_path],
            ),
            (
                RatingJudgeAgent,
                {
                    "feature_name":       feature,
                    "manifest_path":      manifest_path,
                    "spec_analysis_path": spec_analysis_path,
                    "gherkin_path":       gherkin_path,
                },
                [ratings_path],
            ),
            (
                EnrichmentAgent,
                {
                    "feature_name": feature,
                    "ratings_path": ratings_path,
                    "gherkin_path": gherkin_path,
                },
                [enriched_path],
            ),
            (
                ScriptForgeAgent,
                {
                    "feature_name":  feature,
                    "enriched_path": enriched_path,
                    "openapi_path":  self.openapi_path,
                    "conftest_path": self.conftest_path,
                },
                [f"tests/api/test_{feature}_api.py"],
            ),
        ]

        # ── Between-agent delay (TPM cooldown) ─────────────────
        delay = (
            self.config
            .get("rate_limits", {})
            .get("between_agents_delay_sec", 15)
        )

        # ── Execute each step ─────────────────────────────────
        for i, (AgentClass, input_data, output_files) in enumerate(steps):
            if i > 0:
                logger.info(
                    f"[Orchestrator] Waiting {delay}s between agents "
                    f"(TPM cooldown)..."
                )
                time.sleep(delay)
                
            if _UI_STOP and _UI_STOP.is_set():
                logger.warning("[Orchestrator] Stop requested by UI — halting pipeline")
                self.final_status = "STOPPED"
                break

            success = self._run_step(AgentClass, input_data, output_files)
            if not success:
                self.final_status = "FAILED"
                logger.error(
                    f"[Orchestrator] Pipeline HALTED at {AgentClass.__name__}"
                )
                break

        # ── Signal OrchestratorAgent itself as done ───────────
        _write_agent_done_signal(
            agent_name = "OrchestratorAgent",
            run_id     = self.run_id,
            confidence = 1.0,
            escalated  = False,
        )

        # ── Write summary + terminal output ───────────────────
        self._write_pipeline_summary()
        self._print_terminal_summary()

        return self.final_status == "SUCCESS"

    # ── Step runner with retry ────────────────────────────────

    def _run_step(
        self,
        AgentClass,
        input_data: dict,
        output_files: list[str],
    ) -> bool:
        """
        Run a single agent step with retry logic.
        Returns True if step succeeded, False if all retries exhausted.
        """
        agent_name  = AgentClass.__name__
        agent_cfg   = self.config["agents"].get(
            agent_name.lower().replace("agent", ""), {}
        )
        max_retries = agent_cfg.get("max_retries", 2)
        threshold   = agent_cfg.get("confidence_threshold", 0.75)

        attempt     = 0
        step_start  = time.time()
        last_result = None
        last_error  = None

        while attempt <= max_retries:
            if attempt > 0:
                wait = 2 ** attempt
                logger.warning(
                    f"[Orchestrator] Retrying {agent_name} "
                    f"(attempt {attempt + 1}/{max_retries + 1}) in {wait}s..."
                )
                time.sleep(wait)

            try:
                agent       = AgentClass(run_id=self.run_id)
                last_result = agent.run(input_data)
                confidence  = last_result.get("confidence", 0.0)
                escalated   = last_result.get("needs_human_review", False)

                # ── R4/R5: Check confidence gate ──────────────
                if confidence >= threshold:
                    duration = round(time.time() - step_start, 2)
                    self._record_agent_result(
                        agent_name, "completed", last_result,
                        output_files, duration
                    )

                    # ── R3: Verify output files exist ──────────
                    missing = [f for f in output_files if not Path(f).exists()]
                    if missing:
                        raise FileNotFoundError(
                            f"R3: {agent_name} reported success but "
                            f"output files missing: {missing}"
                        )

                    logger.info(
                        f"[Orchestrator] ✓ {agent_name} | "
                        f"confidence={confidence:.2f} | "
                        f"duration={duration}s"
                    )

                    # ── R8: Log human review without halting ───
                    if escalated:
                        logger.warning(
                            f"[Orchestrator] ⚠ {agent_name} flagged for "
                            f"human review — pipeline continues"
                        )

                    # ── Write Streamlit signal ─────────────────
                    _write_agent_done_signal(
                        agent_name = agent_name,
                        run_id     = self.run_id,
                        confidence = confidence,
                        escalated  = escalated,
                    )

                    return True

                else:
                    logger.warning(
                        f"[Orchestrator] {agent_name} confidence {confidence:.2f} "
                        f"< threshold {threshold:.2f} — retrying"
                    )
                    attempt += 1
                    continue

            except Exception as e:
                last_error = str(e)
                logger.error(f"[Orchestrator] {agent_name} exception: {e}")
                attempt += 1
                continue

        # ── All retries exhausted — R7: HALT ─────────────────
        error_msg = (
            f"{agent_name} failed after {max_retries + 1} attempts. "
            f"Last error: {last_error or 'confidence below threshold'}"
        )
        self.errors.append(error_msg)
        duration = round(time.time() - step_start, 2)

        self._record_agent_result(
            agent_name, "failed",
            last_result or {"confidence": 0.0, "flagged": [], "needs_human_review": False},
            output_files, duration
        )

        # ── Signal failure so Streamlit card turns red ────────
        _write_agent_done_signal(
            agent_name = agent_name,
            run_id     = self.run_id,
            confidence = last_result.get("confidence", 0.0) if last_result else 0.0,
            escalated  = True,
        )

        logger.error(f"[Orchestrator] ✗ {agent_name} FAILED — {error_msg}")
        return False

    # ── Recording + logging ───────────────────────────────────

    def _record_agent_result(
        self,
        agent_name:   str,
        status:       str,
        result:       dict,
        output_files: list[str],
        duration:     float,
    ):
        self.agent_results.append({
            "name":               agent_name,
            "status":             status,
            "confidence":         result.get("confidence", 0.0),
            "needs_human_review": result.get("needs_human_review", False),
            "flagged":            result.get("flagged", []),
            "duration_sec":       duration,
            "output_files":       output_files,
        })

    def _write_pipeline_summary(self):
        """R12/R13: Write pipeline_summary.log."""
        ended_at     = datetime.utcnow()
        duration_sec = round(
            (ended_at - self.started_at).total_seconds(), 2
        )

        review_queue_path = Path(
            self.config["agents"]["rating_judge"]
            .get("escalation", {})
            .get("queue_path", "human_review/human_review_queue.json")
        )
        human_review_items = 0
        if review_queue_path.exists():
            try:
                queue = json.loads(review_queue_path.read_text())
                human_review_items = sum(
                    1 for item in queue
                    if item.get("run_id") == self.run_id
                )
            except Exception:
                pass

        summary = {
            "run_id":             self.run_id,
            "feature_name":       self.feature_name,
            "started_at":         self.started_at.isoformat(),
            "ended_at":           ended_at.isoformat(),
            "duration_sec":       duration_sec,
            "final_status":       self.final_status,
            "agents":             self.agent_results,
            "human_review_items": human_review_items,
            "human_review_path":  str(review_queue_path),
            "errors":             self.errors,
        }

        log_dir      = Path(self.paths["logs_dir"]) / f"run_{self.run_id}"
        log_dir.mkdir(parents=True, exist_ok=True)
        summary_path = log_dir / "pipeline_summary.log"

        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

        logger.info(f"[Orchestrator] Pipeline summary → {summary_path}")

    def _print_terminal_summary(self):
        """Human-readable terminal output at end of run."""
        print("\n" + "=" * 60)
        print(f"  TestMart AI-QE Pipeline — Run Complete")
        print("=" * 60)
        print(f"  Run ID      : {self.run_id}")
        print(f"  Feature     : {self.feature_name}")
        print(f"  Status      : {self.final_status}")
        print()
        print("  Agent Results:")

        status_icon = {"completed": "✓", "failed": "✗", "skipped": "–"}
        for agent in self.agent_results:
            icon       = status_icon.get(agent["status"], "?")
            review_tag = " ⚠ REVIEW" if agent["needs_human_review"] else ""
            print(
                f"    {icon} {agent['name']:<28} "
                f"confidence={agent['confidence']:.2f}  "
                f"{agent['duration_sec']}s{review_tag}"
            )
            for flag in agent.get("flagged", []):
                print(f"        ↳ {flag}")

        print()

        review_queue = Path(
            self.config["agents"]["rating_judge"]
            .get("escalation", {})
            .get("queue_path", "human_review/human_review_queue.json")
        )
        if review_queue.exists():
            try:
                queue     = json.loads(review_queue.read_text())
                this_run  = [i for i in queue if i.get("run_id") == self.run_id]
                if this_run:
                    print(f"  ⚠  {len(this_run)} item(s) awaiting human review:")
                    print(f"     → {review_queue}")
                    print()
            except Exception:
                pass

        if self.errors:
            print("  Errors:")
            for err in self.errors:
                print(f"    ✗ {err}")
            print()

        if self.final_status == "SUCCESS":
            script = f"tests/api/test_{self.feature_name}_api.py"
            print(f"  ✓ Run pytest:")
            print(f"    pytest {script} -v")
            print(f"    pytest {script} -v -m smoke")

        print("=" * 60 + "\n")


# ── CLI entry point ───────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="TestMart AI-QE Pipeline Orchestrator"
    )
    parser.add_argument("--feature", required=True, help="Feature name e.g. login")
    parser.add_argument("--spec",    default=None,
        help="Path to feature spec markdown (default: requirements/{feature}_FEATURES.md)")
    parser.add_argument("--openapi", default="requirements/openapi.json",
        help="Path to openapi.json")
    parser.add_argument("--conftest", default="tests/conftest.py",
        help="Path to conftest.py")
    args = parser.parse_args()

    feature  = args.feature.lower()
    spec     = args.spec or f"requirements/{feature.upper()}_FEATURES.md"
    openapi  = args.openapi
    conftest = args.conftest

    for path in [spec, openapi]:
        if not Path(path).exists():
            logger.error(f"Required file not found: {path}")
            sys.exit(1)

    orchestrator = OrchestratorAgent(
        feature_name  = feature,
        spec_path     = spec,
        openapi_path  = openapi,
        conftest_path = conftest,
    )

    success = orchestrator.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()