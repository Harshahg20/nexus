"""
NEXUS — Multi-Scenario Comparison Panel

Side-by-side comparison of the supplier failure, port disruption, and freight
shock scenarios so judges and operators can immediately answer:
  "What's worse — SUP-001 failure OR PORT-TYO closure?"

Design:
  - Three scenario columns: Supplier Failure | Port Disruption | Freight Shock
  - Four comparison rows: Revenue at Risk | Orders | Customers | Duration
  - Colour-coded "worst" indicator per row
  - No third-party chart libraries — pure HTML + Streamlit columns

SiS compatibility: uses components.html, st.columns, st.metric.
No st.pills, st.toggle, or hide_index.
"""
from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components
from services.snowflake import (
    load_supplier_failure_impact,
    load_supplier_failure_parameters,
    load_port_disruption_impact,
    load_port_disruption_parameters,
    load_freight_shock_summary,
)
from ui.theme import C, FONT


def _bar_width(value: float, max_val: float) -> int:
    """Return a bar width percentage (5–100%) relative to max_val."""
    if max_val <= 0:
        return 5
    return max(5, min(100, int(100 * value / max_val)))


def render() -> None:
    """Render the three-scenario comparison panel."""

    # ── Load data from all three scenario engines ────────────────────────────
    sf_impact  = load_supplier_failure_impact()
    sf_params  = load_supplier_failure_parameters()
    port_impact = load_port_disruption_impact()
    port_params = load_port_disruption_parameters()
    freight     = load_freight_shock_summary()

    # Supplier Failure values
    sf_rev      = float(sf_impact.get("REVENUE_EXPOSURE", 0) or 0)
    sf_orders   = int(sf_impact.get("ORDERS_AT_RISK", 0) or 0)
    sf_custs    = int(sf_impact.get("CUSTOMERS_EXPOSED", 0) or 0)
    sf_dur      = int(sf_params.get("DURATION_DAYS", 14) or 14) if sf_params else 14
    sf_sup      = sf_params.get("FAILED_SUPPLIER_ID", "SUP-001") if sf_params else "SUP-001"
    sf_cap      = float(sf_params.get("CAPACITY_REDUCTION_PCT", 100) or 100) if sf_params else 100

    # Port Disruption values
    pd_rev      = float(port_impact.get("REVENUE_EXPOSURE", 0) or 0)
    pd_orders   = int(port_impact.get("ORDERS_AT_RISK", 0) or 0)
    pd_custs    = int(port_impact.get("CUSTOMERS_EXPOSED", 0) or 0)
    pd_dur      = int(port_params.get("DURATION_DAYS", 7) or 7) if port_params else 7
    pd_port     = port_params.get("DISRUPTED_PORT_ID", "PORT-TYO") if port_params else "PORT-TYO"

    # Freight Shock values
    fr_cost     = float(freight.get("MODELED_MINIMUM_SOURCE_COST", 0) or 0)
    fr_uncov    = int(freight.get("MODELED_UNCOVERED_UNITS", 0) or 0)
    fr_parts    = int(freight.get("PARTS_ANALYZED", 0) or 0)
    fr_dur      = int(freight.get("DURATION_DAYS", 14) or 14) if freight else 14

    # ── Section header ───────────────────────────────────────────────────────
    st.markdown(
        f"<p style='font-size:0.63rem;font-weight:700;text-transform:uppercase;"
        f"letter-spacing:0.18em;color:{C.T5};margin-bottom:6px;font-family:{FONT};'>"
        f"Scenario Intelligence</p>"
        f"<h3 style='font-size:1.35rem;font-weight:800;color:{C.T1};letter-spacing:-0.02em;"
        f"margin-bottom:4px;font-family:{FONT};'>Multi-Scenario Impact Comparison</h3>"
        f"<p style='font-size:0.82rem;color:{C.T4};margin-bottom:16px;font-family:{FONT};'>"
        f"Side-by-side view of all three disruption scenarios — instantly see which "
        f"event creates the greatest business exposure.</p>",
        unsafe_allow_html=True,
    )

    # ── Build comparison HTML ─────────────────────────────────────────────────
    max_rev     = max(sf_rev, pd_rev, fr_cost, 1)
    max_orders  = max(sf_orders, pd_orders, 1)
    max_custs   = max(sf_custs, pd_custs, 1)

    def _worst_color(a: float, b: float, c: float, mine: float) -> str:
        """Return red if this value is the worst (highest), else default."""
        return "#DC2626" if mine == max(a, b, c) else "#0F172A"

    def _metric_row(label: str, sf_val: str, pd_val: str, fr_val: str,
                    sf_num: float, pd_num: float, fr_num: float) -> str:
        sf_c  = _worst_color(sf_num, pd_num, fr_num, sf_num)
        pd_c  = _worst_color(sf_num, pd_num, fr_num, pd_num)
        fr_c  = _worst_color(sf_num, pd_num, fr_num, fr_num)
        max_n = max(sf_num, pd_num, fr_num, 1)
        sf_w  = _bar_width(sf_num, max_n)
        pd_w  = _bar_width(pd_num, max_n)
        fr_w  = _bar_width(fr_num, max_n)

        def cell(val: str, color: str, bar_w: int) -> str:
            return f"""
            <td style="padding:10px 14px;border-bottom:1px solid #F1F5F9;vertical-align:middle;">
              <div style="font-size:0.88rem;font-weight:700;color:{color};
                          margin-bottom:5px;">{val}</div>
              <div style="height:4px;background:#F1F5F9;border-radius:2px;width:100%;">
                <div style="height:4px;background:{color};border-radius:2px;
                            width:{bar_w}%;opacity:0.7;"></div>
              </div>
            </td>"""

        return f"""
        <tr>
          <td style="padding:10px 14px;border-bottom:1px solid #F1F5F9;
                     font-size:0.72rem;font-weight:600;color:#64748B;
                     white-space:nowrap;vertical-align:middle;">{label}</td>
          {cell(sf_val,  sf_c,  sf_w)}
          {cell(pd_val,  pd_c,  pd_w)}
          {cell(fr_val,  fr_c,  fr_w)}
        </tr>"""

    table_html = f"""
    <table style="width:100%;border-collapse:collapse;font-family:{FONT};
                  background:#fff;border:1px solid #E2E8F0;border-radius:14px;
                  overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.06);">
      <thead>
        <tr>
          <th style="padding:12px 14px;background:#F8FAFC;border-bottom:2px solid #E2E8F0;
                     font-size:0.65rem;font-weight:700;text-transform:uppercase;
                     letter-spacing:0.12em;color:#94A3B8;text-align:left;">Metric</th>
          <th style="padding:12px 14px;background:rgba(220,38,38,0.04);
                     border-bottom:2px solid rgba(220,38,38,0.18);
                     font-size:0.65rem;font-weight:700;text-transform:uppercase;
                     letter-spacing:0.1em;color:#DC2626;text-align:left;">
            ⚠ Supplier Failure<br>
            <span style="font-size:0.58rem;font-weight:600;color:#94A3B8;text-transform:none;">
              {sf_sup} · {sf_cap:.0f}% loss · {sf_dur}d
            </span>
          </th>
          <th style="padding:12px 14px;background:rgba(37,99,235,0.04);
                     border-bottom:2px solid rgba(37,99,235,0.18);
                     font-size:0.65rem;font-weight:700;text-transform:uppercase;
                     letter-spacing:0.1em;color:#2563EB;text-align:left;">
            🚢 Port Disruption<br>
            <span style="font-size:0.58rem;font-weight:600;color:#94A3B8;text-transform:none;">
              {pd_port} · {pd_dur}d closure
            </span>
          </th>
          <th style="padding:12px 14px;background:rgba(124,58,237,0.04);
                     border-bottom:2px solid rgba(124,58,237,0.18);
                     font-size:0.65rem;font-weight:700;text-transform:uppercase;
                     letter-spacing:0.1em;color:#7C3AED;text-align:left;">
            📦 Freight Shock<br>
            <span style="font-size:0.58rem;font-weight:600;color:#94A3B8;text-transform:none;">
              30% rate increase · {fr_dur}d
            </span>
          </th>
        </tr>
      </thead>
      <tbody>
        {_metric_row(
            "Revenue / Cost Impact",
            f"${sf_rev/1_000_000:.2f}M at risk",
            f"${pd_rev/1_000_000:.2f}M at risk",
            f"${fr_cost/1_000_000:.2f}M min cost",
            sf_rev, pd_rev, fr_cost,
        )}
        {_metric_row(
            "Orders Disrupted",
            str(sf_orders),
            str(pd_orders),
            f"{fr_parts} parts analyzed",
            float(sf_orders), float(pd_orders), float(fr_parts),
        )}
        {_metric_row(
            "Customers / Units Exposed",
            f"{sf_custs} customers",
            f"{pd_custs} customers",
            f"{fr_uncov:,} uncovered units",
            float(sf_custs), float(pd_custs), float(fr_uncov / 100),
        )}
        {_metric_row(
            "Disruption Window",
            f"{sf_dur} days",
            f"{pd_dur} days",
            f"{fr_dur} days",
            float(sf_dur), float(pd_dur), float(fr_dur),
        )}
      </tbody>
    </table>"""

    components.html(
        f"""<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ background:transparent; }}
table {{ border-spacing:0; }}
@media (max-width:640px) {{
  th:nth-child(4), td:nth-child(4) {{ display:none; }}
}}
</style>
</head>
<body>{table_html}</body></html>""",
        height=280,
    )

    st.caption(
        "🔴 Red values indicate the highest exposure in each category across all three scenarios. "
        "All figures are deterministic modeled outputs from the NEXUS Scenario Engine — "
        "not operational guarantees."
    )
