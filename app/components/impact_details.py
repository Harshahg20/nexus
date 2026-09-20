import streamlit as st
from services.snowflake import load_supplier_failure_chain


def render():
    chain = load_supplier_failure_chain()
    if chain.empty:
        st.info("No impact detail data available.")
        return

    with st.expander("Affected Parts", expanded=False):
        parts = (
            chain.groupby(["PART_ID", "PART_NAME", "CRITICALITY"])
            .agg(ORDERS_AFFECTED=("ORDER_ID", "nunique"), TOTAL_AT_RISK_REVENUE=("AT_RISK_REVENUE", "sum"))
            .reset_index()
            .sort_values("TOTAL_AT_RISK_REVENUE", ascending=False)
        )
        st.dataframe(
            parts.rename(columns={
                "PART_ID": "Part", "PART_NAME": "Name", "CRITICALITY": "Criticality",
                "ORDERS_AFFECTED": "Orders", "TOTAL_AT_RISK_REVENUE": "At-Risk Revenue",
            }),
            use_container_width=True, hide_index=True,
        )

    with st.expander("Affected Plants", expanded=False):
        plants = (
            chain.groupby(["PLANT_ID", "PLANT_NAME"])
            .agg(ORDERS_AFFECTED=("ORDER_ID", "nunique"), TOTAL_AT_RISK_REVENUE=("AT_RISK_REVENUE", "sum"))
            .reset_index()
            .sort_values("TOTAL_AT_RISK_REVENUE", ascending=False)
        )
        st.dataframe(
            plants.rename(columns={
                "PLANT_ID": "Plant", "PLANT_NAME": "Name",
                "ORDERS_AFFECTED": "Orders", "TOTAL_AT_RISK_REVENUE": "At-Risk Revenue",
            }),
            use_container_width=True, hide_index=True,
        )

    with st.expander("Affected Orders", expanded=False):
        orders = (
            chain[["ORDER_ID", "CUSTOMER_NAME", "PRODUCT_NAME", "PLANT_NAME",
                   "AT_RISK_QUANTITY", "AT_RISK_REVENUE", "PRIORITY", "SLA_TIER"]]
            .drop_duplicates(subset=["ORDER_ID"])
            .sort_values("AT_RISK_REVENUE", ascending=False)
        )
        st.dataframe(
            orders.rename(columns={
                "ORDER_ID": "Order", "CUSTOMER_NAME": "Customer", "PRODUCT_NAME": "Product",
                "PLANT_NAME": "Plant", "AT_RISK_QUANTITY": "At-Risk Qty",
                "AT_RISK_REVENUE": "At-Risk Revenue", "PRIORITY": "Priority", "SLA_TIER": "SLA",
            }),
            use_container_width=True, hide_index=True,
        )

    with st.expander("Affected Customers", expanded=False):
        customers = (
            chain.groupby(["CUSTOMER_ID", "CUSTOMER_NAME", "SLA_TIER"])
            .agg(ORDERS_AFFECTED=("ORDER_ID", "nunique"), TOTAL_AT_RISK_REVENUE=("AT_RISK_REVENUE", "sum"))
            .reset_index()
            .sort_values("TOTAL_AT_RISK_REVENUE", ascending=False)
        )
        st.dataframe(
            customers.rename(columns={
                "CUSTOMER_ID": "Customer ID", "CUSTOMER_NAME": "Customer", "SLA_TIER": "SLA",
                "ORDERS_AFFECTED": "Orders", "TOTAL_AT_RISK_REVENUE": "At-Risk Revenue",
            }),
            use_container_width=True, hide_index=True,
        )
