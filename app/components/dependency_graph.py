import streamlit as st
import pandas as pd
from services.snowflake import load_supplier_failure_chain, load_supplier_failure_parameters


def render():
    params = load_supplier_failure_parameters()
    chain = load_supplier_failure_chain()
    if chain.empty:
        st.info("No dependency chain data available.")
        return

    supplier_id = params.get("FAILED_SUPPLIER_ID", "SUP-001")

    parts = chain[["PART_ID", "PART_NAME", "CRITICALITY"]].drop_duplicates().sort_values("CRITICALITY")
    plants = chain[["PLANT_ID", "PLANT_NAME"]].drop_duplicates()
    products = chain[["PRODUCT_ID", "PRODUCT_NAME"]].drop_duplicates()
    orders = chain[["ORDER_ID", "CUSTOMER_NAME", "AT_RISK_REVENUE", "PRIORITY"]].drop_duplicates()
    customers = chain[["CUSTOMER_ID", "CUSTOMER_NAME", "SLA_TIER"]].drop_duplicates()

    arrow = "↓"
    node_style = (
        "background:#1a1a2e; border:1px solid #2a2a4a; border-radius:8px; "
        "padding:14px 18px; margin:4px 0; text-align:center;"
    )
    arrow_style = "text-align:center; color:#4a5568; font-size:1.4rem; line-height:1.6;"
    label_style = "color:#8892b0; font-size:0.65rem; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:4px;"
    value_style = "color:#e6f1ff; font-size:0.95rem; font-weight:600;"
    tag_style = (
        "display:inline-block; background:#2a2a4a; color:#ccd6f6; border-radius:4px; "
        "padding:2px 8px; margin:2px; font-size:0.78rem;"
    )

    col_left, col_mid, col_right = st.columns([1, 2, 1])

    with col_mid:
        # Supplier node
        st.markdown(
            f'<div style="{node_style} border-color:#e74c3c;">'
            f'<div style="{label_style}">Failed Supplier</div>'
            f'<div style="{value_style}">{supplier_id}</div>'
            f'<div style="color:#a8b2d1; font-size:0.8rem;">{chain["SUPPLIER_NAME"].iloc[0] if not chain.empty else ""}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
        st.markdown(f'<div style="{arrow_style}">{arrow}</div>', unsafe_allow_html=True)

        # Parts node
        part_tags = "".join(
            f'<span style="{tag_style}">{r["PART_NAME"]} ({r["CRITICALITY"]})</span>'
            for _, r in parts.iterrows()
        )
        st.markdown(
            f'<div style="{node_style}">'
            f'<div style="{label_style}">Affected Parts ({len(parts)})</div>'
            f'<div style="margin-top:6px;">{part_tags}</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(f'<div style="{arrow_style}">{arrow}</div>', unsafe_allow_html=True)

        # Plants node
        plant_tags = "".join(
            f'<span style="{tag_style}">{r["PLANT_NAME"]}</span>' for _, r in plants.iterrows()
        )
        st.markdown(
            f'<div style="{node_style}">'
            f'<div style="{label_style}">Affected Plants ({len(plants)})</div>'
            f'<div style="margin-top:6px;">{plant_tags}</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(f'<div style="{arrow_style}">{arrow}</div>', unsafe_allow_html=True)

        # Products node
        prod_tags = "".join(
            f'<span style="{tag_style}">{r["PRODUCT_NAME"]}</span>' for _, r in products.iterrows()
        )
        st.markdown(
            f'<div style="{node_style}">'
            f'<div style="{label_style}">Affected Products ({len(products)})</div>'
            f'<div style="margin-top:6px;">{prod_tags}</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(f'<div style="{arrow_style}">{arrow}</div>', unsafe_allow_html=True)

        # Orders node
        order_count = orders["ORDER_ID"].nunique()
        total_risk = orders["AT_RISK_REVENUE"].sum()
        st.markdown(
            f'<div style="{node_style}">'
            f'<div style="{label_style}">Orders at Risk ({order_count})</div>'
            f'<div style="{value_style}">${total_risk:,.0f} revenue exposure</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(f'<div style="{arrow_style}">{arrow}</div>', unsafe_allow_html=True)

        # Customers node
        cust_tags = "".join(
            f'<span style="{tag_style}">{r["CUSTOMER_NAME"]} ({r["SLA_TIER"]})</span>'
            for _, r in customers.iterrows()
        )
        st.markdown(
            f'<div style="{node_style}">'
            f'<div style="{label_style}">Customers Exposed ({len(customers)})</div>'
            f'<div style="margin-top:6px;">{cust_tags}</div></div>',
            unsafe_allow_html=True,
        )
