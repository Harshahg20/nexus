"""
NEXUS — Interactive Scenario Controls

Renders the sidebar controls that let users change scenario parameters in
real time.  When the user clicks "Apply Scenario", this module:

  1. Writes new values to NEXUS_DB.SCENARIOS.SCENARIO_PARAMS via a SQL MERGE
  2. Clears the Streamlit data cache so downstream views pick up new params
  3. Triggers a page rerun to reflect the updated data

SiS compatibility notes:
  - Uses st.selectbox, st.slider, st.button (all SiS-safe)
  - No st.pills, st.toggle, st.chat_input, hide_index
  - Uses st_rerun() and st_toast() from ui.compat
"""
from __future__ import annotations

import streamlit as st
from services.snowflake import (
    load_suppliers_list,
    load_ports_list,
    load_supplier_failure_parameters,
    load_port_disruption_parameters,
    update_supplier_failure_params,
    update_port_disruption_params,
    clear_scenario_cache,
    load_supplier_failure_impact,
    generate_executive_brief,
)
from ui.compat import st_rerun, st_toast
from ui.theme import C, FONT


def _fmt_supplier(row: dict) -> str:
    """Format a supplier row for display in the dropdown."""
    return f"{row.get('SUPPLIER_ID','?')} — {row.get('SUPPLIER_NAME','?')} ({row.get('RISK_TIER','?')} risk)"


def _fmt_port(row: dict) -> str:
    """Format a port row for display in the dropdown."""
    return f"{row.get('PORT_ID','?')} — {row.get('PORT_NAME','?')} ({row.get('PORT_REGION','?')})"


def render_sidebar() -> None:
    """
    Render the interactive scenario controls inside st.sidebar.
    Call this once from streamlit_app.py before any other sidebar content.
    """
    with st.sidebar:
        st.markdown(
            f"<div style='font-size:0.6rem;font-weight:700;text-transform:uppercase;"
            f"letter-spacing:0.14em;color:#94A3B8;margin-bottom:10px;font-family:{FONT};'>"
            f"🎛️ Scenario Controls</div>",
            unsafe_allow_html=True,
        )

        scenario_type = st.radio(
            "Scenario type",
            options=["Supplier Failure", "Port Disruption"],
            key="sb_scenario_type",
            horizontal=False,
            label_visibility="collapsed",
        )

        st.markdown("---")

        # ── Supplier Failure Controls ────────────────────────────────────────
        if scenario_type == "Supplier Failure":
            _render_supplier_controls()

        # ── Port Disruption Controls ─────────────────────────────────────────
        else:
            _render_port_controls()

        st.markdown("---")

        # ── AI Executive Brief ───────────────────────────────────────────────
        _render_executive_brief_button()


def _render_supplier_controls() -> None:
    """Render supplier failure parameter widgets."""
    # Load supplier list for dropdown
    suppliers_df = load_suppliers_list()
    current_params = load_supplier_failure_parameters()
    current_sid = current_params.get("FAILED_SUPPLIER_ID", "SUP-001") if current_params else "SUP-001"
    current_cap = float(current_params.get("CAPACITY_REDUCTION_PCT", 100) or 100) if current_params else 100.0
    current_dur = int(current_params.get("DURATION_DAYS", 14) or 14) if current_params else 14

    st.markdown(
        f"<div style='font-size:0.72rem;font-weight:700;color:#0F172A;"
        f"margin-bottom:8px;font-family:{FONT};'>⚠ Supplier Failure</div>",
        unsafe_allow_html=True,
    )

    # Supplier dropdown
    if not suppliers_df.empty:
        supplier_options = []
        for _, row in suppliers_df.iterrows():
            supplier_options.append(row.to_dict())

        option_labels = [_fmt_supplier(r) for r in supplier_options]
        supplier_ids  = [r.get("SUPPLIER_ID", "") for r in supplier_options]

        # Find current selection index
        default_idx = 0
        if current_sid in supplier_ids:
            default_idx = supplier_ids.index(current_sid)

        selected_label = st.selectbox(
            "Failed Supplier",
            options=option_labels,
            index=default_idx,
            key="sb_supplier_select",
        )
        selected_sid = supplier_ids[option_labels.index(selected_label)] if selected_label in option_labels else current_sid
    else:
        st.text_input("Supplier ID", value=current_sid, key="sb_supplier_text")
        selected_sid = st.session_state.get("sb_supplier_text", current_sid)

    # Capacity loss slider
    capacity_pct = st.slider(
        "Capacity Loss (%)",
        min_value=10,
        max_value=100,
        value=int(current_cap),
        step=10,
        key="sb_capacity_slider",
        help="Percentage of supplier capacity lost during the disruption window",
    )

    # Duration slider
    duration_days = st.slider(
        "Duration (days)",
        min_value=3,
        max_value=30,
        value=current_dur,
        step=1,
        key="sb_duration_slider",
        help="How many days the disruption lasts",
    )

    # Severity indicator
    if capacity_pct >= 100:
        sev_color, sev_label = "#DC2626", "CRITICAL"
    elif capacity_pct >= 50:
        sev_color, sev_label = "#EA580C", "HIGH"
    else:
        sev_color, sev_label = "#D97706", "MEDIUM"

    st.markdown(
        f"<div style='font-size:0.65rem;font-weight:700;color:{sev_color};"
        f"margin:4px 0 10px;font-family:{FONT};'>Severity: {sev_label}</div>",
        unsafe_allow_html=True,
    )

    # Check if params changed
    params_changed = (
        selected_sid != current_sid
        or abs(capacity_pct - current_cap) > 0.5
        or duration_days != current_dur
    )

    button_label = "▶ Apply Scenario" if params_changed else "✓ Scenario Applied"
    if st.button(button_label, key="sb_apply_supplier", use_container_width=True, type="primary"):
        with st.spinner("Applying scenario parameters…"):
            ok = update_supplier_failure_params(selected_sid, float(capacity_pct), duration_days)
        if ok:
            clear_scenario_cache()
            st_toast("✅ Scenario updated — refreshing data…")
            st_rerun()
        else:
            st.error("❌ Failed to update parameters. Check the Snowflake connection.")


