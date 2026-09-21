from __future__ import annotations
import streamlit as st
import streamlit.components.v1 as components
from services.snowflake import (
    load_supplier_failure_chain,
    load_supplier_failure_parameters,
    is_unsupported_scenario,
)
from ui.theme import FONT

# ── Per-node color config ─────────────────────────────────────────────────────
_N = {
    "supplier": {"color": "#DC2626", "border": "rgba(220,38,38,0.28)", "bg": "rgba(220,38,38,0.04)"},
    "parts":    {"color": "#EA580C", "border": "rgba(234,88,12,0.25)",  "bg": "rgba(234,88,12,0.04)"},
    "plants":   {"color": "#D97706", "border": "rgba(217,119,6,0.25)",  "bg": "rgba(217,119,6,0.04)"},
    "products": {"color": "#7C3AED", "border": "rgba(124,58,237,0.25)", "bg": "rgba(124,58,237,0.04)"},
    "orders":   {"color": "#2563EB", "border": "rgba(37,99,235,0.25)",  "bg": "rgba(37,99,235,0.04)"},
    "customers":{"color": "#0891B2", "border": "rgba(8,145,178,0.25)",  "bg": "rgba(8,145,178,0.04)"},
}

_CRIT  = {"CRITICAL": "#DC2626", "HIGH": "#EA580C", "MEDIUM": "#D97706"}
_SLA   = {"PLATINUM": "#00C49A", "GOLD": "#D97706", "SILVER": "#64748B"}
_STEPS = ["supplier","parts","plants","products","orders","customers"]


def _rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    return f"{int(h[:2],16)},{int(h[2:4],16)},{int(h[4:6],16)}"


def _tag(text: str, color: str) -> str:
    r = _rgb(color)
    return (
        f'<span class="tag" style="display:inline-block;padding:3px 10px;border-radius:6px;'
        f'font-size:0.71rem;font-weight:600;margin:3px 3px 0 0;'
        f'background:rgba({r},0.09);border:1px solid rgba({r},0.22);color:{color};">'
        f'{text}</span>'
    )


def _connector(from_color: str, to_color: str, idx: int) -> str:
    """Animated SVG connector: line draws itself, then a dot travels along it, loops."""
    gid   = f"cg{idx}"
    dur   = 0.55                      # time to draw the line (s)
    delay = 0.45 + idx * 0.80         # stagger per step (s)
    dot_begin = f"{delay + dur - 0.05}s"  # dot starts just as line finishes
    H = 44                             # connector height px

    return f"""
    <div style="height:{H}px;display:flex;align-items:center;
                justify-content:center;position:relative;">
      <svg width="32" height="{H}" viewBox="0 0 32 {H}"
           style="overflow:visible;position:absolute;left:50%;transform:translateX(-50%);">
        <defs>
          <linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stop-color="{from_color}" stop-opacity="0.9"/>
            <stop offset="100%" stop-color="{to_color}"   stop-opacity="0.7"/>
          </linearGradient>
        </defs>

        <!-- Dashed flowing background line (loops) -->
        <line x1="16" y1="0" x2="16" y2="{H}"
              stroke="url(#{gid})" stroke-width="1.5" fill="none"
              stroke-dasharray="5 5" stroke-dashoffset="0"
              opacity="0.25"
              style="animation:dashflow 0.8s linear {delay}s infinite;"/>

        <!-- Solid draw-in line (one shot) -->
        <line x1="16" y1="0" x2="16" y2="{H}"
              stroke="url(#{gid})" stroke-width="2" fill="none"
              stroke-linecap="round"
              stroke-dasharray="{H}" stroke-dashoffset="{H}"
              style="animation:drawConn {dur}s cubic-bezier(.4,0,.2,1) {delay}s forwards;"/>

        <!-- Traveling dot along connector -->
        <circle r="3.5" fill="{from_color}" opacity="0.9">
          <animateMotion dur="0.6s" begin="{dot_begin}" repeatCount="indefinite"
                         path="M16 0 L16 {H}"/>
          <animate attributeName="opacity" values="0;1;1;0" dur="0.6s"
                   begin="{dot_begin}" repeatCount="indefinite"/>
        </circle>

        <!-- Arrowhead chevron -->
        <path d="M11 {H-9} L16 {H-2} L21 {H-9}"
              fill="none" stroke="{to_color}" stroke-width="1.8"
              stroke-linecap="round" stroke-linejoin="round"
              opacity="0"
              style="animation:fadeIn 0.2s ease {delay+dur}s forwards;"/>
      </svg>
    </div>"""


