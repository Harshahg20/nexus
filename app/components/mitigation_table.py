import streamlit as st
import pandas as pd
from services.snowflake import load_mitigation_comparison


def render():
    df = load_mitigation_comparison()
    if df.empty:
        st.info("No mitigation data available.")
        return

    display_order = {"NO_ACTION": 0, "EXPEDITE_SHIPMENT": 1, "ALTERNATE_SUPPLIER": 2}
    df["_sort"] = df["MITIGATION_TYPE"].map(display_order).fillna(99)
    df = df.sort_values("_sort").drop(columns=["_sort"])

    friendly_names = {
        "NO_ACTION": "No Action",
        "EXPEDITE_SHIPMENT": "Expedite Shipment",
        "ALTERNATE_SUPPLIER": "Alternate Supplier",
    }

    cols = st.columns(len(df))
    for col, (_, row) in zip(cols, df.iterrows()):
        name = friendly_names.get(row["MITIGATION_TYPE"], row["MITIGATION_TYPE"])
        remaining = row.get("REMAINING_REVENUE_EXPOSURE", 0)
        protected = row.get("MODELED_REVENUE_PROTECTED", 0)
        cost = row.get("MODELED_INCREMENTAL_COST", 0)
        orders = row.get("ORDERS_AT_RISK", 0)
        customers = row.get("CUSTOMERS_EXPOSED", 0)

        with col:
            st.markdown(
                f"""<div style="background:#1a1a2e; border:1px solid #2a2a4a; border-radius:8px; padding:18px;">
                    <div style="color:#ccd6f6; font-size:1rem; font-weight:600; margin-bottom:14px;
                        text-align:center;">{name}</div>
                    <table style="width:100%; color:#a8b2d1; font-size:0.82rem;">
                        <tr><td style="padding:3px 0; color:#8892b0;">Orders at Risk</td>
                            <td style="text-align:right; color:#e6f1ff; font-weight:600;">{orders}</td></tr>
                        <tr><td style="padding:3px 0; color:#8892b0;">Customers Exposed</td>
                            <td style="text-align:right; color:#e6f1ff; font-weight:600;">{customers}</td></tr>
                        <tr><td style="padding:3px 0; color:#8892b0;">Remaining Exposure</td>
                            <td style="text-align:right; color:#e6f1ff; font-weight:600;">${remaining:,.0f}</td></tr>
                        <tr><td style="padding:3px 0; color:#8892b0;">Revenue Protected</td>
                            <td style="text-align:right; color:#e6f1ff; font-weight:600;">${protected:,.0f}</td></tr>
                        <tr><td style="padding:3px 0; color:#8892b0;">Modeled Cost</td>
                            <td style="text-align:right; color:#e6f1ff; font-weight:600;">${cost:,.0f}</td></tr>
                    </table>
                </div>""",
                unsafe_allow_html=True,
            )

    st.caption(
        "Deterministic modeled outcome using explicit part capacity and priority-based "
        "order allocation. Not an operational execution guarantee. Compare modeled tradeoffs "
        "to inform planning decisions."
    )
