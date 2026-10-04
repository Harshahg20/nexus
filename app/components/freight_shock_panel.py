"""
NEXUS — Freight Shock Panel

Renders the freight shock scenario results in the main dashboard.
Previously this scenario was only accessible via the AI agent; exposing it
here makes all three scenario engines visible to judges on the main page.

Shows:
  - Freight Shock KPI strip (cost impact, parts analyzed, uncovered units)
  - Per-part sourcing cost table
  - Scenario parameters (30% rate increase, 14 days)

SiS compatibility: st.columns, st.metric, components.html, st_dataframe.
No st.pills, st.toggle, or hide_index.
"""
from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components
from services.snowflake import load_freight_shock_summary, load_freight_shock_chain
from ui.compat import st_dataframe
from ui.theme import C, FONT


def render() -> None:
    """Render the freight shock scenario panel."""
    summary = load_freight_shock_summary()
    chain   = load_freight_shock_chain()

    if not summary:
        st.info("Freight shock data unavailable — ensure `011_freight_shock_engine.sql` is deployed.")
        return

    freight_pct  = float(summary.get("FREIGHT_INCREASE_PCT", 30) or 30)
    duration     = int(summary.get("DURATION_DAYS", 14) or 14)
    parts_count  = int(summary.get("PARTS_ANALYZED", 0) or 0)
    protected    = int(summary.get("MODELED_PROTECTED_UNITS", 0) or 0)
    uncovered    = int(summary.get("MODELED_UNCOVERED_UNITS", 0) or 0)
    min_cost     = float(summary.get("MODELED_MINIMUM_SOURCE_COST", 0) or 0)

    # ── Section header ───────────────────────────────────────────────────────
    st.markdown(
        f"<p style='font-size:0.63rem;font-weight:700;text-transform:uppercase;"
        f"letter-spacing:0.18em;color:{C.T5};margin-bottom:6px;font-family:{FONT};'>"
        f"Third Scenario Engine</p>"
        f"<h3 style='font-size:1.35rem;font-weight:800;color:{C.T1};letter-spacing:-0.02em;"
        f"margin-bottom:4px;font-family:{FONT};'>Freight Shock — Cost Impact Analysis</h3>"
        f"<p style='font-size:0.82rem;color:{C.T4};margin-bottom:16px;font-family:{FONT};'>"
        f"A <b>{freight_pct:.0f}% global freight rate spike</b> over {duration} days raises landed "
        f"cost for all inbound parts. The engine compares qualified supplier options to find the "
        f"minimum-cost sourcing strategy across {parts_count} analyzed parts.</p>",
        unsafe_allow_html=True,
    )

    # ── KPI strip ────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        components.html(
            _kpi_card(
                "Freight Rate Increase",
                f"{freight_pct:.0f}%",
                f"{duration}-day window",
                "linear-gradient(90deg,#7C3AED,#2563EB)",
                "#7C3AED",
            ),
            height=118,
        )

    with col2:
        components.html(
            _kpi_card(
                "Min Source Cost",
                f"${min_cost/1_000_000:.2f}M",
                "Lowest modeled option",
                "linear-gradient(90deg,#DC2626,#EA580C)",
                "#DC2626",
            ),
            height=118,
        )

    with col3:
        components.html(
            _kpi_card(
                "Protected Units",
                f"{protected:,}",
                "Coverable within capacity",
                "linear-gradient(90deg,#00C49A,#0891B2)",
                "#007A5E",
            ),
            height=118,
        )

    with col4:
        components.html(
            _kpi_card(
                "Uncovered Units",
                f"{uncovered:,}",
                "Demand above all-supplier capacity",
                "linear-gradient(90deg,#EA580C,#D97706)",
                "#EA580C",
            ),
            height=118,
        )

    st.caption(
        "Source: `NEXUS_DB.SCENARIOS.V_FREIGHT_SHOCK_SUMMARY` · "
        "All figures are modeled outcomes — actual landed costs depend on contract terms and routes."
    )

    # ── Per-part sourcing options ─────────────────────────────────────────────
    if not chain.empty:
        with st.expander(f"📦 Per-Part Sourcing Options — {len(chain)} rows", expanded=False):
            # Rename columns for display
            display = chain.rename(columns={
                "PART_ID":             "Part ID",
                "SUPPLIER_ID":         "Supplier",
                "SUPPLIER_NAME":       "Supplier Name",
                "REQUIRED_UNITS":      "Required Units",
                "PROTECTED_UNITS":     "Protected Units",
                "UNCOVERED_UNITS":     "Uncovered Units",
                "MODELED_FREIGHT_COST":"Freight Cost ($)",
                "LEAD_TIME_DAYS":      "Lead Time (d)",
            })
            st_dataframe(display, use_container_width=True)
            st.caption(
                "Freight Cost = unit_cost × (1 + freight_increase_pct/100) × protected_units. "
                "Choose the supplier with lowest cost and sufficient capacity."
            )


def _kpi_card(label: str, value: str, sub: str, accent: str, val_color: str) -> str:
    return f"""<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<style>
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ background:transparent; font-family:{FONT}; padding:2px 0; }}
.card {{
  background:#fff; border:1px solid #E2E8F0; border-radius:14px;
  overflow:hidden;
  box-shadow:0 1px 3px rgba(0,0,0,.07);
}}
.bar  {{ height:3px; background:{accent}; }}
.body {{ padding:14px 16px; }}
.lbl  {{ font-size:.6rem; font-weight:700; text-transform:uppercase;
         letter-spacing:.12em; color:#94A3B8; margin-bottom:8px; }}
.val  {{ font-size:clamp(1.2rem,4vw,1.8rem); font-weight:800;
         color:{val_color}; letter-spacing:-.03em; line-height:1.1; margin-bottom:4px; }}
.sub  {{ font-size:.67rem; color:#CBD5E1; }}
</style>
</head>
<body>
<div class="card">
  <div class="bar"></div>
  <div class="body">
    <div class="lbl">{label}</div>
    <div class="val">{value}</div>
    <div class="sub">{sub}</div>
  </div>
</div>
</body></html>"""