def _node(kind: str, step: int, total: int, heading: str, body_html: str,
          is_first: bool = False) -> str:
    n     = _N[kind]
    delay = 0.1 + step * 0.80   # stagger per step (s)
    pulse = (
        f'<span style="position:absolute;left:-9px;top:50%;transform:translateY(-50%);'
        f'width:12px;height:12px;border-radius:50%;'
        f'background:rgba({_rgb(n["color"])},0.25);'
        f'animation:ripple 1.6s ease-out {delay+0.4}s infinite;'
        f'display:block;"></span>'
    ) if is_first else ""

    return f"""
    <div class="cascade-node" style="position:relative;background:#ffffff;
                border:1px solid {n['border']};
                border-left:3px solid {n['color']};
                border-radius:0 14px 14px 0;
                opacity:0;
                animation:nodeIn 0.45s cubic-bezier(.4,0,.2,1) {delay}s forwards;">
      {pulse}
      <div class="node-inner" style="padding:16px 20px;
                box-shadow:0 2px 12px rgba(0,0,0,0.07);
                border-radius:0 14px 14px 0;">
        <!-- Step badge -->
        <div class="step-badge" style="position:absolute;top:10px;right:14px;font-size:0.57rem;
                    font-weight:700;text-transform:uppercase;letter-spacing:0.1em;
                    color:{n['color']};opacity:0.5;">
          Step {step+1} / {total}
        </div>
        <!-- Label -->
        <div class="node-label" style="font-size:0.6rem;font-weight:700;text-transform:uppercase;
                    letter-spacing:0.14em;color:{n['color']};margin-bottom:9px;">
          {heading}
        </div>
        {body_html}
      </div>
    </div>"""


