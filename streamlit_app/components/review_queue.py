import streamlit as st
import json
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.resolve()


def render_review_queue(run_id: str | None):
    """Read human_review_queue.json and display items needing SDET review."""
    queue_path = PROJECT_ROOT / "human_review" / "human_review_queue.json"

    if not queue_path.exists():
        st.markdown("""
        <div style="
            text-align: center;
            padding: 3rem 1rem;
            color: #64748b;
            font-size: 0.85rem;
        ">
            <div style="font-size:2rem;margin-bottom:0.75rem;">✅</div>
            No items in the review queue.<br>
            <span style="font-size:0.75rem;">
                Items appear here when an agent's confidence falls below threshold.
            </span>
        </div>
        """, unsafe_allow_html=True)
        return

    try:
        data = json.loads(queue_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        st.warning("Could not read human_review_queue.json")
        return

    if not isinstance(data, list) or len(data) == 0:
        st.info("Review queue is empty — all agents passed confidence threshold.")
        return

    st.markdown(
        f'<div style="color:#f59e0b;font-size:0.85rem;margin-bottom:1rem;">'
        f'⚠️  <b>{len(data)} item{"s" if len(data) != 1 else ""}</b> '
        f'need{"s" if len(data) == 1 else ""} SDET review</div>',
        unsafe_allow_html=True,
    )

    for i, item in enumerate(data):
        title       = item.get("title", item.get("scenario", f"Item {i+1}"))
        agent       = item.get("agent", "Unknown agent")
        confidence  = item.get("confidence")
        reason      = item.get("reason", item.get("escalation_reason", "Low confidence"))

        conf_str = f"{confidence:.2f}" if confidence is not None else "—"

        st.markdown(f"""
        <div class="review-item">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div style="font-weight:600;font-size:0.88rem">{title}</div>
                <div style="
                    font-family:'JetBrains Mono',monospace;
                    font-size:0.72rem;
                    color:#f59e0b;
                    background:rgba(245,158,11,0.1);
                    padding:0.15rem 0.5rem;
                    border-radius:4px;
                ">conf: {conf_str}</div>
            </div>
            <div style="font-size:0.75rem;color:#64748b;margin:0.35rem 0;">
                Escalated by: <b style="color:#94a3b8">{agent}</b>
            </div>
            <div style="font-size:0.78rem;color:#94a3b8;line-height:1.5;">
                {reason}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Score override form
    st.markdown("---")
    st.markdown("**Override a score** *(writes to rating_overrides.json)*")

    with st.form("override_form"):
        override_title = st.text_input("Scenario title (exact match)")
        col1, col2, col3 = st.columns(3)
        with col1:
            business_impact = st.slider("Business Impact", 1.0, 5.0, 3.0, 0.5)
            frequency       = st.slider("Frequency of Use", 1.0, 5.0, 3.0, 0.5)
        with col2:
            failure_prob    = st.slider("Failure Probability", 1.0, 5.0, 3.0, 0.5)
            dependency      = st.slider("Dependency Impact", 1.0, 5.0, 3.0, 0.5)
        with col3:
            assertion_spec  = st.slider("Assertion Specificity", 1.0, 5.0, 3.0, 0.5)
        override_reason = st.text_input("Reason for override")

        submitted = st.form_submit_button("Save Override")

    if submitted and override_title:
        _save_override(
            override_title,
            business_impact, frequency, failure_prob, dependency, assertion_spec,
            override_reason,
        )
        st.success(f"Override saved for: {override_title}")


def _save_override(title, impact, freq, prob, dep, assertion, reason):
    overrides_path = PROJECT_ROOT / "human_review" / "rating_overrides.json"
    overrides_path.parent.mkdir(exist_ok=True)

    try:
        existing = json.loads(overrides_path.read_text(encoding="utf-8")) if overrides_path.exists() else []
    except (json.JSONDecodeError, OSError):
        existing = []

    # Remove any existing override for the same title
    existing = [o for o in existing if o.get("title") != title]

    existing.append({
        "title": title,
        "scores": {
            "business_impact":      impact,
            "frequency_of_use":     freq,
            "failure_probability":  prob,
            "dependency_impact":    dep,
            "assertion_specificity": assertion,
        },
        "reason": reason or "SDET manual override",
    })

    overrides_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")