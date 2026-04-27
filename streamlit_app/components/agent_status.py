import streamlit as st

AGENT_META = {
    "SpecAnalystAgent":   {"icon": "🔍", "model": "llama-3.3-70b", "role": "Reads spec, extracts intent & risks"},
    "GherkinAuthorAgent": {"icon": "✍️",  "model": "llama-3.3-70b", "role": "Writes Gherkin scenarios"},
    "RatingJudgeAgent":   {"icon": "⚖️",  "model": "llama-3.1-8b",  "role": "Scores scenarios (5 dimensions)"},
    "EnrichmentAgent":    {"icon": "🏷️",  "model": "llama-3.1-8b",  "role": "Tags, prioritises, drops low-risk"},
    "ScriptForgeAgent":   {"icon": "🔨",  "model": "llama-3.1-8b",  "role": "Generates pytest scripts"},
    "OrchestratorAgent":  {"icon": "🎛️",  "model": "llama-3.1-8b",  "role": "Routes, retries, escalates"},
}

STATUS_BADGE = {
    "waiting":  ('<span class="badge badge-waiting">Waiting</span>',  "agent-card"),
    "running":  ('<span class="badge badge-running">● Running</span>',  "agent-card running"),
    "complete": ('<span class="badge badge-complete">✓ Complete</span>', "agent-card complete"),
    "escalated":('<span class="badge badge-escalated">⚠ Escalated</span>', "agent-card escalated"),
    "failed":   ('<span class="badge badge-failed">✗ Failed</span>',    "agent-card failed"),
}


def render_agent_status(agents: dict):
    """Render a card for each agent showing status, confidence, and duration."""
    for agent_name, state in agents.items():
        meta = AGENT_META.get(agent_name, {"icon": "🤖", "model": "—", "role": "—"})
        status = state.get("status", "waiting")
        badge_html, card_class = STATUS_BADGE.get(status, STATUS_BADGE["waiting"])

        confidence = state.get("confidence")
        duration = state.get("duration")

        conf_str = f"{confidence:.2f}" if confidence is not None else "—"
        dur_str  = f"{duration}s"      if duration  is not None else "—"

        # Confidence color
        if confidence is None:
            conf_color = "#64748b"
        elif confidence >= 0.8:
            conf_color = "#10b981"
        elif confidence >= 0.6:
            conf_color = "#f59e0b"
        else:
            conf_color = "#ef4444"

        st.markdown(f"""
        <div class="{card_class}">
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div>
                    <div class="agent-name">{meta['icon']}  {agent_name}</div>
                    <div style="font-size:0.75rem; color:#64748b; margin-bottom:0.5rem;">
                        {meta['role']}
                    </div>
                </div>
                <div>{badge_html}</div>
            </div>
            <div class="agent-meta">
                <span>Model: <b style="color:#94a3b8">{meta['model']}</b></span>
                <span>Confidence: <b style="color:{conf_color}">{conf_str}</b></span>
                <span>Duration: <b style="color:#94a3b8">{dur_str}</b></span>
            </div>
        </div>
        """, unsafe_allow_html=True)