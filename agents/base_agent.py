"""
agents/base_agent.py
====================
Shared base class for every agent in the TestMart AI-QE Pipeline.

Every agent inherits from AgentBase. It provides:
  - Groq client (llama-3.3-70b-versatile or llama-3.1-8b-instant)
  - Config loading from agent_config.yaml
  - Decision log writer (one file per agent per run)
  - Memory read/write (cross-run JSON store)
  - Confidence gate (auto-escalate below threshold)
  - Structured output helper (JSON mode)
  - Retry with backoff
"""

import os
import json
import time
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from groq import Groq

# ── Config path (relative to project root) ──────────────────
CONFIG_PATH = Path(__file__).parent.parent / "agent_config.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


class AgentBase(ABC):
    """
    Base class for all QE pipeline agents.

    Subclasses must implement:
        run(self, input_data: dict) -> dict
    
    run() must return a dict that always contains:
        {
          "output":     <agent-specific payload>,
          "confidence": <float 0.0–1.0>,
          "flagged":    <list of issues for human review>,
          "agent":      <agent name string>
        }
    """

    def __init__(self, agent_name: str, run_id: str):
        self.agent_name = agent_name
        self.run_id = run_id
        self.config = load_config()
        self.agent_cfg = self.config["agents"][agent_name]
        self.paths = self.config["paths"]

        # ── Groq client ──────────────────────────────────────
        api_key = os.environ.get(self.config["groq"]["api_key_env"])
        if not api_key:
            raise EnvironmentError(
                f"GROQ_API_KEY not set. "
                f"Run: export GROQ_API_KEY=your_key"
            )
        self.client = Groq(api_key=api_key)
        self.model = self.agent_cfg["model"]
        self.temperature = self.agent_cfg["temperature"]
        self.max_tokens = self.agent_cfg["max_tokens"]
        self.confidence_threshold = self.agent_cfg["confidence_threshold"]
        self.max_retries = self.agent_cfg.get("max_retries", 2)

        # ── Logging ──────────────────────────────────────────
        log_cfg = self.config["logging"]
        self._setup_logging(log_cfg)

        # ── Decision log path ────────────────────────────────
        log_dir = Path(self.paths["logs_dir"]) / f"run_{self.run_id}"
        log_dir.mkdir(parents=True, exist_ok=True)
        self.decision_log_path = log_dir / f"{agent_name}_decision.log"

        # ── Memory path ──────────────────────────────────────
        self.memory_path = (
            Path(self.paths["memory_dir"]) / f"{agent_name}_memory.json"
        )
        Path(self.paths["memory_dir"]).mkdir(parents=True, exist_ok=True)

        self.logger.info(f"[{self.agent_name}] Initialized | run={self.run_id}")

    # ── Setup ────────────────────────────────────────────────

    def _setup_logging(self, log_cfg: dict):
        level = getattr(logging, log_cfg.get("level", "INFO"))
        logging.basicConfig(
            level=level,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.logger = logging.getLogger(self.agent_name)

    # ── Token estimation ─────────────────────────────────────

    # Free tier TPM limits per model (tokens per minute)
    _TPM_LIMITS = {
        "llama-3.3-70b-versatile": 12000,
        "llama-3.1-8b-instant":    6000,
    }
    # Rough chars-per-token ratio for estimation (conservative)
    _CHARS_PER_TOKEN = 3.5

    def _estimate_tokens(self, text: str) -> int:
        return int(len(text) / self._CHARS_PER_TOKEN)

    def _trim_to_token_budget(self, text: str, max_tokens: int) -> str:
        """
        Hard-trim a text block to stay within a token budget.
        Trims from the END (keeps beginning — most important context first).
        Appends a notice so the LLM knows content was trimmed.
        """
        max_chars = int(max_tokens * self._CHARS_PER_TOKEN)
        if len(text) <= max_chars:
            return text
        trimmed = text[:max_chars]
        self.logger.warning(
            f"[{self.agent_name}] Prompt trimmed: "
            f"{len(text)} → {len(trimmed)} chars to stay within TPM limit"
        )
        return trimmed + "\n... [content trimmed to stay within token limit]"

    def _safe_prompt_budget(self) -> int:
        """
        Return the max tokens we can use for the COMBINED prompt
        (system + user), leaving headroom for the response.
        Budget = TPM_limit × 0.6 (60% for input, 40% for output headroom)
        """
        tpm = self._TPM_LIMITS.get(self.model, 6000)
        return int(tpm * 0.6)

    # ── Core LLM call ────────────────────────────────────────

    def call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
    ) -> str:
        """
        Call the Groq LLM with 429-aware retry + backoff.
        Reads the retry-after header when rate limited.
        Trims prompts that exceed the safe token budget.
        Returns the raw string content of the response.
        """
        # ── Trim prompts to safe budget before sending ────────
        budget        = self._safe_prompt_budget()
        system_tokens = self._estimate_tokens(system_prompt)
        user_budget   = max(500, budget - system_tokens)
        user_prompt   = self._trim_to_token_budget(user_prompt, user_budget)

        estimated_tokens = system_tokens + self._estimate_tokens(user_prompt)
        self.logger.debug(
            f"[{self.agent_name}] Estimated prompt tokens: ~{estimated_tokens} "
            f"(budget: {budget})"
        )

        attempt    = 0
        last_error = None

        while attempt <= self.max_retries:
            try:
                kwargs = dict(
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_prompt},
                    ],
                )
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}

                response = self.client.chat.completions.create(**kwargs)
                content  = response.choices[0].message.content
                self.logger.info(
                    f"[{self.agent_name}] LLM call OK | "
                    f"attempt={attempt+1} | tokens={response.usage.total_tokens}"
                )
                return content

            except Exception as e:
                last_error  = e
                error_str   = str(e)

                # ── 429 Rate limit — read retry-after header ──
                wait = self._parse_retry_after(e, attempt)
                self.logger.warning(
                    f"[{self.agent_name}] LLM error (attempt {attempt+1}/{self.max_retries+1}): "
                    f"{'Rate limited (429)' if '429' in error_str else error_str[:80]}. "
                    f"Waiting {wait}s before retry..."
                )
                time.sleep(wait)
                attempt += 1

        raise RuntimeError(
            f"[{self.agent_name}] LLM call failed after "
            f"{self.max_retries+1} attempts. Last error: {last_error}"
        )

    def _parse_retry_after(self, error: Exception, attempt: int) -> float:
        """
        Extract retry-after seconds from a 429 response.
        Falls back to exponential backoff if header not available.
        Adds a small jitter to avoid thundering herd.
        """
        import random

        # Groq SDK wraps the response — try to read retry-after header
        retry_after = None
        try:
            # groq.RateLimitError exposes .response with headers
            response = getattr(error, "response", None)
            if response is not None:
                headers     = getattr(response, "headers", {})
                retry_after = headers.get("retry-after") or headers.get("x-ratelimit-reset-tokens")
                if retry_after:
                    retry_after = float(retry_after)
        except Exception:
            pass

        if retry_after:
            # Add small jitter (±2s) so parallel runs don't all retry at once
            jitter = random.uniform(1, 3)
            wait   = retry_after + jitter
            self.logger.info(
                f"[{self.agent_name}] Groq retry-after header: {retry_after}s + {jitter:.1f}s jitter"
            )
            return wait

        # Fallback: exponential backoff — 10s, 20s, 40s
        # Longer than before because 429s need real cooldown time
        base_wait = 10 * (2 ** attempt)
        jitter    = random.uniform(1, 5)
        return min(base_wait + jitter, 120)   # cap at 2 minutes

    def call_llm_json(self, system_prompt: str, user_prompt: str) -> dict:
        """
        Call LLM in JSON mode and parse the response.
        Returns a Python dict.
        """
        raw = self.call_llm(system_prompt, user_prompt, json_mode=True)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            self.logger.error(
                f"[{self.agent_name}] JSON parse failed: {e}\nRaw: {raw[:500]}"
            )
            raise

    # ── Confidence gate ──────────────────────────────────────

    def confidence_gate(self, result: dict) -> dict:
        """
        Check confidence score. If below threshold:
          - Log to decision log
          - Add to human_review_queue (if escalation enabled)
          - Mark result with needs_human_review=True
        Returns the result dict (possibly mutated).
        """
        confidence = result.get("confidence", 1.0)
        threshold = self.confidence_threshold

        if confidence < threshold:
            self.logger.warning(
                f"[{self.agent_name}] Confidence {confidence:.2f} < "
                f"threshold {threshold:.2f} — escalating to human review"
            )
            result["needs_human_review"] = True
            self._write_to_human_review_queue(result)
        else:
            result["needs_human_review"] = False

        return result

    def _write_to_human_review_queue(self, result: dict):
        escalation_cfg = self.agent_cfg.get("escalation", {})
        if not escalation_cfg.get("enabled", False):
            return

        queue_path = Path(escalation_cfg["queue_path"])
        queue_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing queue
        queue = []
        if queue_path.exists():
            with open(queue_path) as f:
                try:
                    queue = json.load(f)
                except json.JSONDecodeError:
                    queue = []

        # Append new entry
        queue.append({
            "run_id": self.run_id,
            "agent": self.agent_name,
            "timestamp": datetime.utcnow().isoformat(),
            "confidence": result.get("confidence"),
            "flagged": result.get("flagged", []),
            "output_summary": str(result.get("output", ""))[:500],
        })

        with open(queue_path, "w") as f:
            json.dump(queue, f, indent=2)

        self.logger.info(
            f"[{self.agent_name}] Escalated to human review queue: "
            f"{queue_path}"
        )

    # ── Decision log ─────────────────────────────────────────

    def write_decision_log(
        self,
        inputs: dict,
        rules_applied: list[str],
        decisions: list[str],
        result: dict,
    ):
        """
        Write a structured decision log entry for this agent run.
        One file per agent per pipeline run.
        """
        if not self.config["logging"].get("write_decision_logs", True):
            return

        entry = {
            "run_id": self.run_id,
            "agent": self.agent_name,
            "model": self.model,
            "timestamp": datetime.utcnow().isoformat(),
            "inputs_summary": {k: str(v)[:300] for k, v in inputs.items()},
            "rules_applied": rules_applied,
            "decisions": decisions,
            "confidence": result.get("confidence"),
            "needs_human_review": result.get("needs_human_review", False),
            "flagged": result.get("flagged", []),
        }

        with open(self.decision_log_path, "w") as f:
            json.dump(entry, f, indent=2)

        self.logger.info(
            f"[{self.agent_name}] Decision log written → "
            f"{self.decision_log_path}"
        )

    # ── Memory ───────────────────────────────────────────────

    def load_memory(self) -> list[dict]:
        """Load cross-run memory for this agent. Returns list of entries."""
        if not self.config["memory"].get("enabled", True):
            return []
        if not self.memory_path.exists():
            return []
        with open(self.memory_path) as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

    def save_memory(self, new_entry: dict):
        """
        Append a new memory entry for this agent.
        Prunes to max_entries_per_agent (rolling window).
        """
        if not self.config["memory"].get("enabled", True):
            return

        max_entries = self.config["memory"].get("max_entries_per_agent", 50)
        entries = self.load_memory()
        entries.append({
            "run_id": self.run_id,
            "timestamp": datetime.utcnow().isoformat(),
            **new_entry,
        })

        # Prune oldest entries
        if len(entries) > max_entries:
            entries = entries[-max_entries:]

        with open(self.memory_path, "w") as f:
            json.dump(entries, f, indent=2)

        self.logger.info(
            f"[{self.agent_name}] Memory updated → {self.memory_path} "
            f"({len(entries)} entries)"
        )

    def format_memory_for_prompt(self, entries: list[dict], max_entries: int = 5) -> str:
        """
        Format recent memory entries as a readable string
        to inject into the agent's system prompt.
        """
        if not entries:
            return "No prior run history available."

        recent = entries[-max_entries:]
        lines = ["=== MEMORY FROM PRIOR RUNS ==="]
        for e in recent:
            lines.append(f"• [{e.get('timestamp', '')[:10]}] {e.get('summary', str(e))}")
        lines.append("=== END MEMORY ===")
        return "\n".join(lines)

    # ── Abstract interface ───────────────────────────────────

    @abstractmethod
    def run(self, input_data: dict) -> dict:
        """
        Execute this agent's task.

        Args:
            input_data: dict of inputs specific to this agent

        Returns:
            dict with keys:
              output      – agent-specific result payload
              confidence  – float 0.0–1.0
              flagged     – list of concern strings
              agent       – agent name
        """
        raise NotImplementedError

    # ── Utility ──────────────────────────────────────────────

    def read_file(self, path: str | Path) -> str:
        with open(path) as f:
            return f.read()

    def write_file(self, path: str | Path, content: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        self.logger.info(f"[{self.agent_name}] Wrote → {path}")

    def write_json(self, path: str | Path, data: dict | list):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        self.logger.info(f"[{self.agent_name}] Wrote JSON → {path}")

    def read_json(self, path: str | Path) -> dict | list:
        with open(path) as f:
            return json.load(f)