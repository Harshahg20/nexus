import streamlit as st

st.set_page_config(
    page_title="NEXUS — Supply Chain Resilience",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- Dark theme CSS ---
st.markdown(
    """<style>
    .stApp { background-color: #0a0a1a; }
    header[data-testid="stHeader"] { background-color: #0a0a1a; }
    [data-testid="stSidebar"] { background-color: #0d0d22; }
    h1, h2, h3, h4, h5, h6, p, span, div, label { color: #ccd6f6; }
    .stMarkdown p { color: #a8b2d1; }
    .stCaption p { color: #5a6580 !important; font-size: 0.78rem; }
    div[data-testid="stExpander"] { background-color: #11112a; border: 1px solid #1e1e3a; border-radius: 8px; }
    div[data-testid="stDataFrame"] { background-color: #11112a; }
    .stChatMessage { background-color: #11112a; }
    .stChatInputContainer { background-color: #1a1a2e; }
    section[data-testid="stSidebar"] .stMarkdown p { color: #a8b2d1; }
    </style>""",
    unsafe_allow_html=True,
)

# --- Header ---
st.markdown(
    """<div style="text-align:center; padding:24px 0 8px;">
        <div style="color:#64ffda; font-size:0.75rem; text-transform:uppercase;
            letter-spacing:0.25em; margin-bottom:6px;">◆ NEXUS</div>
        <div style="color:#e6f1ff; font-size:1.8rem; font-weight:700;
            line-height:1.2;">Supply Chain Resilience Command Center</div>
        <div style="color:#8892b0; font-size:0.9rem; margin-top:8px;">
            See the chain. Find the break. Act before the impact.</div>
    </div>""",
    unsafe_allow_html=True,
)
st.markdown("---")

# --- KPI Cards ---
from components import kpi_cards
kpi_cards.render()
st.markdown("")

# --- Two-column layout: scenario panel + dependency graph ---
col_scenario, col_graph = st.columns([1, 3])

with col_scenario:
    from components import scenario_panel
    scenario_panel.render()

with col_graph:
    st.markdown(
        '<div style="color:#ccd6f6; font-size:1.15rem; font-weight:600; margin-bottom:12px;">'
        "What Breaks Next?</div>",
        unsafe_allow_html=True,
    )
    from components import dependency_graph
    dependency_graph.render()

st.markdown("---")

# --- Impact Details ---
st.markdown(
    '<div style="color:#ccd6f6; font-size:1.15rem; font-weight:600; margin-bottom:8px;">'
    "Impact Details</div>",
    unsafe_allow_html=True,
)
from components import impact_details
impact_details.render()

st.markdown("---")

# --- Mitigation Comparison ---
st.markdown(
    '<div style="color:#ccd6f6; font-size:1.15rem; font-weight:600; margin-bottom:4px;">'
    "Compare Mitigations</div>",
    unsafe_allow_html=True,
)
st.markdown(
    '<div style="color:#8892b0; font-size:0.8rem; margin-bottom:12px;">'
    "Compare modeled tradeoffs to inform planning decisions.</div>",
    unsafe_allow_html=True,
)
from components import mitigation_table
mitigation_table.render()

st.markdown("---")

# --- Agent Chat ---
st.markdown(
    '<div style="color:#ccd6f6; font-size:1.15rem; font-weight:600; margin-bottom:4px;">'
    "Ask NEXUS</div>",
    unsafe_allow_html=True,
)
from components import chat
chat.render()

st.markdown("---")

# --- Evidence ---
st.markdown(
    '<div style="color:#ccd6f6; font-size:1.15rem; font-weight:600; margin-bottom:8px;">'
    "Evidence &amp; Modeling</div>",
    unsafe_allow_html=True,
)
from components import evidence
evidence.render()