def render():
    params = load_supplier_failure_parameters()

    # Detect unsupported scenario parameters before rendering the graph
    if params:
        unsupported, guidance = is_unsupported_scenario(params)
        if unsupported:
            st.warning(
                "⚠ **Unsupported scenario — cascade graph will be empty.**\n\n"
                + guidance
            )

    chain  = load_supplier_failure_chain()
    if chain.empty:
        st.info(
            "No cascade-chain data is available for the active scenario. "
            "If the scenario parameters are unsupported (see banner above), "
            "update them in Snowflake to match the seeded configuration. "
            "Otherwise check the Snowflake connection or verify that "
            "`NEXUS_DB.SCENARIOS.V_SUPPLIER_FAILURE_CHAIN` returns rows."
        )
        return

    sid  = params.get("FAILED_SUPPLIER_ID", "SUP-001")
    name = chain["SUPPLIER_NAME"].iloc[0]

    parts     = chain[["PART_ID","PART_NAME","CRITICALITY"]].drop_duplicates().sort_values("CRITICALITY")
    plants    = chain[["PLANT_ID","PLANT_NAME"]].drop_duplicates()
    products  = chain[["PRODUCT_ID","PRODUCT_NAME"]].drop_duplicates()
    customers = chain[["CUSTOMER_ID","CUSTOMER_NAME","SLA_TIER"]].drop_duplicates()
    n_orders  = chain["ORDER_ID"].nunique()
    revenue   = chain[["ORDER_ID","AT_RISK_REVENUE"]].drop_duplicates("ORDER_ID")["AT_RISK_REVENUE"].sum()
    total_steps = len(_STEPS)

    # ── Build node HTML bodies ────────────────────────────────────────────────
    body_supplier = (
        f'<div style="font-size:1rem;font-weight:800;color:#0F172A;'
        f'margin-bottom:3px;letter-spacing:-0.01em;">{sid}</div>'
        f'<div style="font-size:0.8rem;color:#94A3B8;">{name}</div>'
    )

    part_tags     = "".join(_tag(f"{r['PART_NAME']} · {r['CRITICALITY']}", _CRIT.get(str(r['CRITICALITY']).upper(),"#64748B")) for _,r in parts.iterrows())
    plant_tags    = "".join(_tag(r["PLANT_NAME"], "#D97706") for _,r in plants.iterrows())
    product_tags  = "".join(_tag(r["PRODUCT_NAME"], "#7C3AED") for _,r in products.iterrows())
    customer_tags = "".join(_tag(f"{r['CUSTOMER_NAME']} · {r['SLA_TIER']}", _SLA.get(str(r['SLA_TIER']).upper(),"#64748B")) for _,r in customers.iterrows())

    body_orders = (
        f'<div class="node-metric" style="font-size:1.55rem;font-weight:800;color:#DC2626;'
        f'letter-spacing:-0.03em;margin-bottom:3px;">${revenue:,.0f}</div>'
        f'<div class="node-sub" style="font-size:0.78rem;color:#94A3B8;">'
        f'modeled revenue exposure across {n_orders} orders</div>'
    )

    nodes = [
        ("supplier", "⚠  Failed Supplier",                  body_supplier,                                                        True),
        ("parts",    f"Affected Parts ({len(parts)})",       f'<div style="display:flex;flex-wrap:wrap;">{part_tags}</div>',        False),
        ("plants",   f"Affected Plants ({len(plants)} sites)",f'<div style="display:flex;flex-wrap:wrap;">{plant_tags}</div>',       False),
        ("products", f"Affected Products ({len(products)})",  f'<div style="display:flex;flex-wrap:wrap;">{product_tags}</div>',     False),
        ("orders",   f"Orders at Risk ({n_orders})",          body_orders,                                                          False),
        ("customers",f"Customers Exposed ({len(customers)})", f'<div style="display:flex;flex-wrap:wrap;">{customer_tags}</div>',    False),
    ]

    # ── Build interleaved node + connector HTML ───────────────────────────────
    body = ""
    for i, (kind, heading, body_html, is_first) in enumerate(nodes):
        body += _node(kind, i, total_steps, heading, body_html, is_first)
        if i < len(nodes) - 1:
            body += _connector(_N[kind]["color"], _N[_STEPS[i+1]]["color"], i)

    # Estimate height: 6 nodes @ ~110px + 5 connectors @ ~44px + tag rows
    tag_rows = (max(len(parts), len(plants), len(products), len(customers)) // 3) * 28
    height   = 860 + tag_rows

    components.html(
        f"""<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<!--
  Source: NEXUS_DB.SCENARIOS.V_SUPPLIER_FAILURE_CHAIN
  Scope : Full disruption cascade — supplier → parts → plants → products → orders → customers
  Type  : Observed data + scenario engine output (modeled cascade propagation)
-->
<style>
* {{ box-sizing:border-box; margin:0; padding:0; font-family:{FONT}; }}
body {{ background:transparent; padding:4px 0 12px; }}

/* Node entrance */
@keyframes nodeIn {{
    from {{ opacity:0; transform:translateX(-14px); }}
    to   {{ opacity:1; transform:translateX(0); }}
}}

/* Connector draw */
@keyframes drawConn {{
    to {{ stroke-dashoffset:0; }}
}}

/* Dashed flow loop */
@keyframes dashflow {{
    to {{ stroke-dashoffset:-10; }}
}}

/* Arrowhead / badge fade */
@keyframes fadeIn {{
    from {{ opacity:0; }}
    to   {{ opacity:1; }}
}}

/* Pulse ripple behind supplier circle */
@keyframes ripple {{
    0%   {{ transform:translateY(-50%) scale(1);   opacity:0.6; }}
    100% {{ transform:translateY(-50%) scale(2.8); opacity:0; }}
}}

/* Subtle card hover (desktop only) */
@media (hover: hover) {{
  .cascade-node:hover {{
    box-shadow: 0 6px 20px rgba(0,0,0,0.1) !important;
    transform: translateX(3px) !important;
  }}
}}
.cascade-node {{
  transition: box-shadow 0.2s ease, transform 0.18s ease;
  cursor: default;
}}

/* ── Responsive node sizing ─────────────────────────────────── */
.cascade-wrap {{ max-width: 680px; margin: 0 auto; padding: 0 4px; }}

/* Tablet */
@media (max-width: 900px) {{
  .cascade-wrap {{ max-width: 560px; }}
}}
/* Mobile landscape */
@media (max-width: 640px) {{
  .cascade-wrap {{ max-width: 100%; padding: 0 2px; }}
  .node-inner {{ padding: 12px 14px !important; }}
  .step-badge {{ font-size: 0.5rem !important; }}
  .node-label {{ font-size: 0.55rem !important; margin-bottom: 6px !important; }}
  .tag {{ font-size: 0.65rem !important; padding: 2px 7px !important; margin: 2px !important; }}
  .node-metric {{ font-size: 1.25rem !important; }}
  .node-sub {{ font-size: 0.7rem !important; }}
}}
/* Mobile portrait */
@media (max-width: 400px) {{
  .node-inner {{ padding: 10px 12px !important; }}
  .tag {{ font-size: 0.6rem !important; padding: 2px 6px !important; }}
}}
</style>
</head>
<body>
  <div class="cascade-wrap">
    {body}
  </div>
</body></html>""",
        height=height,
        scrolling=False,
    )
    st.caption(
        "Source: `NEXUS_DB.SCENARIOS.V_SUPPLIER_FAILURE_CHAIN` · "
        "Cascade propagation is deterministic — observed supplier data joined with "
        "the scenario engine. Revenue figure is a modeled exposure, not a confirmed loss."
    )
