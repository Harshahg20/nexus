import streamlit as st
from services.snowflake import load_supplier_failure_parameters


def render():
    params = load_supplier_failure_parameters()
    if not params:
        st.info("No active scenario configured.")
        return

    st.markdown(
        f"""<div style="background:#1a1a2e; border:1px solid #2a2a4a; border-radius:8px; padding:20px;">
            <div style="color:#8892b0; font-size:0.7rem; text-transform:uppercase;
                letter-spacing:0.12em; margin-bottom:12px;">Active Scenario</div>
            <div style="color:#ccd6f6; font-size:1.1rem; font-weight:600; margin-bottom:16px;">
                Supplier Failure</div>
            <table style="width:100%; color:#a8b2d1; font-size:0.85rem;">
                <tr><td style="padding:4px 0; color:#8892b0;">Supplier</td>
                    <td style="padding:4px 0; text-align:right; color:#e6f1ff; font-weight:600;">
                        {params.get('FAILED_SUPPLIER_ID', '—')}</td></tr>
                <tr><td style="padding:4px 0; color:#8892b0;">Capacity Reduction</td>
                    <td style="padding:4px 0; text-align:right; color:#e6f1ff; font-weight:600;">
                        {params.get('CAPACITY_REDUCTION_PCT', 0):.0f}%</td></tr>
                <tr><td style="padding:4px 0; color:#8892b0;">Duration</td>
                    <td style="padding:4px 0; text-align:right; color:#e6f1ff; font-weight:600;">
                        {params.get('DURATION_DAYS', 0)} days</td></tr>
                <tr><td style="padding:4px 0; color:#8892b0;">Start Date</td>
                    <td style="padding:4px 0; text-align:right; color:#e6f1ff; font-weight:600;">
                        {params.get('START_DATE', '—')}</td></tr>
            </table>
        </div>""",
        unsafe_allow_html=True,
    )
    st.caption(
        "This MVP runs the configured deterministic scenario. "
        "Custom scenario parameters are not yet supported."
    )
