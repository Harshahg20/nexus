import streamlit as st
import streamlit.components.v1 as components
from services.snowflake import load_supplier_failure_parameters
from ui.theme import C, FONT


def render():
    params = load_supplier_failure_parameters()
    if not params:
        st.info("No active scenario configured.")
        return

    supplier = params.get("FAILED_SUPPLIER_ID", "—")
    capacity = params.get("CAPACITY_REDUCTION_PCT", 0)
    duration = params.get("DURATION_DAYS", 0)
    start    = str(params.get("START_DATE", "—"))

    if capacity >= 100:
        color, bg, border, label = "#DC2626", "rgba(220,38,38,0.07)", "rgba(220,38,38,0.25)", "CRITICAL"
    elif capacity >= 50:
        color, bg, border, label = "#EA580C", "rgba(234,88,12,0.07)", "rgba(234,88,12,0.25)", "HIGH"
    else:
        color, bg, border, label = "#D97706", "rgba(217,119,6,0.07)", "rgba(217,119,6,0.25)", "MEDIUM"

    def param(lbl, val, val_color="#0F172A"):
        return f"""
        <div style="display:flex;flex-direction:column;gap:2px;">
          <div style="font-size:0.6rem;font-weight:700;text-transform:uppercase;
                      letter-spacing:0.1em;color:#94A3B8;">{lbl}</div>
          <div style="font-size:0.92rem;font-weight:700;color:{val_color};">{val}</div>
        </div>"""

    sep = '<div style="width:1px;height:36px;background:#E2E8F0;align-self:center;"></div>'

    banner = f"""
    <div style="display:flex;align-items:center;flex-wrap:wrap;gap:20px;
                padding:16px 24px;background:#ffffff;
                border:1px solid #E2E8F0;border-left:3px solid {color};
                border-radius:0 14px 14px 0;
                box-shadow:0 1px 3px rgba(0,0,0,0.07);margin-bottom:8px;">

      <div style="display:inline-flex;align-items:center;gap:7px;
                  padding:5px 14px;background:{bg};
                  border:1px solid {border};border-radius:100px;">
        <span style="width:7px;height:7px;border-radius:50%;background:{color};
                     display:inline-block;flex-shrink:0;
                     animation:rp 1.5s ease infinite;"></span>
        <span style="font-size:0.62rem;font-weight:700;text-transform:uppercase;
                     letter-spacing:0.12em;color:{color};white-space:nowrap;">
          {label} &mdash; Active Scenario
        </span>
      </div>

      {sep}
      {param("Scenario Type",   "Supplier Failure")}
      {sep}
      {param("Supplier ID",     supplier, color)}
      {sep}
      {param("Capacity Impact", f"{capacity:.0f}% reduction")}
      {sep}
      {param("Duration",        f"{duration} days")}
      {sep}
      {param("Start Date",      start)}

      <div style="margin-left:auto;font-size:0.7rem;color:#CBD5E1;
                  text-align:right;line-height:1.6;max-width:180px;">
        Deterministic scenario.<br>Custom params not yet supported.
      </div>
    </div>"""

    components.html(
        f"<!DOCTYPE html><html><head><meta charset='UTF-8'>"
        f"<style>*{{box-sizing:border-box;font-family:{FONT};}}"
        f"@keyframes rp{{0%,100%{{box-shadow:0 0 0 0 rgba(220,38,38,.5);}}"
        f"50%{{box-shadow:0 0 0 5px rgba(220,38,38,0);}}}}</style>"
        f"</head><body style='margin:0;padding:0;background:transparent;'>"
        f"{banner}</body></html>",
        height=88,
    )
