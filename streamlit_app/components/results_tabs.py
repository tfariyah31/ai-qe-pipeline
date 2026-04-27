"""
components/results_tabs.py
---------------------------
Shown after pipeline completes. Three tabs:
  1. Gherkin   — login.enriched.md
  2. pytest    — test_login_api.py
  3. Risk Scores — login_ratings.json bar chart
"""

import json
import pathlib
import streamlit as st

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.resolve()


def render_results_tabs(feature_name: str):
    """Call this after pipeline_state['status'] == 'complete'."""

    if not feature_name:
        return

    fname = feature_name.strip().lower().replace(" ", "_")

    gherkin_path  = PROJECT_ROOT / "tests" / "test_cases" / f"{fname}.enriched.md"
    pytest_path   = PROJECT_ROOT / "tests" / "api"        / f"test_{fname}_api.py"
    ratings_path  = PROJECT_ROOT / "ratings"              / f"{fname}_ratings.json"
    rejected_path = PROJECT_ROOT / "tests" / "test_cases" / f"{fname}.rejection_summary.md"

    st.markdown("---")
    st.markdown("### 📁 Generated Outputs")

    tab_gherkin, tab_pytest, tab_scores = st.tabs([
        "📝 Gherkin Scenarios",
        "🧪 pytest Script",
        "📊 Risk Scores",
    ])

    # ── Tab 1: Gherkin ────────────────────────────────────────────────────────
    with tab_gherkin:
        if gherkin_path.exists():
            content       = gherkin_path.read_text(encoding="utf-8")
            scenario_count = content.count("Scenario:")

            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(
                    f"**{scenario_count} scenarios** — `{gherkin_path.name}`"
                )
            with col2:
                st.download_button(
                    label     = "⬇ Download",
                    data      = content,
                    file_name = gherkin_path.name,
                    mime      = "text/markdown",
                    use_container_width=True,
                )

            # Tag summary row
            p0 = content.count("@smoke")
            p2 = content.count("@regression")
            st.markdown(
                f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.78rem;'
                f'color:#64748b;margin-bottom:0.75rem;">'
                f'<span style="color:#ef4444">@smoke</span> {p0} &nbsp;·&nbsp; '
                f'<span style="color:#3b82f6">@regression</span> {p2}'
                f'</div>',
                unsafe_allow_html=True,
            )

            st.code(content, language="gherkin")

            # Rejection summary if present
            if rejected_path.exists():
                with st.expander("🗑 Rejected scenarios"):
                    st.markdown(rejected_path.read_text(encoding="utf-8"))
        else:
            _not_ready(gherkin_path.name)

    # ── Tab 2: pytest ─────────────────────────────────────────────────────────
    with tab_pytest:
        if pytest_path.exists():
            content    = pytest_path.read_text(encoding="utf-8")
            test_count = content.count("def test_")

            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{test_count} test functions** — `{pytest_path.name}`")
            with col2:
                st.download_button(
                    label     = "⬇ Download",
                    data      = content,
                    file_name = pytest_path.name,
                    mime      = "text/x-python",
                    use_container_width=True,
                )

            # Run command hint
            st.markdown(
                f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.76rem;'
                f'background:#070b10;border:1px solid #1e2a38;border-radius:6px;'
                f'padding:0.5rem 0.75rem;color:#10b981;margin-bottom:0.75rem;">'
                f'$ pytest tests/api/{pytest_path.name} -v -m smoke'
                f'</div>',
                unsafe_allow_html=True,
            )

            st.code(content, language="python")
        else:
            _not_ready(pytest_path.name)

    # ── Tab 3: Risk Scores ────────────────────────────────────────────────────
    with tab_scores:
        if ratings_path.exists():
            _render_risk_chart(ratings_path)
        else:
            _not_ready(ratings_path.name)


