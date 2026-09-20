from __future__ import annotations
import streamlit as st
import streamlit.components.v1 as components
from services.snowflake import load_mitigation_comparison
from ui.theme import FONT


_CFG = {
    "NO_ACTION": {
        "name": "No Action",       "icon": "⚠",
        "grad": "linear-gradient(90deg,#DC2626,#EA580C)",
        "color": "#DC2626", "bg": "rgba(220,38,38,0.04)", "border": "rgba(220,38,38,0.18)",
        "desc": "Baseline — absorb the full disruption impact.",
        "best": False,
    },
    "EXPEDITE_SHIPMENT": {
        "name": "Expedite Shipment","icon": "⚡",
        "grad": "linear-gradient(90deg,#EA580C,#D97706)",
        "color": "#EA580C", "bg": "rgba(234,88,12,0.04)", "border": "rgba(234,88,12,0.18)",
        "desc": "Rush inventory to narrow the shortage window.",
        "best": False,
    },
    "ALTERNATE_SUPPLIER": {
        "name": "Alternate Supplier","icon": "✓",
        "grad": "linear-gradient(90deg,#16A34A,#00C49A)",
        "color": "#16A34A", "bg": "rgba(22,163,74,0.04)", "border": "rgba(22,163,74,0.2)",
        "desc": "Re-source from secondary supplier — highest recovery.",
        "best": True,
    },
}


def _val(v: str, color: str = "#0F172A") -> str:
    return f'<span style="font-size:0.9rem;font-weight:700;color:{color};">{v}</span>'


def _row(lbl: str, val_html: str, last: bool = False) -> str:
    border = "" if last else "border-bottom:1px solid #F1F5F9;"
    return (
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'padding:7px 0;{border}">'
        f'<span style="font-size:0.78rem;color:#94A3B8;">{lbl}</span>'
        f'{val_html}</div>'
    )


def render():
    df = load_mitigation_comparison()
    if df.empty:
        st.info("No mitigation data available.")
        return

    order_map = {"NO_ACTION": 0, "EXPEDITE_SHIPMENT": 1, "ALTERNATE_SUPPLIER": 2}
    df["_s"] = df["MITIGATION_TYPE"].map(order_map).fillna(99)
    df = df.sort_values("_s").drop(columns=["_s"])

    max_prot = max(df["MODELED_REVENUE_PROTECTED"].max() if "MODELED_REVENUE_PROTECTED" in df.columns else 1, 1)

    cards_html = ""
    for _, row in df.iterrows():
        key  = row["MITIGATION_TYPE"]
        cfg  = _CFG.get(key, _CFG["NO_ACTION"])
        rem  = row.get("REMAINING_REVENUE_EXPOSURE", 0)
        prot = row.get("MODELED_REVENUE_PROTECTED", 0)
        cost = row.get("MODELED_INCREMENTAL_COST", 0)
        ords = row.get("ORDERS_AT_RISK", 0)
        custs= row.get("CUSTOMERS_EXPOSED", 0)
        pct  = int((prot / max_prot) * 100) if max_prot else 0

        best_badge = (
            f'<span style="font-size:0.58rem;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:0.1em;color:#16A34A;background:rgba(22,163,74,0.08);'
            f'border:1px solid rgba(22,163,74,0.22);border-radius:100px;'
            f'padding:2px 8px;margin-left:8px;vertical-align:middle;">RECOMMENDED</span>'
            if cfg["best"] else ""
        )

        cards_html += f"""
        <div style="background:#ffffff;border:1px solid {cfg['border']};border-radius:16px;
                    overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.06);
                    display:flex;flex-direction:column;">
          <div style="height:3px;background:{cfg['grad']};"></div>
          <div style="padding:20px;flex:1;display:flex;flex-direction:column;">
            <div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:14px;">
              <span style="font-size:1.4rem;line-height:1;flex-shrink:0;">{cfg['icon']}</span>
              <div>
                <div style="font-size:1rem;font-weight:800;color:#0F172A;line-height:1.2;">
                  {cfg['name']}{best_badge}
                </div>
                <div style="font-size:0.72rem;color:#94A3B8;margin-top:3px;line-height:1.5;">
                  {cfg['desc']}
                </div>
              </div>
            </div>
            <div style="height:1px;background:#F1F5F9;margin-bottom:4px;"></div>
            {_row("Orders at Risk",     _val(str(ords)))}
            {_row("Customers Exposed",  _val(str(custs)))}
            {_row("Remaining Exposure", _val(f"${rem:,.0f}", "#DC2626" if rem > 0 else "#16A34A"))}
            {_row("Revenue Recovered",  _val(f"${prot:,.0f}", "#16A34A" if prot > 0 else "#94A3B8"))}
            {_row("Incremental Cost",   _val(f"${cost:,.0f}", "#EA580C" if cost > 0 else "#94A3B8"), last=True)}
            <div style="margin-top:14px;">
              <div style="height:4px;border-radius:2px;background:#F1F5F9;overflow:hidden;">
                <div style="height:100%;width:{pct}%;background:{cfg['grad']};border-radius:2px;"></div>
              </div>
              <div style="font-size:0.65rem;color:#CBD5E1;margin-top:5px;">
                Revenue recovery &nbsp;·&nbsp; {pct}%
              </div>
            </div>
          </div>
        </div>"""

    components.html(
        f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
        <style>
        * {{ box-sizing:border-box; font-family:{FONT}; margin:0; padding:0; }}
        body {{ background:transparent; padding:0; }}
        </style></head>
        <body>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;padding:4px 0;">
          {cards_html}
        </div>
        </body></html>""",
        height=410,
        scrolling=False,
    )

    st.caption(
        "Deterministic modeled outcomes using priority-based order allocation. "
        "Not an operational execution guarantee — use to inform, not execute."
    )
