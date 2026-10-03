from __future__ import annotations
import streamlit as st
from ui.compat import st_dataframe
import streamlit.components.v1 as components
from services.snowflake import load_governed_metric_catalog
from ui.theme import C, FONT, FONT_MONO, SHADOW_SM

_OBSERVED = [
    ("Suppliers",  "NEXUS_DB.RAW.SUPPLIERS"),
    ("Parts",      "NEXUS_DB.RAW.PARTS"),
    ("Plants",     "NEXUS_DB.RAW.PLANTS"),
    ("Inventory",  "NEXUS_DB.RAW.INVENTORY"),
    ("Shipments",  "NEXUS_DB.RAW.SHIPMENTS"),
    ("Orders",     "NEXUS_DB.RAW.ORDERS"),
    ("Customers",  "NEXUS_DB.RAW.CUSTOMERS"),
]
_MODELED = [
    ("Supplier failure impact",  "NEXUS_DB.SCENARIOS.V_SUPPLIER_FAILURE_IMPACT"),
    ("Order-part allocation",    "NEXUS_DB.SCENARIOS.V_ORDER_PART_ALLOCATION"),
    ("Revenue exposure",         "NEXUS_DB.SCENARIOS.V_ORDER_IMPACT"),
    ("Mitigation comparison",    "NEXUS_DB.SCENARIOS.V_MITIGATION_COMPARISON"),
    ("Port disruption",          "NEXUS_DB.SCENARIOS.V_PORT_DISRUPTION_IMPACT"),
    ("Freight shock",            "NEXUS_DB.SCENARIOS.V_FREIGHT_SHOCK_SUMMARY"),
]


def _panel_html(title: str, rows: list[tuple[str,str]]) -> str:
    rows_html = "".join(
        f'<tr>'
        f'<td style="padding:9px 0;color:#64748B;font-size:0.82rem;border-bottom:1px solid #F1F5F9;'
        f'padding-right:20px;vertical-align:middle;white-space:nowrap;">{n}</td>'
        f'<td style="padding:9px 0;border-bottom:1px solid #F1F5F9;vertical-align:middle;">'
        f'<code style="color:#007A5E;background:rgba(0,196,154,0.07);'
        f'border:1px solid rgba(0,196,154,0.22);border-radius:5px;'
        f'padding:2px 8px;font-size:0.68rem;font-family:{FONT_MONO};">{s}</code>'
        f'</td></tr>'
        for n, s in rows
    )
    return (
        f'<div style="background:#ffffff;border:1px solid #E2E8F0;border-radius:14px;'
        f'padding:22px;box-shadow:0 1px 3px rgba(0,0,0,0.07);height:100%;">'
        f'<div style="font-size:0.62rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:0.16em;color:#CBD5E1;margin-bottom:16px;">{title}</div>'
        f'<table style="width:100%;border-collapse:collapse;">{rows_html}</table>'
        f'</div>'
    )


def render():
    obs_html = _panel_html("Observed / Governed Data", _OBSERVED)
    mod_html = _panel_html("Modeled Scenario Outputs",  _MODELED)

    components.html(
        f"""<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
* {{ box-sizing:border-box; font-family:{FONT}; margin:0; padding:0; }}
body {{ background:transparent; padding:0; }}
#egrid {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; padding:4px 0; }}
/* Mobile: stack vertically */
@media (max-width: 640px) {{
  #egrid {{ grid-template-columns: 1fr !important; gap: 10px; }}
}}
/* Mobile portrait: reduce padding inside panels */
@media (max-width: 480px) {{
  #egrid > div {{ padding: 16px !important; }}
  code {{ font-size: 0.6rem !important; padding: 2px 6px !important; }}
}}
/* Hover effect (desktop only) */
@media (hover: hover) {{
  #egrid > div:hover {{
    box-shadow: 0 4px 16px rgba(0,0,0,0.09) !important;
    border-color: #CBD5E1 !important;
    transition: box-shadow 0.2s ease, border-color 0.2s ease;
  }}
}}
</style>
</head>
<body>
<div id="egrid">
  {obs_html}
  {mod_html}
</div>
</body></html>""",
        height=320,
        scrolling=False,
    )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    with st.expander("◈  Governed Metric Definitions", expanded=False):
        catalog = load_governed_metric_catalog()
        if not catalog.empty:
            st_dataframe(
                catalog.rename(columns={
                    "METRIC_NAME": "Metric",
                    "DEFINITION":  "Definition",
                    "SOURCE_VIEW": "Source View",
                    }),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Metric catalog not available.")

    st.caption(
        "Scenario outputs are modelled decision-support results produced by deterministic "
        "priority-based order allocation. They are not operational guarantees. "
        "**Scope note:** `orders_at_risk`, `customers_exposed`, and `affected_parts` in the KPI strip "
        "count all shortages under the active scenario (all causes). "
        "The cascade and impact-detail sections trace only shortages caused by the failing supplier's "
        "qualified parts — counts will differ when pre-existing supply constraints are present."
    )
