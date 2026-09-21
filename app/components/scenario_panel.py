import streamlit as st
import streamlit.components.v1 as components
from services.snowflake import load_supplier_failure_parameters, is_unsupported_scenario
from ui.theme import C, FONT


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
