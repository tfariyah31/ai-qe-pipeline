import streamlit as st
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from components.sidebar      import render_sidebar
from components.agent_status import render_agent_status
from components.log_viewer   import render_log_viewer
from components.review_queue import render_review_queue
from components.results_tabs import render_results_tabs   # ← NEW
from pipeline_runner         import PipelineRunner

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI QE Console",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;600;800&display=swap');

:root {
    --bg: #0a0e14;
    --surface: #111720;
    --border: #1e2a38;
    --accent: #00d9ff;
    --accent2: #7c3aed;
    --success: #10b981;
    --warning: #f59e0b;
    --danger: #ef4444;
    --text: #e2e8f0;
    --muted: #64748b;
}

html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
    background-color: var(--bg);
    color: var(--text);
}

#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 2rem 4rem; max-width: 100%; }

.qa-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1.5rem 0 2rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 2rem;
}
.qa-header h1 {
    font-size: 2rem;
    font-weight: 800;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
    letter-spacing: -0.03em;
}
.qa-header .subtitle {
    font-size: 0.85rem;
    color: var(--muted);
    font-family: 'JetBrains Mono', monospace;
    margin: 0;
}

.agent-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 0.75rem;
    transition: border-color 0.2s;
}
.agent-card.running   { border-color: var(--accent); }
.agent-card.complete  { border-color: var(--success); }
.agent-card.escalated { border-color: var(--warning); }
.agent-card.failed    { border-color: var(--danger); }

.agent-name {
    font-weight: 600;
    font-size: 0.9rem;
    margin-bottom: 0.4rem;
}
.agent-meta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: var(--muted);
    display: flex;
    gap: 1.5rem;
}

.badge {
    display: inline-block;
    padding: 0.15rem 0.6rem;
    border-radius: 100px;
    font-size: 0.7rem;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.badge-waiting   { background: #1e2a38; color: var(--muted); }
.badge-running   { background: rgba(0,217,255,0.1); color: var(--accent); }
.badge-complete  { background: rgba(16,185,129,0.1); color: var(--success); }
.badge-escalated { background: rgba(245,158,11,0.1); color: var(--warning); }
.badge-failed    { background: rgba(239,68,68,0.1); color: var(--danger); }

.log-container {
    background: #070b10;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    line-height: 1.6;
    max-height: 400px;
    overflow-y: auto;
    color: #a8c0d6;
}

.review-item {
    background: rgba(245,158,11,0.05);
    border: 1px solid rgba(245,158,11,0.2);
    border-radius: 6px;
    padding: 0.85rem;
    margin-bottom: 0.6rem;
}

.progress-track {
    height: 4px;
    background: var(--border);
    border-radius: 2px;
    margin: 1rem 0 1.5rem;
    overflow: hidden;
}
.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent2), var(--accent));
    border-radius: 2px;
    transition: width 0.5s ease;
}

.metric-tile {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem 1.25rem;
    text-align: center;
}
.metric-tile .value {
    font-size: 1.8rem;
    font-weight: 800;
    color: var(--accent);
    line-height: 1;
}
.metric-tile .label {
    font-size: 0.72rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 0.4rem;
    font-family: 'JetBrains Mono', monospace;
}

.stButton > button {
    background: linear-gradient(135deg, var(--accent2), var(--accent)) !important;
    color: white !important;
    border: none !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
    padding: 0.6rem 1.5rem !important;
    border-radius: 6px !important;
    transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.85 !important; }

