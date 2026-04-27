import streamlit as st

LEVEL_COLOR = {
    "info":    "#a8c0d6",
    "success": "#10b981",
    "warning": "#f59e0b",
    "error":   "#ef4444",
    "agent":   "#00d9ff",
}

LEVEL_PREFIX = {
    "info":    "   ",
    "success": "✓  ",
    "warning": "⚠  ",
    "error":   "✗  ",
    "agent":   "►  ",
}


def render_log_viewer(logs: list[dict]):
    """Render a terminal-style log panel."""
    if not logs:
        st.markdown("""
        <div style="
            text-align: center;
            padding: 3rem 1rem;
            color: #64748b;
            font-size: 0.85rem;
            font-family: 'JetBrains Mono', monospace;
        ">
            Logs will appear here during the pipeline run.
        </div>
        """, unsafe_allow_html=True)
        return

    lines_html = ""
    for entry in logs[-200:]:   # cap at last 200 lines
        level = entry.get("level", "info")
        msg   = entry.get("message", "")
        ts    = entry.get("timestamp", "")
        color  = LEVEL_COLOR.get(level, "#a8c0d6")
        prefix = LEVEL_PREFIX.get(level, "   ")

        # Escape HTML special chars
        msg = msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        lines_html += (
            f'<div style="color:{color}">'
            f'<span style="color:#2d3f52;user-select:none">{ts} </span>'
            f'{prefix}{msg}'
            f'</div>'
        )

    # Auto-scroll JS — scrolls to bottom when new lines arrive
    autoscroll_js = """
    <script>
        const logBox = document.getElementById('log-box');
        if (logBox) { logBox.scrollTop = logBox.scrollHeight; }
    </script>
    """

    st.markdown(f"""
    <div id="log-box" class="log-container">
        {lines_html}
    </div>
    {autoscroll_js}
    """, unsafe_allow_html=True)

    st.caption(f"{len(logs)} log entries")