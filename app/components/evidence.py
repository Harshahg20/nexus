import streamlit as st
from services.snowflake import load_governed_metric_catalog


def render():
    observed = [
        ("Suppliers", "RAW.SUPPLIERS"),
        ("Parts", "RAW.PARTS"),
        ("Plants", "RAW.PLANTS"),
        ("Inventory", "RAW.INVENTORY"),
        ("Shipments", "RAW.SHIPMENTS"),
        ("Orders", "RAW.ORDERS"),
        ("Customers", "RAW.CUSTOMERS"),
    ]
    modeled = [
        ("Supplier failure impact", "SCENARIOS.V_SUPPLIER_FAILURE_IMPACT"),
        ("Order-part allocation", "SCENARIOS.V_ORDER_PART_ALLOCATION"),
        ("Revenue exposure", "SCENARIOS.V_ORDER_IMPACT"),
        ("Mitigation comparison", "SCENARIOS.V_MITIGATION_COMPARISON"),
        ("Port disruption impact", "SCENARIOS.V_PORT_DISRUPTION_IMPACT"),
        ("Freight shock summary", "SCENARIOS.V_FREIGHT_SHOCK_SUMMARY"),
    ]

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Observed / Governed Data**")
        for name, source in observed:
            st.markdown(
                f'<div style="color:#a8b2d1; font-size:0.82rem; padding:2px 0;">'
                f'{name} &mdash; <code style="color:#64ffda; font-size:0.75rem;">{source}</code></div>',
                unsafe_allow_html=True,
            )

    with col2:
        st.markdown("**Modeled Outputs**")
        for name, source in modeled:
            st.markdown(
                f'<div style="color:#a8b2d1; font-size:0.82rem; padding:2px 0;">'
                f'{name} &mdash; <code style="color:#64ffda; font-size:0.75rem;">{source}</code></div>',
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown("**Governed Metric Definitions**")
    catalog = load_governed_metric_catalog()
    if not catalog.empty:
        st.dataframe(
            catalog.rename(columns={
                "METRIC_NAME": "Metric", "DEFINITION": "Definition", "SOURCE_VIEW": "Source View",
            }),
            use_container_width=True, hide_index=True,
        )

    st.caption(
        "Scenario outputs are modeled decision-support results produced by deterministic "
        "priority-based order allocation. They are not operational guarantees."
    )
