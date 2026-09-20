import streamlit as st
from services.snowflake import load_supplier_failure_impact
from ui.theme import C, FONT
import streamlit.components.v1 as components


def render():
    impact = load_supplier_failure_impact()
    if not impact:
        st.warning("No scenario impact data available.")
        return

    revenue   = impact.get("REVENUE_EXPOSURE", 0)
    orders    = impact.get("ORDERS_AT_RISK", 0)
    parts     = impact.get("AFFECTED_PARTS", 0)
    customers = impact.get("CUSTOMERS_EXPOSED", 0)
    plants    = impact.get("AFFECTED_PLANTS", 0)
    units     = impact.get("UNITS_AT_RISK", 0)

    # ── Render via components.html so the accent bars are guaranteed ──────────
    # Each card: white card, colored top border, big number, label, sub-label
    def card(label, value, sub, accent, val_color="#0F172A"):
        return f"""
        <div style="background:#ffffff;border:1px solid #E2E8F0;border-radius:14px;
                    padding:0;overflow:hidden;
                    box-shadow:0 1px 3px rgba(0,0,0,0.07),0 1px 2px rgba(0,0,0,0.04);
                    transition:box-shadow .2s;height:100%;">
          <div style="height:3px;background:{accent};"></div>
          <div style="padding:18px 18px 16px;">
            <div style="font-size:0.62rem;font-weight:700;text-transform:uppercase;
                        letter-spacing:0.12em;color:#94A3B8;margin-bottom:10px;">{label}</div>
            <div style="font-size:1.9rem;font-weight:800;color:{val_color};
                        letter-spacing:-0.03em;line-height:1.1;margin-bottom:6px;">{value}</div>
            <div style="font-size:0.72rem;color:#CBD5E1;">{sub}</div>
          </div>
        </div>"""

    cards_html = f"""
    <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:12px;
                font-family:{FONT};">
      {card("Revenue Exposure",  f"${revenue/1_000_000:.2f}M", "Total at-risk revenue",
            "linear-gradient(90deg,#DC2626,#EA580C)", val_color="#DC2626")}
      {card("Orders at Risk",    str(orders),                 "Open orders w/ shortages",
            "linear-gradient(90deg,#EA580C,#D97706)")}
      {card("Affected Parts",    str(parts),                  "Parts with unmet demand",
            "linear-gradient(90deg,#2563EB,#0891B2)")}
      {card("Customers Exposed", str(customers),              "Distinct buyers impacted",
            "linear-gradient(90deg,#7C3AED,#2563EB)")}
      {card("Affected Plants",   str(plants),                 "Manufacturing sites hit",
            "linear-gradient(90deg,#00C49A,#0891B2)")}
      {card("Units at Risk",     f"{units:,.0f}",             "Product units w/ shortages",
            "linear-gradient(90deg,#94A3B8,#64748B)")}
    </div>"""

    components.html(
        f"<!DOCTYPE html><html><head><meta charset='UTF-8'></head>"
        f"<body style='margin:0;padding:0;background:transparent;'>"
        f"{cards_html}"
        f"</body></html>",
        height=120,
    )