def _render_risk_chart(ratings_path: pathlib.Path):
    """Parse ratings JSON and render a styled bar chart."""
    try:
        data = json.loads(ratings_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        st.error("Could not parse ratings JSON.")
        return

    # Support nested {"scenarios": [...]} or flat list
    if isinstance(data, dict):
        scenarios = data.get("scenarios") or list(data.values())
    elif isinstance(data, list):
        scenarios = data
    else:
        st.warning("Unexpected ratings format.")
        return

    # Filter out any non-dict items
    scenarios = [s for s in scenarios if isinstance(s, dict)]

    if not scenarios:
        st.info("No ratings data found.")
        return

    # Extract title + score — handle varied key names
    rows = []
    for s in scenarios:
        title = (
            s.get("title") or
            s.get("scenario") or
            s.get("name") or
            s.get("scenario_title") or
            "Unnamed"
        )
        score = (
            s.get("weighted_score") or
            s.get("risk_score") or
            s.get("score") or
            s.get("final_score") or
            0.0
        )
        priority = s.get("priority") or s.get("tag") or ""
        rows.append({"title": title, "score": float(score), "priority": priority})

    # Sort descending
    rows.sort(key=lambda r: r["score"], reverse=True)

    total     = len(rows)
    p0_count  = sum(1 for r in rows if "smoke" in r["priority"].lower() or r["score"] >= 4.0)
    avg_score = round(sum(r["score"] for r in rows) / total, 2) if total else 0

    # Summary tiles
    c1, c2, c3 = st.columns(3)
    for col, val, label in [
        (c1, total,     "Total Scenarios"),
        (c2, p0_count,  "Smoke / P0"),
        (c3, avg_score, "Avg Risk Score"),
    ]:
        with col:
            st.markdown(
                f'<div class="metric-tile">'
                f'<div class="value">{val}</div>'
                f'<div class="label">{label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # Bar chart using Streamlit native (no extra deps)
    import pandas as pd
    df = pd.DataFrame(rows)

    # Truncate long titles for display
    df["display"] = df["title"].apply(
        lambda t: t[:48] + "…" if len(t) > 48 else t
    )

    st.markdown("**Risk score per scenario** (threshold: 3.0 = regression, 4.0 = smoke)")

    # Color-coded score bars via HTML
    for _, row in df.iterrows():
        score    = row["score"]
        pct      = min(score / 5.0, 1.0) * 100
        priority = row["priority"]

        p = priority.upper()
        if score >= 4.0 or p in ("P0", "P1"):
            color, badge_color, badge = "#ef4444", "rgba(239,68,68,0.15)", "smoke"
        elif score >= 3.0 or p == "P2":
            color, badge_color, badge = "#3b82f6", "rgba(59,130,246,0.15)", "regression"
        else:
            color, badge_color, badge = "#475569", "rgba(71,85,105,0.15)", "dropped"
            
        st.markdown(f"""
        <div style="margin-bottom:0.5rem;">
            <div style="
                display:flex;
                justify-content:space-between;
                font-size:0.76rem;
                color:#94a3b8;
                margin-bottom:0.2rem;
            ">
                <span style="max-width:75%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
                    {row['display']}
                </span>
                <span style="display:flex;gap:0.5rem;align-items:center;">
                    <span style="
                        background:{badge_color};
                        color:{color};
                        padding:0.1rem 0.4rem;
                        border-radius:4px;
                        font-family:'JetBrains Mono',monospace;
                        font-size:0.68rem;
                    ">{badge}</span>
                    <b style="color:{color}">{score:.2f}</b>
                </span>
            </div>
            <div style="height:6px;background:#1e2a38;border-radius:3px;">
                <div style="
                    width:{pct}%;
                    height:100%;
                    background:{color};
                    border-radius:3px;
                    transition:width 0.3s ease;
                "></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Download ratings JSON
    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button(
        label     = "⬇ Download ratings JSON",
        data      = ratings_path.read_text(encoding="utf-8"),
        file_name = ratings_path.name,
        mime      = "application/json",
        use_container_width=False,
    )


def _not_ready(filename: str):
    st.markdown(f"""
    <div style="
        text-align:center;
        padding:2.5rem 1rem;
        color:#64748b;
        font-size:0.85rem;
    ">
        <div style="font-size:1.5rem;margin-bottom:0.5rem;">⏳</div>
        <code style="color:#475569">{filename}</code><br>
        <span style="font-size:0.75rem;">Will appear here after pipeline completes.</span>
    </div>
    """, unsafe_allow_html=True)