[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}
</style>
""", unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────────────
if "pipeline_state" not in st.session_state:
    st.session_state.pipeline_state = {
        "status":  "idle",
        "run_id":  None,
        "feature": None,
        "agents": {
            "SpecAnalystAgent":   {"status": "waiting", "confidence": None, "duration": None},
            "GherkinAuthorAgent": {"status": "waiting", "confidence": None, "duration": None},
            "RatingJudgeAgent":   {"status": "waiting", "confidence": None, "duration": None},
            "EnrichmentAgent":    {"status": "waiting", "confidence": None, "duration": None},
            "ScriptForgeAgent":   {"status": "waiting", "confidence": None, "duration": None},
            "OrchestratorAgent":  {"status": "waiting", "confidence": None, "duration": None},
        },
        "logs": [],
        "metrics": {
            "scenarios_generated": 0,
            "tests_created":       0,
            "escalations":         0,
            "scenarios_dropped":   0,
        }
    }

if "runner" not in st.session_state:
    st.session_state.runner = None

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="qa-header">
    <div>
        <h1>🤖 AI QE Console</h1>
        <p class="subtitle">AI-Orchestrated Quality Engineering Pipeline · 6 Agents · Live</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Layout ────────────────────────────────────────────────────────────────────
sidebar_col, main_col = st.columns([1, 2.5], gap="large")

with sidebar_col:
    feature_name, spec_text, run_clicked = render_sidebar(st.session_state.pipeline_state)

    if run_clicked and feature_name and spec_text:
        runner = PipelineRunner(feature_name, spec_text)
        st.session_state.runner = runner
        st.session_state.pipeline_state["status"]  = "running"
        st.session_state.pipeline_state["feature"] = feature_name
        st.session_state.pipeline_state["run_id"]  = runner.run_id
        st.session_state.pipeline_state["logs"]    = []
        for agent in st.session_state.pipeline_state["agents"]:
            st.session_state.pipeline_state["agents"][agent] = {
                "status": "waiting", "confidence": None, "duration": None
            }
        runner.start()
        st.rerun()

with main_col:
    state = st.session_state.pipeline_state

    # Progress bar
    if state["status"] in ("running", "complete"):
        completed = sum(
            1 for a in state["agents"].values()
            if a["status"] in ("complete", "escalated", "failed")
        )
        pct = int((completed / 6) * 100)
        st.markdown(f"""
        <div class="progress-track">
            <div class="progress-fill" style="width:{pct}%"></div>
        </div>
        """, unsafe_allow_html=True)

    # Poll runner for updates
    if state["status"] == "running" and st.session_state.runner:
        runner  = st.session_state.runner
        updates = runner.poll()

        for update in updates:
            utype = update.get("type")
            if utype == "agent_update":
                agent_name = update["agent"]
                if agent_name in state["agents"]:
                    state["agents"][agent_name].update({
                        "status":     update.get("status", "running"),
                        "confidence": update.get("confidence"),
                        "duration":   update.get("duration"),
                    })
            elif utype == "log":
                state["logs"].append(update)
            elif utype == "metrics":
                state["metrics"].update(update.get("data", {}))
            elif utype == "pipeline_complete":
                state["status"] = "complete"
                st.rerun()
            elif utype == "pipeline_failed":
                state["status"] = "failed"
                st.rerun()

    # Metrics row
    if state["status"] in ("running", "complete"):
        m  = state["metrics"]
        c1, c2, c3, c4 = st.columns(4)
        for col, val, label in [
            (c1, m["scenarios_generated"], "Scenarios"),
            (c2, m["tests_created"],       "Tests Created"),
            (c3, m["escalations"],         "Escalations"),
            (c4, m["scenarios_dropped"],   "Dropped"),
        ]:
            with col:
                st.markdown(f"""
                <div class="metric-tile">
                    <div class="value">{val}</div>
                    <div class="label">{label}</div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # Tabs
    tab_agents, tab_logs, tab_queue = st.tabs(
        ["🤖 Agent Pipeline", "📋 Live Logs", "⚠️ Review Queue"]
    )

    with tab_agents:
        render_agent_status(state["agents"])

    with tab_logs:
        render_log_viewer(state["logs"])

    with tab_queue:
        render_review_queue(state.get("run_id"))

    # ── Results tabs shown after completion ── ← NEW ──────────────────────────
    if state["status"] == "complete" and state.get("feature"):
        render_results_tabs(state["feature"])

    # Auto-rerun while running
    if state["status"] == "running":
        import time
        time.sleep(1.5)
        st.rerun()