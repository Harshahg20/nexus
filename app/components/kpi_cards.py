import streamlit as st
from services.snowflake import load_supplier_failure_impact


def render():
    impact = load_supplier_failure_impact()
    if not impact:
        st.warning("No scenario impact data available.")
        return

    cols = st.columns(6)

    kpis = [
        ("Revenue Exposure", f"${impact.get('REVENUE_EXPOSURE', 0):,.0f}", "Total modeled revenue at risk"),
        ("Orders at Risk", f"{impact.get('ORDERS_AT_RISK', 0)}", "Open orders with modeled shortages"),
        ("Affected Parts", f"{impact.get('AFFECTED_PARTS', 0)}", "Parts with unmet demand"),
        ("Customers Exposed", f"{impact.get('CUSTOMERS_EXPOSED', 0)}", "Distinct customers affected"),
        ("Affected Plants", f"{impact.get('AFFECTED_PLANTS', 0)}", "Manufacturing sites impacted"),
        ("Units at Risk", f"{impact.get('UNITS_AT_RISK', 0):,.0f}", "Product units with shortages"),
    ]

    for col, (label, value, help_text) in zip(cols, kpis):
        with col:
            st.markdown(
                f"""<div style="background:#1a1a2e; border:1px solid #2a2a4a; border-radius:8px;
                    padding:20px 16px; text-align:center;">
                    <div style="color:#8892b0; font-size:0.75rem; text-transform:uppercase;
                        letter-spacing:0.1em; margin-bottom:8px;">{label}</div>
                    <div style="color:#e6f1ff; font-size:1.8rem; font-weight:700;
                        line-height:1.2;">{value}</div>
                </div>""",
                unsafe_allow_html=True,
                help=help_text,
            )
