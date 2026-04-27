"""components/sidebar.py — Feature input + run controls"""

import streamlit as st


EXAMPLE_SPEC = """\
## Login Feature

As a registered user, I want to log in to the platform
so that I can access my account and perform actions.

### Acceptance Criteria
- User can log in with valid email and password
- User receives JWT token on success
- Invalid credentials return 401 with error message
- Blocked accounts cannot log in
- Password is case-sensitive
- Email is case-insensitive
- Successful login returns user profile data
- Refresh token is issued alongside access token
""".strip()


def render_sidebar(pipeline_state: dict) -> tuple[str, str, bool]:
    """
    Renders the sidebar and returns (feature_name, spec_text, run_clicked).
    """
    st.markdown("### ⚙️ Pipeline Config")

    status     = pipeline_state["status"]
    is_running = status == "running"

    # ── Required field styles ─────────────────────────────────────────────────
    st.markdown("""
    <style>
    .required-label {
        font-size: 0.85rem;
        font-weight: 600;
        color: #e2e8f0;
        margin-bottom: 0.25rem;
    }
    .required-label span.asterisk {
        color: #ef4444;
        margin-left: 3px;
        font-size: 0.9rem;
    }
    .field-error {
        color: #ef4444;
        font-size: 0.75rem;
        font-family: 'JetBrains Mono', monospace;
        margin-top: 0.2rem;
    }
    div[data-testid="stTextInput"] input:placeholder-shown {
        border-color: rgba(239,68,68,0.4) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Retrieve submitted state (for validation display) ─────────────────────
    submitted = st.session_state.get("_form_submitted", False)

    # ── Feature name field ────────────────────────────────────────────────────
    st.markdown(
        '<div class="required-label">Feature name <span class="asterisk">*</span></div>',
        unsafe_allow_html=True,
    )
    feature_name = st.text_input(
        label         = "feature_name_input",
        label_visibility = "collapsed",
        placeholder   = "e.g. login, checkout, search",
        disabled      = is_running,
        help          = "Used to name generated files e.g. LOGIN_FEATURES.md",
        key           = "feature_name_field",
    )

    # Show inline error if submitted with empty field
    if submitted and not feature_name.strip():
        st.markdown(
            '<div class="field-error">⚠ Feature Name is required</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top:0.75rem'></div>", unsafe_allow_html=True)

    # ── Feature spec field ────────────────────────────────────────────────────
    st.markdown(
        '<div class="required-label">Feature Spec <span class="asterisk">*</span></div>',
        unsafe_allow_html=True,
    )
    spec_text = st.text_area(
        label            = "spec_text_input",
        label_visibility = "collapsed",
        placeholder      = "Paste your feature spec or user stories here...",
        height           = 280,
        disabled         = is_running,
        key              = "spec_text_field",
    )

    if submitted and not spec_text.strip():
        st.markdown(
            '<div class="field-error">⚠ Feature spec is required</div>',
            unsafe_allow_html=True,
        )

    # ── Load example / Clear buttons ──────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Load example", disabled=is_running, use_container_width=True):
            st.session_state["feature_name_field"] = "login"
            st.session_state["spec_text_field"]    = EXAMPLE_SPEC
            st.session_state["_form_submitted"]    = False
            st.rerun()
    with col2:
        if st.button("Clear", disabled=is_running, use_container_width=True):
            st.session_state["feature_name_field"] = ""
            st.session_state["spec_text_field"]    = ""
            st.session_state["_form_submitted"]    = False
            st.rerun()

    st.markdown("---")

    # ── Action buttons ────────────────────────────────────────────────────────
    run_clicked = False

    if is_running:
        # ── Stop button ───────────────────────────────────────────────────────
        st.markdown("""
        <div style="
            background: rgba(0,217,255,0.05);
            border: 1px solid rgba(0,217,255,0.2);
            border-radius: 6px;
            padding: 0.6rem;
            text-align: center;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.78rem;
            color: #00d9ff;
            margin-bottom: 0.6rem;
        ">
            🔄 Pipeline running...
        </div>
        """, unsafe_allow_html=True)

        if st.button("⏹ Stop Pipeline", use_container_width=True, type="primary"):
            runner = st.session_state.get("runner")
            if runner:
                runner.stop()
            st.session_state.pipeline_state["status"] = "idle"
            st.session_state["_form_submitted"] = False
            st.rerun()

    elif status == "complete":
        st.success("✅ Pipeline complete!")
        if st.button("▶ Run again", use_container_width=True):
            st.session_state["_form_submitted"] = True
            run_clicked = True

    elif status == "failed":
        st.error("❌ Pipeline failed")
        if st.button("↺ Retry", use_container_width=True):
            st.session_state["_form_submitted"] = True
            run_clicked = True

    else:
        # ── Primary Run button ────────────────────────────────────────────────
        if st.button("▶  Run Pipeline", use_container_width=True, type="primary"):
            st.session_state["_form_submitted"] = True
            # Re-read values after marking submitted
            feature_name = st.session_state.get("feature_name_field", "").strip()
            spec_text    = st.session_state.get("spec_text_field", "").strip()
            if feature_name and spec_text:
                run_clicked = True
            else:
                st.rerun()  # rerun to show validation errors

    # ── Pipeline info ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.78rem; color:#64748b; line-height:1.7;">
    <b style="color:#94a3b8;">6 Agents</b><br>
    SpecAnalyst → GherkinAuthor<br>
    → RatingJudge → Enrichment<br>
    → ScriptForge → Orchestrator
    <br><br>
    <b style="color:#94a3b8;">Outputs</b><br>
    • Gherkin test cases<br>
    • Weighted risk scores<br>
    • Executable pytest scripts<br>
    • Decision audit logs
    </div>
    """, unsafe_allow_html=True)

    return feature_name, spec_text, run_clicked