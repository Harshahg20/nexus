import streamlit as st

st.set_page_config(
    page_title="NEXUS — Supply Chain Resilience",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Inject safe global CSS (no @import, no custom class deps) ─────────────────
from ui.theme import GLOBAL_CSS, C, FONT, SHADOW_MD
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


# ─── HEADER ──────────────────────────────────────────────────────────────────
import streamlit.components.v1 as components

components.html(f"""
<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{
  font-family:{FONT};
  background:transparent;
  padding:36px 24px 28px;
  text-align:center;
}}
.pill {{
  display:inline-flex; align-items:center; gap:8px;
  padding:5px 18px;
  border:1px solid rgba(0,196,154,0.35);
  border-radius:100px;
  background:rgba(0,196,154,0.07);
  margin-bottom:18px;
}}
.dot {{
  width:7px; height:7px; border-radius:50%;
  background:{C.TEAL};
  animation:tp 2s ease infinite;
}}
@keyframes tp {{
  0%,100% {{ box-shadow:0 0 0 0 rgba(0,196,154,0.5); }}
  50%     {{ box-shadow:0 0 0 5px rgba(0,196,154,0); }}
}}
.pill-text {{
  font-size:0.62rem; font-weight:700; text-transform:uppercase;
  letter-spacing:0.3em; color:{C.TEAL};
}}
.title {{
  font-size:2.5rem; font-weight:800; line-height:1.15;
  letter-spacing:-0.03em; color:{C.T1};
  margin-bottom:10px;
}}
.title span {{
  background:linear-gradient(135deg,{C.TEAL} 0%,#0891B2 100%);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent;
  background-clip:text;
}}
.tagline {{
  font-size:0.98rem; color:{C.T4}; letter-spacing:0.01em; margin-bottom:20px;
}}
.live-badge {{
  display:inline-flex; align-items:center; gap:8px;
  padding:6px 16px;
  background:{C.RED_DIM};
  border:1px solid {C.RED_BORDER};
  border-radius:100px;
}}
.live-dot {{
  width:7px; height:7px; border-radius:50%;
  background:{C.RED}; animation:rp 1.6s ease infinite;
  flex-shrink:0;
}}
@keyframes rp {{
  0%,100% {{ box-shadow:0 0 0 0 rgba(220,38,38,0.5); }}
  50%     {{ box-shadow:0 0 0 5px rgba(220,38,38,0); }}
}}
.live-text {{
  font-size:0.63rem; font-weight:700; text-transform:uppercase;
  letter-spacing:0.1em; color:{C.RED_TEXT};
}}
</style>
</head><body>
<div class="pill">
  <span class="dot"></span>
  <span class="pill-text">NEXUS</span>
  <span class="dot"></span>
</div>
<div class="title">
  Supply Chain Resilience<br><span>Command Center</span>
</div>
<div class="tagline">
  See the chain &nbsp;&middot;&nbsp; Find the break &nbsp;&middot;&nbsp; Act before the impact
</div>
<div class="live-badge">
  <span class="live-dot"></span>
  <span class="live-text">Scenario Active &mdash; Supplier Failure Engine</span>
</div>
</body></html>
""", height=220)


# ─── KPI STRIP ───────────────────────────────────────────────────────────────
from components import kpi_cards
kpi_cards.render()

st.write("")

# ─── SCENARIO BANNER ─────────────────────────────────────────────────────────
from components import scenario_panel
scenario_panel.render()

# ─── CASCADE ─────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f"<p style='font-size:0.63rem;font-weight:700;text-transform:uppercase;"
    f"letter-spacing:0.18em;color:{C.T5};margin-bottom:6px;font-family:{FONT};'>Failure Propagation</p>"
    f"<h3 style='font-size:1.35rem;font-weight:800;color:{C.T1};letter-spacing:-0.02em;"
    f"margin-bottom:4px;font-family:{FONT};'>What Breaks Next?</h3>"
    f"<p style='font-size:0.82rem;color:{C.T4};margin-bottom:20px;font-family:{FONT};'>"
    f"Deterministic cascade — one supplier disruption propagates through parts → plants → products → orders → customers.</p>",
    unsafe_allow_html=True,
)
from components import dependency_graph
dependency_graph.render()

st.markdown("---")

# ─── IMPACT DETAILS ──────────────────────────────────────────────────────────
st.markdown(
    f"<p style='font-size:0.63rem;font-weight:700;text-transform:uppercase;"
    f"letter-spacing:0.18em;color:{C.T5};margin-bottom:6px;font-family:{FONT};'>Downstream Impact</p>"
    f"<h3 style='font-size:1.35rem;font-weight:800;color:{C.T1};letter-spacing:-0.02em;"
    f"margin-bottom:4px;font-family:{FONT};'>Impact Details</h3>"
    f"<p style='font-size:0.82rem;color:{C.T4};margin-bottom:20px;font-family:{FONT};'>"
    f"Drill into every affected part, plant, order and customer for this scenario.</p>",
    unsafe_allow_html=True,
)
from components import impact_details
impact_details.render()

st.markdown("---")

# ─── MITIGATIONS ─────────────────────────────────────────────────────────────
st.markdown(
    f"<p style='font-size:0.63rem;font-weight:700;text-transform:uppercase;"
    f"letter-spacing:0.18em;color:{C.T5};margin-bottom:6px;font-family:{FONT};'>Decision Support</p>"
    f"<h3 style='font-size:1.35rem;font-weight:800;color:{C.T1};letter-spacing:-0.02em;"
    f"margin-bottom:4px;font-family:{FONT};'>Compare Mitigations</h3>"
    f"<p style='font-size:0.82rem;color:{C.T4};margin-bottom:20px;font-family:{FONT};'>"
    f"Three modeled response strategies — compare tradeoffs to inform your decision.</p>",
    unsafe_allow_html=True,
)
from components import mitigation_table
mitigation_table.render()

st.markdown("---")

# ─── ASK NEXUS ───────────────────────────────────────────────────────────────
from components import chat
chat.render()

st.markdown("---")

# ─── EVIDENCE ────────────────────────────────────────────────────────────────
st.markdown(
    f"<p style='font-size:0.63rem;font-weight:700;text-transform:uppercase;"
    f"letter-spacing:0.18em;color:{C.T5};margin-bottom:6px;font-family:{FONT};'>Data Provenance</p>"
    f"<h3 style='font-size:1.35rem;font-weight:800;color:{C.T1};letter-spacing:-0.02em;"
    f"margin-bottom:4px;font-family:{FONT};'>Evidence &amp; Modeling</h3>"
    f"<p style='font-size:0.82rem;color:{C.T4};margin-bottom:20px;font-family:{FONT};'>"
    f"Authoritative Snowflake sources and governed metric definitions behind this analysis.</p>",
    unsafe_allow_html=True,
)
from components import evidence
evidence.render()

# ─── FOOTER ──────────────────────────────────────────────────────────────────
st.markdown(
    f"<div style='text-align:center;padding:32px 0 8px;font-family:{FONT};'>"
    f"<p style='font-size:0.7rem;color:{C.T5};letter-spacing:0.05em;'>"
    f"Snowflake Cortex &nbsp;·&nbsp; Snowpark &nbsp;·&nbsp; Streamlit &nbsp;·&nbsp; Native Semantic View"
    f"</p>"
    f"<p style='font-size:0.65rem;color:{C.T6};margin-top:3px;'>"
    f"NEXUS — Snowflake CoCo CLI Hackathon</p></div>",
    unsafe_allow_html=True,
)
