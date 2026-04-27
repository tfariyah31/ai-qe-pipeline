"""
pipeline_runner.py  (Day 2 — with Stop support)
-------------------------------------------------
Changes from previous version:
  - self._proc saves subprocess reference so stop() can terminate it
  - stop() method kills subprocess and marks pipeline done
  - Required field validation handled in sidebar
"""

import threading
import queue
import time
import os
import json
import pathlib
import subprocess
import sys
from datetime import datetime
import threading


AGENTS_IN_ORDER = [
    "SpecAnalystAgent",
    "GherkinAuthorAgent",
    "RatingJudgeAgent",
    "EnrichmentAgent",
    "ScriptForgeAgent",
    "OrchestratorAgent",
]

SIGNAL_KEYS = {
    "SpecAnalystAgent":   "specanalyst",
    "GherkinAuthorAgent": "gherkinauthor",
    "RatingJudgeAgent":   "ratingjudge",
    "EnrichmentAgent":    "enrichment",
    "ScriptForgeAgent":   "scriptforge",
    "OrchestratorAgent":  "orchestrator",
}

AGENT_LOG_FILES = {
    "SpecAnalystAgent":   "spec_analyst_decision.log",
    "GherkinAuthorAgent": "gherkin_author_decision.log",
    "RatingJudgeAgent":   "rating_judge_decision.log",
    "EnrichmentAgent":    "enrichment_decision.log",
    "ScriptForgeAgent":   "script_forge_decision.log",
    "OrchestratorAgent":  "pipeline_summary.log",
}

AGENT_SIGNAL_FILES = {
    agent: f".signal_{agent.lower().replace('agent', '')}"
    for agent in AGENTS_IN_ORDER
}

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.resolve()
_STOP_EVENT = threading.Event()

