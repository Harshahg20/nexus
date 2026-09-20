import streamlit as st
from services.snowflake import load_supplier_failure_chain
from ui.theme import C, FONT


def render():
    chain = load_supplier_failure_chain()
    if chain.empty:
        st.info("No impact detail data available.")
        return

    parts_df = (
        chain.groupby(["PART_ID", "PART_NAME", "CRITICALITY"])
        .agg(ORDERS_AFFECTED=("ORDER_ID", "nunique"), TOTAL_AT_RISK_REVENUE=("AT_RISK_REVENUE", "sum"))
        .reset_index()
        .sort_values("TOTAL_AT_RISK_REVENUE", ascending=False)
    )
    plants_df = (
        chain.groupby(["PLANT_ID", "PLANT_NAME"])
        .agg(ORDERS_AFFECTED=("ORDER_ID", "nunique"), TOTAL_AT_RISK_REVENUE=("AT_RISK_REVENUE", "sum"))
        .reset_index()
        .sort_values("TOTAL_AT_RISK_REVENUE", ascending=False)
    )
    orders_df = (
        chain[["ORDER_ID", "CUSTOMER_NAME", "PRODUCT_NAME", "PLANT_NAME",
               "AT_RISK_QUANTITY", "AT_RISK_REVENUE", "PRIORITY", "SLA_TIER"]]
        .drop_duplicates(subset=["ORDER_ID"])
        .sort_values("AT_RISK_REVENUE", ascending=False)
    )
    customers_df = (
        chain.groupby(["CUSTOMER_ID", "CUSTOMER_NAME", "SLA_TIER"])
        .agg(ORDERS_AFFECTED=("ORDER_ID", "nunique"), TOTAL_AT_RISK_REVENUE=("AT_RISK_REVENUE", "sum"))
        .reset_index()
        .sort_values("TOTAL_AT_RISK_REVENUE", ascending=False)
    )

    with st.expander(
        f"▸  Affected Parts — {len(parts_df)} parts with unmet demand", expanded=False
    ):
        st.dataframe(
            parts_df.rename(columns={
                "PART_ID": "Part ID", "PART_NAME": "Part Name", "CRITICALITY": "Criticality",
                "ORDERS_AFFECTED": "Orders Affected", "TOTAL_AT_RISK_REVENUE": "At-Risk Revenue ($)",
            }),
            use_container_width=True, hide_index=True,
        )

    with st.expander(
        f"▸  Affected Plants — {len(plants_df)} manufacturing sites impacted", expanded=False
    ):
        st.dataframe(
            plants_df.rename(columns={
                "PLANT_ID": "Plant ID", "PLANT_NAME": "Plant Name",
                "ORDERS_AFFECTED": "Orders Affected", "TOTAL_AT_RISK_REVENUE": "At-Risk Revenue ($)",
            }),
            use_container_width=True, hide_index=True,
        )

    with st.expander(
        f"▸  Affected Orders — {len(orders_df)} open orders with shortage risk", expanded=False
    ):
        st.dataframe(
            orders_df.rename(columns={
                "ORDER_ID": "Order ID", "CUSTOMER_NAME": "Customer",
                "PRODUCT_NAME": "Product", "PLANT_NAME": "Plant",
                "AT_RISK_QUANTITY": "At-Risk Qty", "AT_RISK_REVENUE": "At-Risk Revenue ($)",
                "PRIORITY": "Priority", "SLA_TIER": "SLA Tier",
            }),
            use_container_width=True, hide_index=True,
        )

    with st.expander(
        f"▸  Affected Customers — {len(customers_df)} buyers exposed", expanded=False
    ):
        st.dataframe(
            customers_df.rename(columns={
                "CUSTOMER_ID": "Customer ID", "CUSTOMER_NAME": "Customer Name",
                "SLA_TIER": "SLA Tier", "ORDERS_AFFECTED": "Orders Affected",
                "TOTAL_AT_RISK_REVENUE": "At-Risk Revenue ($)",
            }),
            use_container_width=True, hide_index=True,
        )
