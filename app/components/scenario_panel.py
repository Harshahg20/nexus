import streamlit as st
import streamlit.components.v1 as components
from services.snowflake import (
    load_supplier_failure_parameters,
    load_supplier_failure_impact,
    is_unsupported_scenario,
)
from ui.theme import C, FONT


# Plain-English descriptions for each scenario type
_SCENARIO_DESCRIPTIONS = {
    "SUPPLIER_FAILURE": (
        "A key supplier loses production capacity, creating a parts shortage that cascades "
        "through your manufacturing network — from plants, to products, to customer orders."
    ),
    "PORT_DISRUPTION": (
        "A major port closure blocks inbound shipments, delaying parts delivery across the "
        "manufacturing network and exposing open orders to fulfillment risk."
    ),
    "FREIGHT_SHOCK": (
        "A sudden spike in freight costs raises landed cost for all inbound parts, "
        "compressing margins and potentially making some orders economically unviable."
    ),
}


def render():
    params = load_supplier_failure_parameters()
    if not params:
        st.info(
            "No active scenario is configured. "
            "Check `NEXUS_DB.SCENARIOS.V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS` for data."
        )
        return

    # Detect unsupported scenario parameters before rendering impact data
    unsupported, guidance = is_unsupported_scenario(params)
    if unsupported:
        st.warning(
            "⚠ **Unsupported scenario parameters detected.**\n\n"
            + guidance
        )

    supplier = params.get("FAILED_SUPPLIER_ID", "—")
    capacity = params.get("CAPACITY_REDUCTION_PCT", 0)
    duration = params.get("DURATION_DAYS", 0)
    start    = str(params.get("START_DATE", "—"))

    if capacity >= 100:
        color, bg, border, label = "#DC2626", "rgba(220,38,38,0.07)", "rgba(220,38,38,0.25)", "CRITICAL"
    elif capacity >= 50:
        color, bg, border, label = "#EA580C", "rgba(234,88,12,0.07)", "rgba(234,88,12,0.25)", "HIGH"
    else:
        color, bg, border, label = "#D97706", "rgba(217,119,6,0.07)", "rgba(217,119,6,0.25)", "MEDIUM"

    def param(lbl, val, val_color="#0F172A"):
        return f"""
        <div class="param-item" style="display:flex;flex-direction:column;gap:2px;min-width:0;">
          <div style="font-size:0.58rem;font-weight:700;text-transform:uppercase;
                      letter-spacing:0.1em;color:#94A3B8;white-space:nowrap;">{lbl}</div>
          <div style="font-size:0.88rem;font-weight:700;color:{val_color};
                      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{val}</div>
        </div>"""

    sep = '<div class="sep" style="width:1px;height:32px;background:#E2E8F0;align-self:center;flex-shrink:0;"></div>'

    banner = f"""
    <div class="banner" style="display:flex;align-items:center;flex-wrap:wrap;gap:14px 20px;
                padding:14px 20px;background:#ffffff;
                border:1px solid #E2E8F0;border-left:3px solid {color};
                border-radius:0 14px 14px 0;
                box-shadow:0 1px 3px rgba(0,0,0,0.07);margin-bottom:6px;">

      <!-- Severity pill -->
      <div style="display:inline-flex;align-items:center;gap:7px;flex-shrink:0;
                  padding:5px 14px;background:{bg};
                  border:1px solid {border};border-radius:100px;">
        <span style="width:7px;height:7px;border-radius:50%;background:{color};
                     display:inline-block;flex-shrink:0;
                     animation:rp 1.5s ease infinite;"></span>
        <span style="font-size:0.6rem;font-weight:700;text-transform:uppercase;
                     letter-spacing:0.12em;color:{color};white-space:nowrap;">
          {label} &mdash; Active Scenario
        </span>
      </div>

      <!-- Separator (hidden on mobile) -->
      {sep}

      <!-- Param group: scenario + supplier -->
      <div class="param-group" style="display:flex;align-items:center;gap:14px 20px;flex-wrap:wrap;">
        {param("Scenario Type",   "Supplier Failure")}
        {sep}
        {param("Supplier ID",     supplier, color)}
        {sep}
        {param("Capacity Impact", f"{capacity:.0f}% reduction")}
        {sep}
        {param("Duration",        f"{duration} days")}
        {sep}
        {param("Start Date",      start)}
      </div>

    </div>"""

    components.html(
        f"""<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
* {{ box-sizing:border-box; font-family:{FONT}; margin:0; padding:0; }}
body {{ background:transparent; padding:0; }}
@keyframes rp {{
  0%,100% {{ box-shadow:0 0 0 0 rgba(220,38,38,.5); }}
  50%      {{ box-shadow:0 0 0 5px rgba(220,38,38,0); }}
}}
/* Tablet/mobile: hide vertical separators to prevent overflow */
@media (max-width: 768px) {{
  .sep {{ display: none !important; }}
  .banner {{ gap: 10px 14px !important; padding: 12px 16px !important; }}
}}
/* Mobile portrait: tighter */
@media (max-width: 480px) {{
  .banner {{ padding: 10px 14px !important; border-radius: 0 10px 10px 0 !important; }}
  .param-item div:last-child {{ font-size: 0.82rem !important; }}
}}
</style>
</head>
<body>
{banner}
</body></html>""",
        height=110,
    )
    st.caption(
        f"Scenario assumptions — Supplier **{supplier}** · "
        f"capacity reduced by **{capacity:.0f}%** · "
        f"duration **{duration} days** · starting **{start}**. "
        "All downstream impact figures are computed deterministically by the Snowflake "
        "scenario engine using these parameters."
    )

    # ── Before / After Comparison ─────────────────────────────────────────────
    _impact = load_supplier_failure_impact()
    _rev    = _impact.get("REVENUE_EXPOSURE", 0) or 0
    _ords   = _impact.get("ORDERS_AT_RISK", 0) or 0
    _custs  = _impact.get("CUSTOMERS_EXPOSED", 0) or 0
    _parts  = _impact.get("AFFECTED_PARTS", 0) or 0
    _rev_fmt = f"${_rev/1_000_000:.2f}M" if _rev else "—"

    cmp_html = f"""
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;
                margin:10px 0 4px;font-family:{FONT};">
      <!-- BEFORE column -->
      <div style="background:#F8FAFC;border:1px solid #E2E8F0;
                  border-radius:12px;padding:14px 18px;">
        <div style="font-size:0.6rem;font-weight:700;text-transform:uppercase;
                    letter-spacing:0.12em;color:#94A3B8;margin-bottom:10px;">
          &#9664; Baseline &mdash; Pre-Disruption
        </div>
        <div style="display:flex;flex-direction:column;gap:9px;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.75rem;color:#64748B;">Revenue at Risk</span>
            <span style="font-size:0.78rem;font-weight:700;color:#16A34A;">$0</span>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.75rem;color:#64748B;">Orders Disrupted</span>
            <span style="font-size:0.78rem;font-weight:700;color:#16A34A;">0</span>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.75rem;color:#64748B;">Customers Affected</span>
            <span style="font-size:0.78rem;font-weight:700;color:#16A34A;">0</span>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.75rem;color:#64748B;">Parts With Shortage</span>
            <span style="font-size:0.78rem;font-weight:700;color:#16A34A;">0</span>
          </div>
        </div>
      </div>
      <!-- AFTER column -->
      <div style="background:rgba(220,38,38,0.03);
                  border:1px solid rgba(220,38,38,0.18);
                  border-radius:12px;padding:14px 18px;">
        <div style="font-size:0.6rem;font-weight:700;text-transform:uppercase;
                    letter-spacing:0.12em;color:{color};margin-bottom:10px;">
          &#9654; With Disruption &mdash; Active Scenario
        </div>
        <div style="display:flex;flex-direction:column;gap:9px;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.75rem;color:#64748B;">Revenue at Risk</span>
            <span style="font-size:0.78rem;font-weight:700;color:#DC2626;">{_rev_fmt}</span>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.75rem;color:#64748B;">Orders Disrupted</span>
            <span style="font-size:0.78rem;font-weight:700;color:#EA580C;">{_ords}</span>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.75rem;color:#64748B;">Customers Affected</span>
            <span style="font-size:0.78rem;font-weight:700;color:#EA580C;">{_custs}</span>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:0.75rem;color:#64748B;">Parts With Shortage</span>
            <span style="font-size:0.78rem;font-weight:700;color:#EA580C;">{_parts}</span>
          </div>
        </div>
      </div>
    </div>
    """
    components.html(
        f"""<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<style>
* {{ box-sizing:border-box; margin:0; padding:0; }}
@media (max-width:480px) {{
  div[style*="grid-template-columns:1fr 1fr"] {{ grid-template-columns:1fr !important; }}
}}
</style>
</head>
<body style="background:transparent;padding:0;">{cmp_html}</body></html>""",
        height=172,
    )

    # ── Plain-English explanation ─────────────────────────────────────────────
    with st.expander("ℹ️ What does this scenario mean? (plain-English explanation)", expanded=False):
        loss_desc = "total loss of supply" if capacity >= 100 else f"{capacity:.0f}% reduction in supply output"
        st.markdown(
            f"""**Supplier {supplier}** is a critical node in your manufacturing supply network.
This scenario models a **{loss_desc}** lasting **{duration} days**, starting **{start}**.

**What happens in the supply chain:**
1. **Parts shortage** — {supplier} cannot fulfill purchase orders for the parts it supplies
2. **Plant impact** — Manufacturing sites that depend on those parts cannot run full production
3. **Product shortage** — Finished goods that use the affected parts cannot be built on schedule
4. **Order disruption** — Customer orders for those products face partial or full fulfillment failures
5. **Revenue exposure** — Unfulfilled orders translate directly to **{_rev_fmt}** of at-risk revenue

**Why NEXUS models it this way:**
The Snowflake Scenario Engine traces every edge of the supply graph — from {supplier}'s qualified parts,
through each plant's BOM, to every customer order — and runs a deterministic priority-based allocation
to calculate *exactly* which orders are short, by how much, and which customers are affected.

**For non-experts:** Think of this as a domino effect. {supplier} is the first domino.
NEXUS shows you every domino that falls as a result — before it happens in real life.
            """
        )
