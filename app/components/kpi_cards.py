"""
KPI strip — six headline metrics from V_SUPPLIER_FAILURE_IMPACT.

Metric scope (all from allocation engine, not full cascade chain):
  REVENUE_EXPOSURE   — sum of AT_RISK_REVENUE for orders with a supply deficit
  ORDERS_AT_RISK     — distinct orders where shortage allocation produced a deficit
  AFFECTED_PARTS     — distinct parts with unmet demand after allocation
  CUSTOMERS_EXPOSED  — distinct customers with at least one shortage-allocated order
  AFFECTED_PLANTS    — distinct manufacturing sites producing shortage-affected products
  UNITS_AT_RISK      — sum of unmet unit quantity across all shortage allocations
"""
import streamlit as st
from services.snowflake import (
    load_supplier_failure_impact,
    load_supplier_failure_parameters,
    is_unsupported_scenario,
)
from ui.theme import FONT
import streamlit.components.v1 as components


# Card accent colors
_ACCENTS = [
    "linear-gradient(90deg,#DC2626,#EA580C)",   # Revenue – red→orange
    "linear-gradient(90deg,#EA580C,#D97706)",   # Orders  – orange→amber
    "linear-gradient(90deg,#2563EB,#0891B2)",   # Parts   – blue→cyan
    "linear-gradient(90deg,#7C3AED,#2563EB)",   # Customers – purple→blue
    "linear-gradient(90deg,#00C49A,#0891B2)",   # Plants  – teal→cyan
    "linear-gradient(90deg,#94A3B8,#64748B)",   # Units   – slate
]
_VAL_COLORS = ["#DC2626", "#0F172A", "#0F172A", "#0F172A", "#0F172A", "#0F172A"]


def _card_html(label: str, value: str, sub: str, accent: str, val_color: str,
               val_font_size: str = "clamp(1.25rem,4vw,1.85rem)") -> str:
    return f"""<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ background:transparent; font-family:{FONT}; padding:2px 0; }}
.card {{
  background:#fff; border:1px solid #E2E8F0; border-radius:14px;
  overflow:hidden; height:100%;
  box-shadow:0 1px 3px rgba(0,0,0,.07),0 1px 2px rgba(0,0,0,.04);
  transition:box-shadow .2s,transform .18s;
}}
@media (hover:hover) {{
  .card:hover {{ box-shadow:0 4px 14px rgba(0,0,0,.1); transform:translateY(-2px); }}
}}
.bar  {{ height:3px; background:{accent}; }}
.body {{ padding:16px 16px 14px; }}
.lbl  {{ font-size:.6rem; font-weight:700; text-transform:uppercase;
         letter-spacing:.12em; color:#94A3B8; margin-bottom:8px;
         overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.val  {{ font-size:{val_font_size}; font-weight:800;
         color:{val_color}; letter-spacing:-.03em; line-height:1.1;
         margin-bottom:5px; }}
.sub  {{ font-size:.68rem; color:#CBD5E1;
         overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
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


def render():
    # Check for unsupported scenario before loading KPI data
    params = load_supplier_failure_parameters()
    if params:
        unsupported, guidance = is_unsupported_scenario(params)
        if unsupported:
            st.warning(
                "⚠ **Unsupported scenario — KPI data will be empty.**\n\n" + guidance
            )

        # ── Scenario active indicator ──────────────────────────────────────
        supplier = params.get("FAILED_SUPPLIER_ID", "—")
        capacity = float(params.get("CAPACITY_REDUCTION_PCT", 0) or 0)
        duration = int(params.get("DURATION_DAYS", 0) or 0)
        st.markdown(
            f"<div style='display:inline-flex;align-items:center;gap:8px;margin-bottom:14px;"
            f"padding:6px 16px;background:rgba(220,38,38,0.06);border:1px solid rgba(220,38,38,0.20);"
            f"border-radius:100px;font-family:{FONT};'>"
            f"<span style='width:7px;height:7px;border-radius:50%;background:#DC2626;"
            f"display:inline-block;flex-shrink:0;'></span>"
            f"<span style='font-size:0.65rem;font-weight:700;text-transform:uppercase;"
            f"letter-spacing:0.12em;color:#DC2626;'>"
            f"SCENARIO ACTIVE &mdash; {supplier} &middot; {capacity:.0f}% capacity loss"
            f" &middot; {duration}-day window</span></div>",
            unsafe_allow_html=True,
        )

    impact = load_supplier_failure_impact()
    if not impact:
        st.warning(
            "⚠ **Scenario impact data is unavailable.**  "
            "Check the Snowflake connection and verify that "
            "`NEXUS_DB.SCENARIOS.V_SUPPLIER_FAILURE_IMPACT` returns data."
        )
        return

    revenue   = impact.get("REVENUE_EXPOSURE", 0) or 0
    orders    = impact.get("ORDERS_AT_RISK", 0) or 0
    parts     = impact.get("AFFECTED_PARTS", 0) or 0
    customers = impact.get("CUSTOMERS_EXPOSED", 0) or 0
    plants    = impact.get("AFFECTED_PLANTS", 0) or 0
    units     = impact.get("UNITS_AT_RISK", 0) or 0

    # Revenue KPI is bright red if > $1M to signal severity
    rev_val_color = "#DC2626" if revenue > 1_000_000 else "#EA580C"

    # Sub-labels: clearly state "scenario-wide" scope so users understand
    # these totals include all shortage causes, not only SUP-001-caused shortages.
    metrics = [
        ("Revenue Exposure",   f"${revenue/1_000_000:.2f}M", "Scenario-wide shortage exposure"),
        ("Orders at Risk",     str(orders),                   "Orders with shortage — all causes"),
        ("Parts With Shortage",str(parts),                    "Parts with unmet demand — all causes"),
        ("Customers Exposed",  str(customers),                "Buyers with any shortage order"),
        ("Affected Plants",    str(plants),                   "Plants with at-risk orders"),
        ("Units at Risk",      f"{units:,.0f}",               "Unmet units across all orders"),
    ]
    accents    = _ACCENTS
    val_colors = [rev_val_color] + _VAL_COLORS[1:]

    # ── Layout: revenue card is wide (2/4), other two share row 1 ─────────
    col_rev, col_orders, col_parts = st.columns([2, 1, 1])
    col_cust, col_plants, col_units = st.columns([1, 1, 1])
    all_cols = [col_rev, col_orders, col_parts, col_cust, col_plants, col_units]

    for i, (col, (label, value, sub), accent, val_color) in enumerate(
        zip(all_cols, metrics, accents, val_colors)
    ):
        is_revenue = (i == 0)
        h = 150 if is_revenue else 118
        fsize = "clamp(1.7rem,5vw,2.5rem)" if is_revenue else "clamp(1.25rem,4vw,1.85rem)"
        with col:
            components.html(
                _card_html(label, value, sub, accent, val_color, val_font_size=fsize),
                height=h,
            )

    # Provenance caption: explain the scope difference up-front
    st.caption(
        "Source: `NEXUS_DB.SCENARIOS.V_SUPPLIER_FAILURE_IMPACT` · "
        "These totals reflect **all** open-order shortages under the active scenario, "
        "including pre-existing supply constraints unrelated to SUP-001. "
        "The cascade and impact sections below trace only shortages **caused by SUP-001**."
    )