def _render_port_controls() -> None:
    """Render port disruption parameter widgets."""
    ports_df = load_ports_list()
    current_params = load_port_disruption_parameters()
    current_port = current_params.get("DISRUPTED_PORT_ID", "PORT-TYO") if current_params else "PORT-TYO"
    current_dis   = float(current_params.get("DISRUPTION_PCT", 100) or 100) if current_params else 100.0
    current_dur   = int(current_params.get("DURATION_DAYS", 7) or 7) if current_params else 7

    st.markdown(
        f"<div style='font-size:0.72rem;font-weight:700;color:#0F172A;"
        f"margin-bottom:8px;font-family:{FONT};'>🚢 Port Disruption</div>",
        unsafe_allow_html=True,
    )

    if not ports_df.empty:
        port_options = []
        for _, row in ports_df.iterrows():
            port_options.append(row.to_dict())

        option_labels = [_fmt_port(r) for r in port_options]
        port_ids      = [r.get("PORT_ID", "") for r in port_options]

        default_idx = 0
        if current_port in port_ids:
            default_idx = port_ids.index(current_port)

        selected_label = st.selectbox(
            "Disrupted Port",
            options=option_labels,
            index=default_idx,
            key="sb_port_select",
        )
        selected_port = port_ids[option_labels.index(selected_label)] if selected_label in option_labels else current_port
    else:
        st.text_input("Port ID", value=current_port, key="sb_port_text")
        selected_port = st.session_state.get("sb_port_text", current_port)

    disruption_pct = st.slider(
        "Disruption Severity (%)",
        min_value=10,
        max_value=100,
        value=int(current_dis),
        step=10,
        key="sb_port_disruption_slider",
        help="Percentage of port throughput blocked",
    )

    duration_days = st.slider(
        "Duration (days)",
        min_value=1,
        max_value=21,
        value=current_dur,
        step=1,
        key="sb_port_duration_slider",
    )

    params_changed = (
        selected_port != current_port
        or abs(disruption_pct - current_dis) > 0.5
        or duration_days != current_dur
    )
    button_label = "▶ Apply Scenario" if params_changed else "✓ Scenario Applied"

    if st.button(button_label, key="sb_apply_port", use_container_width=True, type="primary"):
        with st.spinner("Applying port disruption parameters…"):
            ok = update_port_disruption_params(selected_port, float(disruption_pct), duration_days)
        if ok:
            clear_scenario_cache()
            st_toast("✅ Port disruption scenario updated — refreshing…")
            st_rerun()
        else:
            st.error("❌ Failed to update parameters. Check the Snowflake connection.")


def _render_executive_brief_button() -> None:
    """Render the AI Executive Brief generation button."""
    st.markdown(
        f"<div style='font-size:0.6rem;font-weight:700;text-transform:uppercase;"
        f"letter-spacing:0.12em;color:#94A3B8;margin-bottom:8px;font-family:{FONT};'>"
        f"🤖 AI Analysis</div>",
        unsafe_allow_html=True,
    )

    if st.button("✨ Generate Executive Brief", key="sb_gen_brief", use_container_width=True):
        impact = load_supplier_failure_impact()
        params = load_supplier_failure_parameters()
        if impact and params:
            with st.spinner("Generating AI executive brief via Cortex…"):
                brief = generate_executive_brief(impact, params)
            if brief:
                # Store in session state so main body can display it
                st.session_state["exec_brief"] = brief
                st.session_state["exec_brief_fresh"] = True
                st_rerun()
            else:
                st.warning("Could not generate brief — Cortex unavailable.")
        else:
            st.info("Load scenario data first.")
