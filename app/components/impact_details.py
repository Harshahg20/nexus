"""
Impact Details — drill-down into the full disruption cascade.

Source: NEXUS_DB.SCENARIOS.V_SUPPLIER_FAILURE_CHAIN (multi-row).

Scope note
----------
These counts are derived from the cascade-chain view, which traces ALL orders,
parts, plants, products, and customers that appear anywhere in the disruption
path — including those that may be only partially impacted.  The headline KPI
counts (top strip) come from the shortage-allocation engine and may be smaller,
because the allocation engine counts only entities where the deficit is confirmed.
Both scopes are intentional; see the Evidence section for governed definitions.
"""
import streamlit as st
from services.snowflake import (
    load_supplier_failure_chain,
    load_supplier_failure_parameters,
    is_unsupported_scenario,
)
from ui.theme import C, FONT

_SCOPE_NOTE = (
    "ℹ **Scope — SUP-001 causal trace only.** "
    "Counts below come from `V_SUPPLIER_FAILURE_CHAIN`, which restricts to "
    "parts in SUP-001's qualified sourcing portfolio. "
    "Headline KPI numbers include **all** shortage-affected orders and parts "
    "under the active scenario — including pre-existing supply constraints "
    "unrelated to SUP-001. Both scopes are intentional and correct."
)


def render():
    # Detect unsupported scenario parameters early
    params = load_supplier_failure_parameters()
    if params:
        unsupported, guidance = is_unsupported_scenario(params)
        if unsupported:
            st.warning(
                "⚠ **Unsupported scenario — cascade detail will be empty.**\n\n"
                + guidance
            )

    chain = load_supplier_failure_chain()
    if chain.empty:
        st.info(
            "No cascade-chain data is available for the active scenario. "
            "If the scenario parameters are unsupported (see banner above), "
            "update them to match the seeded configuration. "
            "Otherwise check the Snowflake connection or verify that "
            "`NEXUS_DB.SCENARIOS.V_SUPPLIER_FAILURE_CHAIN` returns rows."
        )
        return

    # ── Aggregate by entity ───────────────────────────────────────────────────
    parts_df = (
        chain.groupby(["PART_ID", "PART_NAME", "CRITICALITY"])
        .agg(
            ORDERS_IN_CHAIN=("ORDER_ID", "nunique"),
            TOTAL_AT_RISK_REVENUE=("AT_RISK_REVENUE", "sum"),
        )
        .reset_index()
        .sort_values("TOTAL_AT_RISK_REVENUE", ascending=False)
    )
    plants_df = (
        chain.groupby(["PLANT_ID", "PLANT_NAME"])
        .agg(
            ORDERS_IN_CHAIN=("ORDER_ID", "nunique"),
            TOTAL_AT_RISK_REVENUE=("AT_RISK_REVENUE", "sum"),
        )
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
        .agg(
            ORDERS_IN_CHAIN=("ORDER_ID", "nunique"),
            TOTAL_AT_RISK_REVENUE=("AT_RISK_REVENUE", "sum"),
        )
        .reset_index()
        .sort_values("TOTAL_AT_RISK_REVENUE", ascending=False)
    )

    # ── Scope clarification ───────────────────────────────────────────────────
    st.info(_SCOPE_NOTE)

    # ── Expanders — labels use "in cascade chain" phrasing for clarity ────────
    with st.expander(
        f"▸  Parts in SUP-001 Cascade — {len(parts_df)} parts from SUP-001's portfolio with shortage",
        expanded=False,
    ):
        st.caption(
            "Parts qualified from SUP-001 that have a confirmed unmet demand "
            "in the active scenario. KPI 'Parts With Shortage' (top strip) is larger "
            "because it includes all parts with shortage, regardless of supplier."
        )
        st.dataframe(
            parts_df.rename(columns={
                "PART_ID":             "Part ID",
                "PART_NAME":           "Part Name",
                "CRITICALITY":         "Criticality",
                "ORDERS_IN_CHAIN":     "Orders in Chain",
                "TOTAL_AT_RISK_REVENUE": "At-Risk Revenue ($)",
            }),
            use_container_width=True,
            hide_index=True,
        )

    with st.expander(
        f"▸  Plants in Cascade — {len(plants_df)} manufacturing sites in the disruption path",
        expanded=False,
    ):
        st.caption(
            "Plants that produce shortage-affected products. "
            "Matches KPI 'Affected Plants'."
        )
        st.dataframe(
            plants_df.rename(columns={
                "PLANT_ID":            "Plant ID",
                "PLANT_NAME":          "Plant Name",
                "ORDERS_IN_CHAIN":     "Orders in Chain",
                "TOTAL_AT_RISK_REVENUE": "At-Risk Revenue ($)",
            }),
            use_container_width=True,
            hide_index=True,
        )

    with st.expander(
        f"▸  Orders in SUP-001 Cascade — {len(orders_df)} orders with a SUP-001 part shortage",
        expanded=False,
    ):
        st.caption(
            "Open orders that are at risk AND have at least one SUP-001 portfolio part with unmet demand. "
            "KPI 'Orders at Risk' (top strip) is larger because it counts all at-risk orders, "
            "including those whose shortage comes from parts unrelated to SUP-001."
        )
        st.dataframe(
            orders_df.rename(columns={
                "ORDER_ID":         "Order ID",
                "CUSTOMER_NAME":    "Customer",
                "PRODUCT_NAME":     "Product",
                "PLANT_NAME":       "Plant",
                "AT_RISK_QUANTITY": "At-Risk Qty",
                "AT_RISK_REVENUE":  "At-Risk Revenue ($)",
                "PRIORITY":         "Priority",
                "SLA_TIER":         "SLA Tier",
            }),
            use_container_width=True,
            hide_index=True,
        )

    with st.expander(
        f"▸  Customers in SUP-001 Cascade — {len(customers_df)} buyers with a SUP-001-linked shortage",
        expanded=False,
    ):
        st.caption(
            "Customers who have at least one order in the SUP-001 causal chain. "
            "KPI 'Customers Exposed' (top strip) may be larger if any customer's "
            "at-risk orders trace only to non-SUP-001 parts."
        )
        st.dataframe(
            customers_df.rename(columns={
                "CUSTOMER_ID":         "Customer ID",
                "CUSTOMER_NAME":       "Customer Name",
                "SLA_TIER":            "SLA Tier",
                "ORDERS_IN_CHAIN":     "Orders in Chain",
                "TOTAL_AT_RISK_REVENUE": "At-Risk Revenue ($)",
            }),
            use_container_width=True,
            hide_index=True,
        )

    st.caption(
        "Source: `NEXUS_DB.SCENARIOS.V_SUPPLIER_FAILURE_CHAIN` · "
        "Observed data joined with scenario engine outputs."
    )