class PipelineRunner:
    def __init__(self, feature_name: str, spec_text: str):
        self.feature_name = feature_name.strip().lower().replace(" ", "_")
        self.spec_text    = spec_text
        self.run_id       = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._queue: queue.Queue = queue.Queue()
        self._thread: threading.Thread | None = None
        self._proc:   subprocess.Popen | None = None   # ← saved for stop()
        self._done    = False
        self._stopped = False

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self):
        self._write_spec()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def poll(self) -> list[dict]:
        updates = []
        while not self._queue.empty():
            try:
                updates.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return updates

    def is_done(self) -> bool:
        return self._done

    def stop(self):
        self._stopped = True
        self._done = True
        _STOP_EVENT.set()          # ← signals the orchestrator to stop
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            self._proc.wait()
        self._emit_log("warning", "⏹  Pipeline stopped by user")
        self._queue.put({"type": "pipeline_failed", "error": "Stopped by user"})

    # ── Internal ──────────────────────────────────────────────────────────────

    def _write_spec(self):
        req_dir   = PROJECT_ROOT / "requirements"
        req_dir.mkdir(exist_ok=True)
        spec_path = req_dir / f"{self.feature_name.upper()}_FEATURES.md"
        spec_path.write_text(self.spec_text, encoding="utf-8")
        self._emit_log("info", f"Spec written → {spec_path.name}")

    def _run(self):
        try:
            log_dir = PROJECT_ROOT / "logs" / f"run_{self.run_id}"
            log_dir.mkdir(parents=True, exist_ok=True)

            self._emit_log("agent", f"🚀  Pipeline starting — feature: {self.feature_name}")
            self._emit_log("info",  f"Run ID: {self.run_id}")

            for agent in AGENTS_IN_ORDER:
                self._queue.put({
                    "type": "agent_update",
                    "agent": agent,
                    "status": "waiting",
                })

            try:
                self._run_via_import()
            except ImportError as e:
                self._emit_log("warning", f"Direct import failed ({e}) — running via subprocess")
                self._run_via_subprocess()

        except Exception as exc:
            if not self._stopped:
                self._emit_log("error", f"Pipeline error: {exc}")
                self._queue.put({"type": "pipeline_failed", "error": str(exc)})
        finally:
            self._done = True

    def _run_via_import(self):
        """Call orchestrator directly in-process (fastest, preferred)."""
        _STOP_EVENT.clear()
        import importlib
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))

        orchestrator_module = importlib.import_module(
            "agents.orchestrator.orchestrator_agent"
      )

        watcher = threading.Thread(
            target=self._watch_agent_signals,
            args=(self.run_id,),
            daemon=True,
        )
        watcher.start()

        cls   = getattr(orchestrator_module, "OrchestratorAgent")
        agent = cls(
            feature_name  = self.feature_name,
            spec_path     = f"requirements/{self.feature_name.upper()}_FEATURES.md",
            openapi_path  = "requirements/openapi.json",
            conftest_path = "tests/conftest.py",
        )
        agent.run_id = self.run_id
        agent.run()

        # ← Wait for watcher to finish before emitting pipeline_complete
        watcher.join(timeout=30)

        if not self._stopped:
            self._finish_pipeline()

    def _run_via_subprocess(self):
        """Fallback: run orchestrator as a subprocess."""
        cmd = [
            sys.executable, "-m",
            "agents.orchestrator.orchestrator_agent",
            "--feature", self.feature_name,
        ]
        env = os.environ.copy()
        env["PIPELINE_RUN_ID"] = self.run_id

        # ── Save proc as self._proc so stop() can terminate it ────────────────
        self._proc = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            start_new_session=False,
        )
        proc = self._proc

        watcher = threading.Thread(
            target=self._watch_agent_signals,
            args=(self.run_id,),
            daemon=True,
        )
        watcher.start()

        try:
            for line in proc.stdout:
                if self._stopped:
                    break
                line = line.rstrip()
                if line:
                    self._emit_log(self._classify_line(line), line)
        finally:
            if proc.poll() is None:
                proc.terminate()
            proc.wait()

        if self._stopped:
            return

        if proc.returncode in (0, None):
            self._finish_pipeline()
        else:
            self._queue.put({
                "type": "pipeline_failed",
                "error": f"Subprocess exited with code {proc.returncode}"
            })

    def _watch_agent_signals(self, run_id: str):
        """
        Poll for .signal_{agent} files independently for each agent.
        Cards flip to Running only when the previous agent completes.
        Cards flip to Complete as soon as signal file appears.
        """
        log_dir     = PROJECT_ROOT / "logs" / f"run_{run_id}"
        completed:   set[str]         = set()
        running:     set[str]         = set()
        start_times: dict[str, float] = {}
        deadline     = time.time() + 600

        while time.time() < deadline and not self._stopped:
            all_done = True

            for agent in AGENTS_IN_ORDER:
                if agent in completed:
                    continue

                all_done  = False
                agent_idx = AGENTS_IN_ORDER.index(agent)
                # OrchestratorAgent runs the whole time — mark running immediately
                is_orchestrator = agent == "OrchestratorAgent"
                prev_done = agent_idx == 0 or AGENTS_IN_ORDER[agent_idx - 1] in completed or is_orchestrator

                if agent not in running and (prev_done or is_orchestrator):
                    running.add(agent)
                    start_times[agent] = time.time()
                    self._queue.put({
                        "type": "agent_update",
                        "agent": agent,
                        "status": "running",
                    })
                    self._emit_log("agent", f"► {agent} starting...")

                # Only check signal if agent is marked running
                if agent not in running:
                    continue

                signal_key  = SIGNAL_KEYS.get(agent, agent.lower())
                signal_path = log_dir / f".signal_{signal_key}"
                log_path    = log_dir / AGENT_LOG_FILES.get(agent, "")

                found      = False
                confidence = None
                escalated  = False

                if signal_path.exists():
                    try:
                        data       = json.loads(signal_path.read_text(encoding="utf-8"))
                        confidence = data.get("confidence")
                        escalated  = data.get("escalated", False)
                        found      = True
                    except (json.JSONDecodeError, OSError):
                        pass

                elif log_path.exists() and log_path.stat().st_size > 50:
                    confidence, escalated = self._parse_decision_log(log_path)
                    found = True

                if found:
                    duration = round(time.time() - start_times.get(agent, time.time()), 1)
                    completed.add(agent)
                    status = "escalated" if escalated else "complete"

                    self._queue.put({
                        "type": "agent_update",
                        "agent": agent,
                        "status": status,
                        "confidence": confidence,
                        "duration": duration,
                    })

                    icon     = "⚠️" if escalated else "✅"
                    conf_str = f"(confidence: {confidence:.2f})" if confidence else ""
                    self._emit_log(
                        "warning" if escalated else "success",
                        f"{icon}  {agent} {status} in {duration}s {conf_str}"
                    )

                    if log_path.exists():
                        self._stream_log_preview(log_path)

            if all_done:
                break

            time.sleep(1.0)

    def _stream_log_preview(self, log_path: pathlib.Path, max_lines: int = 15):
        try:
            lines = log_path.read_text(encoding="utf-8").splitlines()
            for line in lines[:max_lines]:
                if line.strip():
                    self._emit_log(self._classify_line(line), f"    {line}")
        except OSError:
            pass

    def _parse_decision_log(self, log_path: pathlib.Path) -> tuple[float | None, bool]:
        confidence = None
        escalated  = False
        try:
            text = log_path.read_text(encoding="utf-8")
            for line in text.splitlines():
                lower = line.lower()
                if "confidence" in lower and ":" in line:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        try:
                            confidence = float(parts[-1].strip().split()[0])
                        except ValueError:
                            pass
                if "human_review" in lower or "needs_human_review: true" in lower:
                    escalated = True
        except OSError:
            pass
        return confidence, escalated

    def _finish_pipeline(self):
        self._emit_log("success", "✅  All agents complete — pipeline done")
        metrics = self._collect_metrics()
        self._queue.put({"type": "metrics", "data": metrics})
        self._queue.put({"type": "pipeline_complete"})

    def _collect_metrics(self) -> dict:
        metrics = {
            "scenarios_generated": 0,
            "tests_created":       0,
            "escalations":         0,
            "scenarios_dropped":   0,
        }
        try:
            gherkin_path = (
                PROJECT_ROOT / "tests" / "test_cases"
                / f"{self.feature_name}.enriched.md"
            )
            if gherkin_path.exists():
                metrics["scenarios_generated"] = gherkin_path.read_text().count("Scenario:")

            test_path = (
                PROJECT_ROOT / "tests" / "api"
                / f"test_{self.feature_name}_api.py"
            )
            if test_path.exists():
                metrics["tests_created"] = test_path.read_text().count("def test_")

            queue_path = PROJECT_ROOT / "human_review" / "human_review_queue.json"
            if queue_path.exists():
                data = json.loads(queue_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    metrics["escalations"] = len(data)

            rejection_path = (
                PROJECT_ROOT / "tests" / "test_cases"
                / f"{self.feature_name}.rejection_summary.md"
            )
            if rejection_path.exists():
                metrics["scenarios_dropped"] = rejection_path.read_text().count("##")
        except Exception:
            pass
        return metrics

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _on_agent_log(self, agent_name: str, event: str, data: dict):
        if event == "start":
            self._queue.put({
                "type": "agent_update",
                "agent": agent_name,
                "status": "running",
            })
        elif event == "complete":
            self._queue.put({
                "type": "agent_update",
                "agent": agent_name,
                "status": "escalated" if data.get("needs_human_review") else "complete",
                "confidence": data.get("confidence"),
                "duration": data.get("duration"),
            })
        elif event == "log":
            self._emit_log(data.get("level", "info"), data.get("message", ""))

    def _emit_log(self, level: str, message: str):
        self._queue.put({
            "type": "log",
            "level": level,
            "message": message,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        })

    @staticmethod
    def _classify_line(line: str) -> str:
        lower = line.lower()
        if any(w in lower for w in ("error", "fail", "exception", "traceback")):
            return "error"
        if any(w in lower for w in ("warn", "escalat", "review")):
            return "warning"
        if any(w in lower for w in ("✅", "complete", "success", "done", "generated")):
            return "success"
        if any(w in lower for w in ("agent", "running", "start", "►")):
            return "agent"
        return "info"