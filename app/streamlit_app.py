import sys
import streamlit as st

# ── Python version guard (server log only — no UI banner) ────────────────────
import warnings as _warnings
_PY = sys.version_info
if (_PY.major, _PY.minor) < (3, 11):
    _warnings.warn(
        f"NEXUS is running on Python {_PY.major}.{_PY.minor}. "
        "Python 3.9 is EOL — Snowflake no longer patches this runtime. "
        "Run `make setup PYTHON=python3.11` to upgrade (see README → Prerequisites).",
        DeprecationWarning,
        stacklevel=1,
    )

st.set_page_config(
    page_title="NEXUS — Supply Chain Resilience",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Inject safe global CSS (no @import, no custom class deps) ─────────────────
from ui.theme import GLOBAL_CSS, C, FONT, SHADOW_MD
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
from services.snowflake import (
    load_supplier_failure_parameters as _sb_load_params,
    load_supplier_failure_impact as _sb_load_impact,
)
_sb_params = _sb_load_params()
_sb_supplier = _sb_params.get("FAILED_SUPPLIER_ID", "SUP-001") if _sb_params else "SUP-001"
_sb_capacity = float(_sb_params.get("CAPACITY_REDUCTION_PCT", 100) or 100) if _sb_params else 100
_sb_duration = int(_sb_params.get("DURATION_DAYS", 14) or 14) if _sb_params else 14

with st.sidebar:
    st.markdown(
        f"<div style='text-align:center;padding:8px 0 16px;font-family:{FONT};'>"
        f"<div style='font-size:1.2rem;font-weight:800;color:#0F172A;"
        f"letter-spacing:-0.02em;margin-bottom:4px;'>◆ NEXUS</div>"
        f"<div style='font-size:0.62rem;color:#94A3B8;text-transform:uppercase;"
        f"letter-spacing:0.15em;'>Supply Chain Intelligence</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # Powered by Snowflake badge
    st.markdown(
        "<div style='padding:10px 14px;background:rgba(0,196,154,0.06);"
        "border:1px solid rgba(0,196,154,0.22);border-radius:10px;"
        "text-align:center;margin-bottom:12px;'>"
        "<div style='font-size:0.58rem;font-weight:700;text-transform:uppercase;"
        "letter-spacing:0.12em;color:#007A5E;margin-bottom:3px;'>Powered by</div>"
        "<div style='font-size:1.0rem;font-weight:800;color:#007A5E;'>❄️ Snowflake</div>"
        "<div style='font-size:0.62rem;color:#94A3B8;margin-top:3px;'>"
        "Cortex &nbsp;·&nbsp; Snowpark &nbsp;·&nbsp; SiS</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    # Active scenario info
    st.markdown(
        f"<div style='font-size:0.6rem;font-weight:700;text-transform:uppercase;"
        f"letter-spacing:0.12em;color:#94A3B8;margin-bottom:8px;font-family:{FONT};'>"
        f"Active Scenario</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='padding:10px 14px;background:rgba(220,38,38,0.05);"
        f"border:1px solid rgba(220,38,38,0.18);border-radius:10px;margin-bottom:12px;"
        f"font-family:{FONT};'>"
        f"<div style='font-size:0.78rem;font-weight:700;color:#DC2626;margin-bottom:5px;'>"
        f"⚠ Supplier Failure</div>"
        f"<div style='font-size:0.72rem;color:#334155;margin-bottom:2px;'>"
        f"{_sb_supplier} &nbsp;·&nbsp; {_sb_capacity:.0f}% capacity loss</div>"
        f"<div style='font-size:0.68rem;color:#94A3B8;'>{_sb_duration}-day disruption window</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # GitHub link
    st.markdown(
        "<a href='https://github.com/Harshahg20/nexus' target='_blank' "
        "style='display:block;padding:9px 14px;background:#0F172A;border-radius:10px;"
        "text-decoration:none;text-align:center;margin-bottom:10px;'>"
        "<span style='font-size:0.75rem;font-weight:700;color:#ffffff;'>"
        "⬡ View on GitHub</span></a>",
        unsafe_allow_html=True,
    )

    # Hackathon watermark
    st.markdown(
        "<div style='text-align:center;padding:8px 0 4px;'>"
        "<div style='font-size:0.58rem;color:#CBD5E1;'>Snowflake CoCo CLI Hackathon</div>"
        "</div>",
        unsafe_allow_html=True,
    )


# ─── HEADER (with live quick-stat badges) ────────────────────────────────────
import streamlit.components.v1 as components

# Fetch quick stats early — cached, so no extra DB round-trips after first load
_hero_impact  = _sb_load_impact()
_hero_revenue = _hero_impact.get("REVENUE_EXPOSURE", 0) or 0
_hero_orders  = _hero_impact.get("ORDERS_AT_RISK", 0) or 0
_hero_custs   = _hero_impact.get("CUSTOMERS_EXPOSED", 0) or 0
_rev_display  = f"${_hero_revenue/1_000_000:.1f}M" if _hero_revenue else "—"
_ord_display  = str(_hero_orders) if _hero_orders else "—"
_cst_display  = str(_hero_custs) if _hero_custs else "—"

components.html(f"""
<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{
  font-family:{FONT};
  background:transparent;
  padding:32px 20px 24px;
  text-align:center;
}}
.pill {{
  display:inline-flex; align-items:center; gap:8px;
  padding:5px 18px;
  border:1px solid rgba(0,196,154,0.35);
  border-radius:100px;
  background:rgba(0,196,154,0.07);
  margin-bottom:16px;
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
  font-size:2.4rem; font-weight:800; line-height:1.15;
  letter-spacing:-0.03em; color:{C.T1};
  margin-bottom:10px;
}}
.title span {{
  background:linear-gradient(135deg,{C.TEAL} 0%,#0891B2 100%);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent;
  background-clip:text;
}}
.tagline {{
  font-size:0.95rem; color:{C.T4}; letter-spacing:0.01em; margin-bottom:18px;
  line-height:1.5;
}}
/* ── Live stats strip ───────────────────────────────────────── */
.stats-strip {{
  display:inline-flex; align-items:stretch;
  background:#F8FAFC; border:1px solid #E2E8F0; border-radius:12px;
  overflow:hidden; margin:0 auto 18px; max-width:520px; width:100%;
}}
.stat {{
  flex:1; padding:10px 12px; text-align:center;
  border-right:1px solid #E2E8F0;
}}
.stat:last-child {{ border-right:none; }}
.stat-val {{
  font-size:1.1rem; font-weight:800; letter-spacing:-0.02em; color:#0F172A;
  line-height:1.2;
}}
.stat-val.red {{ color:#DC2626; }}
.stat-lbl {{
  font-size:0.56rem; font-weight:700; text-transform:uppercase;
  letter-spacing:0.1em; color:#94A3B8; margin-top:3px;
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
/* ── Responsive type scale ───────────────────────────────────── */
@media (max-width: 768px) {{
  body {{ padding:24px 16px 20px; }}
  .title {{ font-size:1.9rem; }}
  .tagline {{ font-size:0.85rem; }}
  .stats-strip {{ max-width:100%; }}
  .stat-val {{ font-size:0.95rem; }}
}}
@media (max-width: 480px) {{
  .title {{ font-size:1.55rem; }}
  .tagline {{ font-size:0.78rem; }}
  .pill {{ padding:4px 14px; margin-bottom:12px; }}
  .live-badge {{ padding:5px 12px; }}
  .stat {{ padding:8px 8px; }}
  .stat-val {{ font-size:0.85rem; }}
}}
</style>
</head><body>
<div class="pill">
  <span class="dot"></span>
  <span class="pill-text">AI-Powered Supply Chain Resilience on Snowflake</span>
  <span class="dot"></span>
</div>
<div class="title">
  Supply Chain Resilience<br><span>Command Center</span>
</div>
<div class="tagline">
  See the chain &nbsp;&middot;&nbsp; Find the break &nbsp;&middot;&nbsp; Act before the impact
</div>
<!-- Live stats from Snowflake -->
<div class="stats-strip">
  <div class="stat">
    <div class="stat-val red">{_rev_display}</div>
    <div class="stat-lbl">At-Risk Revenue</div>
  </div>
  <div class="stat">
    <div class="stat-val">{_ord_display}</div>
    <div class="stat-lbl">Orders Disrupted</div>
  </div>
  <div class="stat">
    <div class="stat-val">{_cst_display}</div>
    <div class="stat-lbl">Customers Affected</div>
  </div>
</div>
<br>
<div class="live-badge">
  <span class="live-dot"></span>
  <span class="live-text">Supplier Failure: {_sb_supplier} ({_sb_duration}-day disruption)</span>
</div>
</body></html>
""", height=310)


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
    f"letter-spacing:0.18em;color:{C.T5};margin-bottom:6px;font-family:{FONT};'>Failure Propagation — SUP-001 Causal Impact</p>"
    f"<h3 style='font-size:1.35rem;font-weight:800;color:{C.T1};letter-spacing:-0.02em;"
    f"margin-bottom:4px;font-family:{FONT};'>What Breaks Because of SUP-001?</h3>"
    f"<p style='font-size:0.82rem;color:{C.T4};margin-bottom:20px;font-family:{FONT};'>"
    f"Causal cascade from SUP-001's failure — only parts, orders, and customers whose shortage "
    f"is traceable to SUP-001's qualified parts. Counts here are smaller than the headline KPIs "
    f"above, which include all scenario-wide shortages.</p>",
    unsafe_allow_html=True,
)
from components import dependency_graph
dependency_graph.render()

st.markdown("---")

# ─── IMPACT DETAILS ──────────────────────────────────────────────────────────
st.markdown(
    f"<p style='font-size:0.63rem;font-weight:700;text-transform:uppercase;"
    f"letter-spacing:0.18em;color:{C.T5};margin-bottom:6px;font-family:{FONT};'>Downstream Impact — SUP-001 Causal Trace</p>"
    f"<h3 style='font-size:1.35rem;font-weight:800;color:{C.T1};letter-spacing:-0.02em;"
    f"margin-bottom:4px;font-family:{FONT};'>Impact Details</h3>"
    f"<p style='font-size:0.82rem;color:{C.T4};margin-bottom:20px;font-family:{FONT};'>"
    f"Parts, plants, orders, and customers whose shortage is traceable to SUP-001. "
    f"Counts are smaller than headline KPIs, which include all scenario-wide shortages.</p>",
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
    f"Four modeled response strategies — compare tradeoffs to inform your decision.</p>",
    unsafe_allow_html=True,
)
from components import mitigation_table
mitigation_table.render()

st.markdown("---")

# ─── PORT DISRUPTION SCENARIO ────────────────────────────────────────────────
with st.expander("🚢  Port Disruption Scenario — PORT-TYO (7-day disruption)", expanded=False):
    st.caption(
        "Alternative scenario: Tokyo port (PORT-TYO) closure propagated through the supply chain. "
        "Blocked shipments create part shortages at downstream plants, disrupting orders and customers."
    )
    try:
        from services.snowflake import get_session as _get_session
        _port_session = _get_session()
        _port_df = _port_session.sql(
            "SELECT supplier_name, part_name, plant_name, customer_name, "
            "at_risk_quantity, at_risk_revenue, sla_tier "
            "FROM NEXUS_DB.SCENARIOS.V_PORT_DISRUPTION_CHAIN LIMIT 20"
        ).to_pandas()
        if not _port_df.empty:
            from ui.compat import st_dataframe
            st_dataframe(_port_df, use_container_width=True, hide_index=True)
        else:
            st.info("No port disruption impact data found — the view returned no rows.")
    except Exception as _port_exc:
        st.info(f"Port disruption view not available: {_port_exc}")

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

st.markdown("---")

# ─── HOW NEXUS WORKS ─────────────────────────────────────────────────────────
with st.expander("⚙️  How NEXUS Works — Technical Architecture (for judges & technical reviewers)", expanded=False):
    components.html(f"""<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<style>
* {{ box-sizing:border-box; margin:0; padding:0; font-family:{FONT}; }}
body {{ background:transparent; padding:4px 0; }}
.arch-grid {{
  display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin-bottom:20px;
}}
.layer {{
  background:#fff; border:1px solid #E2E8F0; border-radius:14px;
  overflow:hidden; padding:0;
  box-shadow:0 1px 4px rgba(0,0,0,0.06);
}}
.layer-bar {{ height:3px; }}
.layer-body {{ padding:16px 18px 18px; }}
.layer-num {{
  font-size:0.58rem; font-weight:700; text-transform:uppercase;
  letter-spacing:0.15em; color:#94A3B8; margin-bottom:6px;
}}
.layer-title {{ font-size:0.95rem; font-weight:800; color:#0F172A; margin-bottom:8px; }}
.layer-desc  {{ font-size:0.75rem; color:#64748B; line-height:1.6; margin-bottom:10px; }}
.tech-pill {{
  display:inline-block; padding:3px 10px; border-radius:6px; margin:2px 2px 0 0;
  font-size:0.68rem; font-weight:600;
}}
.powered-grid {{
  display:grid; grid-template-columns:repeat(4,1fr); gap:12px;
}}
.powered-item {{
  background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px;
  padding:12px 14px; text-align:center;
}}
.powered-icon {{ font-size:1.4rem; margin-bottom:4px; }}
.powered-name {{ font-size:0.72rem; font-weight:700; color:#0F172A; margin-bottom:2px; }}
.powered-desc {{ font-size:0.62rem; color:#94A3B8; line-height:1.4; }}
@media (max-width:700px) {{
  .arch-grid {{ grid-template-columns:1fr; }}
  .powered-grid {{ grid-template-columns:repeat(2,1fr); }}
}}
</style>
</head>
<body>
<div style="margin-bottom:14px;">
  <div style="font-size:0.6rem;font-weight:700;text-transform:uppercase;letter-spacing:0.18em;
              color:#94A3B8;margin-bottom:4px;">Architecture</div>
  <div style="font-size:1.1rem;font-weight:800;color:#0F172A;letter-spacing:-0.02em;">
    3-Layer Intelligence Stack
  </div>
</div>
<div class="arch-grid">
  <!-- Layer 1 -->
  <div class="layer">
    <div class="layer-bar" style="background:linear-gradient(90deg,#2563EB,#0891B2);"></div>
    <div class="layer-body">
      <div class="layer-num">Layer 1</div>
      <div class="layer-title">Raw Data</div>
      <div class="layer-desc">
        Supplier master, product BOM, customer orders, and historical pricing — 
        all governed Snowflake tables. Semantic Views add a metadata layer so the AI 
        agent understands <em>data meaning</em>, not just column names.
      </div>
      <span class="tech-pill" style="background:rgba(37,99,235,0.08);border:1px solid rgba(37,99,235,0.2);color:#2563EB;">Snowflake Tables</span>
      <span class="tech-pill" style="background:rgba(37,99,235,0.08);border:1px solid rgba(37,99,235,0.2);color:#2563EB;">Semantic Views</span>
    </div>
  </div>
  <!-- Layer 2 -->
  <div class="layer">
    <div class="layer-bar" style="background:linear-gradient(90deg,#7C3AED,#2563EB);"></div>
    <div class="layer-body">
      <div class="layer-num">Layer 2</div>
      <div class="layer-title">Scenario Engine</div>
      <div class="layer-desc">
        When a disruption scenario is activated, a deterministic allocation model runs 
        <em>inside Snowflake</em> via Snowpark — no data movement. Traces Supplier → Parts 
        → Plants → Products → Orders → Customers and computes financial impact in real-time SQL.
      </div>
      <span class="tech-pill" style="background:rgba(124,58,237,0.08);border:1px solid rgba(124,58,237,0.2);color:#7C3AED;">Snowpark</span>
      <span class="tech-pill" style="background:rgba(124,58,237,0.08);border:1px solid rgba(124,58,237,0.2);color:#7C3AED;">SQL Views</span>
    </div>
  </div>
  <!-- Layer 3 -->
  <div class="layer">
    <div class="layer-bar" style="background:linear-gradient(90deg,#00C49A,#0891B2);"></div>
    <div class="layer-body">
      <div class="layer-num">Layer 3</div>
      <div class="layer-title">AI Agent</div>
      <div class="layer-desc">
        A Cortex-powered agent interprets natural language questions against Semantic Views.
        It maps "which customers are most at risk?" to governed metrics and returns grounded,
        auditable answers — no hallucination risk because it queries <em>live Snowflake data</em>.
      </div>
      <span class="tech-pill" style="background:rgba(0,196,154,0.08);border:1px solid rgba(0,196,154,0.2);color:#007A5E;">Cortex Agent</span>
      <span class="tech-pill" style="background:rgba(0,196,154,0.08);border:1px solid rgba(0,196,154,0.2);color:#007A5E;">Cortex LLM</span>
    </div>
  </div>
</div>

<div style="margin:16px 0 10px;">
  <div style="font-size:0.6rem;font-weight:700;text-transform:uppercase;letter-spacing:0.18em;
              color:#94A3B8;margin-bottom:8px;">Powered by</div>
</div>
<div class="powered-grid">
  <div class="powered-item">
    <div class="powered-icon">❄️</div>
    <div class="powered-name">Snowflake Cortex</div>
    <div class="powered-desc">LLM inference + Agent framework on live data</div>
  </div>
  <div class="powered-item">
    <div class="powered-icon">📐</div>
    <div class="powered-name">Semantic Views</div>
    <div class="powered-desc">Governed metadata for agent grounding</div>
  </div>
  <div class="powered-item">
    <div class="powered-icon">🔧</div>
    <div class="powered-name">Snowpark</div>
    <div class="powered-desc">In-warehouse Python computation, zero data movement</div>
  </div>
  <div class="powered-item">
    <div class="powered-icon">🌐</div>
    <div class="powered-name">Streamlit in Snowflake</div>
    <div class="powered-desc">Fully managed frontend — no infra to operate</div>
  </div>
</div>
</body></html>""", height=560)

    st.caption(
        "NEXUS was built for the Snowflake CoCo CLI Hackathon. "
        "All computation runs inside Snowflake — the frontend is a pure Streamlit-in-Snowflake app. "
        "Source: [github.com/Harshahg20/nexus](https://github.com/Harshahg20/nexus)"
    )


# ─── FOOTER ──────────────────────────────────────────────────────────────────
st.markdown(
    f"<div style='text-align:center;padding:32px 0 8px;font-family:{FONT};'>"
    f"<p style='font-size:0.7rem;color:{C.T5};letter-spacing:0.05em;'>"
    f"Snowflake Cortex &nbsp;·&nbsp; Snowpark &nbsp;·&nbsp; Streamlit &nbsp;·&nbsp; Native Semantic View"
    f"</p>"
    f"<p style='font-size:0.65rem;color:{C.T6};margin-top:3px;'>"
    f"NEXUS — Snowflake CoCo CLI Hackathon &nbsp;·&nbsp; "
    f"<a href='https://github.com/Harshahg20/nexus' style='color:{C.TEAL};text-decoration:none;'>"
    f"github.com/Harshahg20/nexus</a></p></div>",
    unsafe_allow_html=True,
)
