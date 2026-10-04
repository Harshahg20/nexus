"""
NEXUS Design System — Light Theme
Inspired by: Stripe, Linear, Vercel, shadcn/ui slate-light
"""

FONT       = "-apple-system,BlinkMacSystemFont,'SF Pro Display','Segoe UI','Helvetica Neue',Arial,sans-serif"
FONT_MONO  = "'SF Mono','Fira Code','Cascadia Code','Consolas',monospace"


class C:
    # ── Backgrounds ───────────────────────────────────────────────────────────
    BASE       = "#F1F5F9"   # slate-100 – page bg
    CARD       = "#FFFFFF"   # white cards
    CARD_ALT   = "#F8FAFC"   # slate-50
    ELEVATED   = "#FFFFFF"

    # ── Borders ───────────────────────────────────────────────────────────────
    BORDER     = "#E2E8F0"   # slate-200
    BORDER_MD  = "#CBD5E1"   # slate-300
    BORDER_LG  = "#94A3B8"   # slate-400

    # ── Text (slate scale) ────────────────────────────────────────────────────
    T1         = "#0F172A"   # slate-900
    T2         = "#1E293B"   # slate-800
    T3         = "#334155"   # slate-700
    T4         = "#64748B"   # slate-500
    T5         = "#94A3B8"   # slate-400
    T6         = "#CBD5E1"   # slate-300

    # ── Brand ─────────────────────────────────────────────────────────────────
    TEAL       = "#00C49A"
    TEAL_DIM   = "rgba(0,196,154,0.08)"
    TEAL_BORDER= "rgba(0,196,154,0.3)"
    TEAL_TEXT  = "#007A5E"

    # ── Status – darker shades for light bg readability ───────────────────────
    RED        = "#DC2626"
    RED_DIM    = "rgba(220,38,38,0.06)"
    RED_BORDER = "rgba(220,38,38,0.22)"
    RED_GLOW   = "rgba(220,38,38,0.08)"
    RED_TEXT   = "#DC2626"

    ORANGE     = "#EA580C"
    ORANGE_DIM = "rgba(234,88,12,0.06)"
    ORANGE_BORDER = "rgba(234,88,12,0.22)"
    ORANGE_TEXT= "#EA580C"

    GREEN      = "#16A34A"
    GREEN_DIM  = "rgba(22,163,74,0.06)"
    GREEN_BORDER = "rgba(22,163,74,0.22)"
    GREEN_TEXT = "#16A34A"

    AMBER      = "#D97706"
    AMBER_DIM  = "rgba(217,119,6,0.06)"
    AMBER_BORDER = "rgba(217,119,6,0.22)"

    BLUE       = "#2563EB"
    BLUE_DIM   = "rgba(37,99,235,0.06)"
    BLUE_BORDER= "rgba(37,99,235,0.22)"

    PURPLE     = "#7C3AED"
    PURPLE_DIM = "rgba(124,58,237,0.06)"
    PURPLE_BORDER = "rgba(124,58,237,0.22)"

    CYAN       = "#0891B2"
    CYAN_DIM   = "rgba(8,145,178,0.06)"
    CYAN_BORDER= "rgba(8,145,178,0.22)"


# Shadow tokens
SHADOW_SM  = "0 1px 3px rgba(0,0,0,0.07), 0 1px 2px rgba(0,0,0,0.04)"
SHADOW_MD  = "0 4px 12px rgba(0,0,0,0.06), 0 2px 4px rgba(0,0,0,0.04)"
SHADOW_LG  = "0 8px 24px rgba(0,0,0,0.08), 0 2px 6px rgba(0,0,0,0.04)"



# ── Global CSS ────────────────────────────────────────────────────────────────
# SAFE: no @import, targets Streamlit data-testid selectors only
GLOBAL_CSS = f"""<style>

/* ── Force light theme — main area ──────────────────────────────────────── */
[data-testid="stApp"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
section[data-testid="stMain"],
.main, .main > div {{
    background-color: {C.BASE} !important;
    color: {C.T1} !important;
}}

/* ── Force light theme — sidebar (nuclear: catches all SiS dark overrides) ── */
[data-testid="stSidebar"],
section[data-testid="stSidebar"],
[data-testid="stSidebar"] > div,
[data-testid="stSidebar"] > div > div,
[data-testid="stSidebar"] > div > div > div,
[data-testid="stSidebarContent"],
[data-testid="stSidebarUserContent"],
[data-testid="stSidebarUserContent"] > div,
[data-testid="stSidebarUserContent"] > div > div {{
    background-color: {C.CARD} !important;
    color-scheme: light !important;
}}

/* Sidebar — ALL text elements forced dark (wildcard catches radio spans etc) */
[data-testid="stSidebar"] *:not(svg):not(path):not(circle):not(rect) {{
    color: {C.T2} !important;
}}

/* Sidebar — re-allow brand/status colors on specific elements */
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] a {{
    color: {C.TEAL_TEXT} !important;
}}

/* Sidebar — slider fill & thumb stay teal */
[data-testid="stSidebar"] [data-testid="stSlider"] [role="slider"] {{
    background-color: {C.TEAL} !important;
    border-color: {C.TEAL} !important;
}}

/* Sidebar — selectbox dropdown: force light bg + dark text */
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div,
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div > div,
[data-testid="stSidebar"] select,
[data-testid="stSidebar"] [data-testid="stSelectbox"] span {{
    background-color: {C.BASE} !important;
    color: {C.T1} !important;
    border-color: {C.BORDER_MD} !important;
}}

/* Sidebar — text input */
[data-testid="stSidebar"] input {{
    background-color: {C.BASE} !important;
    color: {C.T1} !important;
    border-color: {C.BORDER_MD} !important;
}}

/* Sidebar — slider track background */
[data-testid="stSidebar"] [data-testid="stSlider"] > div {{
    background-color: {C.CARD} !important;
}}

/* ── Typography ─────────────────────────────────────────────────────────── */
* {{ font-family: {FONT}; }}
h1,h2,h3,h4,h5,h6 {{ color: {C.T1} !important; font-weight: 700; }}
p, .stMarkdown p  {{ color: {C.T3} !important; }}
.stCaption, .stCaption p {{
    color: {C.T5} !important;
    font-size: 0.73rem !important;
    line-height: 1.6 !important;
}}

/* ── Layout ─────────────────────────────────────────────────────────────── */
.block-container {{
    padding: 0 2.5rem 5rem !important;
    max-width: 1360px !important;
    margin: 0 auto !important;
}}
[data-testid="column"] {{ padding: 0 6px !important; }}
[data-testid="stHeader"] {{ background: transparent !important; box-shadow: none !important; }}

/* ── Hide chrome ────────────────────────────────────────────────────────── */
#MainMenu, footer, .stDeployButton {{ display: none !important; }}

/* ── Divider ────────────────────────────────────────────────────────────── */
hr {{
    border: none !important;
    border-top: 1px solid {C.BORDER} !important;
    margin: 2rem 0 !important;
}}

/* ── st.metric ──────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {{
    background: {C.CARD};
    border: 1px solid {C.BORDER};
    border-radius: 14px;
    padding: 20px 20px 16px !important;
    box-shadow: {SHADOW_SM};
    transition: box-shadow 0.2s, border-color 0.2s;
}}
[data-testid="stMetric"]:hover {{
    box-shadow: {SHADOW_MD};
    border-color: {C.BORDER_MD};
}}
[data-testid="stMetricLabel"]  {{ color: {C.T4} !important; font-size: 0.72rem !important; font-weight: 700 !important; text-transform: uppercase !important; letter-spacing: 0.1em !important; }}
[data-testid="stMetricValue"]  {{ color: {C.T1} !important; font-size: 1.9rem !important; font-weight: 800 !important; letter-spacing: -0.02em !important; }}

/* ── Scrollbar ──────────────────────────────────────────────────────────── */
::-webkit-scrollbar {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{ background: {C.BASE}; }}
::-webkit-scrollbar-thumb {{ background: {C.BORDER_MD}; border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: {C.TEAL}; }}

/* ── Expanders ──────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {{
    background: {C.CARD} !important;
    border: 1px solid {C.BORDER} !important;
    border-radius: 12px !important;
    margin-bottom: 8px !important;
    box-shadow: {SHADOW_SM} !important;
    overflow: hidden !important;
}}
[data-testid="stExpander"] summary {{
    padding: 14px 20px !important;
    color: {C.T3} !important;
    font-size: 0.875rem !important;
    font-weight: 600 !important;
}}
[data-testid="stExpander"] summary:hover {{
    color: {C.T1} !important;
    background: {C.CARD_ALT} !important;
}}
[data-testid="stExpander"] > div > div {{
    border-top: 1px solid {C.BORDER} !important;
    padding: 16px 20px !important;
}}

/* ── DataFrames ─────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {{
    border-radius: 10px !important;
    border: 1px solid {C.BORDER} !important;
    box-shadow: {SHADOW_SM} !important;
    overflow: hidden !important;
}}
[data-testid="stDataFrame"] thead th {{
    background: {C.CARD_ALT} !important;
    color: {C.T4} !important;
    font-size: 0.7rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
}}
[data-testid="stDataFrame"] tbody td {{
    color: {C.T2} !important;
    font-size: 0.82rem !important;
}}
[data-testid="stDataFrame"] tbody tr:hover td {{
    background: {C.CARD_ALT} !important;
}}

/* ── Chat ───────────────────────────────────────────────────────────────── */
[data-testid="stChatMessage"] {{
    background: {C.CARD} !important;
    border: 1px solid {C.BORDER} !important;
    border-radius: 12px !important;
    margin: 6px 0 !important;
    box-shadow: {SHADOW_SM} !important;
}}
.stChatInputContainer {{
    background: {C.CARD} !important;
    border: 1px solid {C.BORDER_MD} !important;
    border-radius: 12px !important;
    box-shadow: {SHADOW_SM} !important;
}}
.stChatInputContainer:focus-within {{
    border-color: {C.TEAL} !important;
    box-shadow: 0 0 0 3px {C.TEAL_DIM} !important;
}}

/* ── Chip / action buttons ───────────────────────────────────────────────── */
.stButton > button {{
    background: {C.CARD} !important;
    border: 1px solid {C.BORDER} !important;
    color: {C.T3} !important;
    border-radius: 10px !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    padding: 9px 14px !important;
    width: 100% !important;
    text-align: left !important;
    /* Smooth cubic-bezier for professional feel */
    transition: background 0.22s cubic-bezier(.4,0,.2,1),
                border-color 0.22s cubic-bezier(.4,0,.2,1),
                color 0.22s cubic-bezier(.4,0,.2,1),
                box-shadow 0.22s cubic-bezier(.4,0,.2,1),
                transform 0.18s cubic-bezier(.4,0,.2,1) !important;
    box-shadow: {SHADOW_SM} !important;
    position: relative !important;
    overflow: hidden !important;
}}
/* Shimmer sweep on hover */
.stButton > button::after {{
    content: '' !important;
    position: absolute !important;
    top: 0 !important; left: -75% !important;
    width: 60% !important; height: 100% !important;
    background: linear-gradient(120deg, transparent 0%, rgba(0,196,154,0.14) 50%, transparent 100%) !important;
    transform: skewX(-18deg) !important;
    transition: left 0.55s ease !important;
    pointer-events: none !important;
}}
.stButton > button:hover::after {{ left: 130% !important; }}
.stButton > button:hover {{
    background: {C.TEAL_DIM} !important;
    border-color: {C.TEAL_BORDER} !important;
    color: {C.TEAL_TEXT} !important;
    box-shadow: 0 4px 16px rgba(0,196,154,0.18), 0 1px 3px rgba(0,0,0,0.06) !important;
    transform: translateY(-2px) !important;
}}
.stButton > button:active {{
    transform: translateY(0px) scale(0.985) !important;
    box-shadow: {SHADOW_SM} !important;
    transition-duration: 0.08s !important;
}}

/* ── Streamlit header / Deploy button ────────────────────────────────────── */
[data-testid="stHeader"] button,
[data-testid="stToolbarActions"] button,
[data-testid="stBaseButton-header"],
[data-testid="stDeployButton"] button,
button[data-testid*="deploy"],
button[kind="header"] {{
    background: rgba(0,196,154,0.08) !important;
    border: 1px solid rgba(0,196,154,0.28) !important;
    color: {C.TEAL_TEXT} !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.02em !important;
    padding: 6px 16px !important;
    transition: background 0.22s ease, color 0.22s ease,
                border-color 0.22s ease, box-shadow 0.22s ease,
                transform 0.18s cubic-bezier(.4,0,.2,1) !important;
    position: relative !important;
    overflow: hidden !important;
    cursor: pointer !important;
}}
[data-testid="stHeader"] button::after,
[data-testid="stBaseButton-header"]::after {{
    content: '' !important;
    position: absolute !important;
    inset: 0 !important;
    background: linear-gradient(135deg,rgba(0,196,154,0.15) 0%,transparent 70%) !important;
    opacity: 0 !important;
    transition: opacity 0.22s ease !important;
    pointer-events: none !important;
}}
[data-testid="stHeader"] button:hover,
[data-testid="stBaseButton-header"]:hover,
[data-testid="stDeployButton"] button:hover {{
    background: {C.TEAL} !important;
    color: #ffffff !important;
    border-color: {C.TEAL} !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(0,196,154,0.35), 0 2px 6px rgba(0,0,0,0.08) !important;
}}
[data-testid="stHeader"] button:hover::after {{ opacity: 1 !important; }}
[data-testid="stHeader"] button:active,
[data-testid="stBaseButton-header"]:active {{
    transform: translateY(0) scale(0.97) !important;
    transition-duration: 0.08s !important;
}}

/* ── Chat send button ────────────────────────────────────────────────────── */
[data-testid="stChatInputSubmitButton"] button,
[data-testid="stChatInput"] button {{
    background: {C.TEAL} !important;
    border: none !important;
    border-radius: 8px !important;
    transition: all 0.2s cubic-bezier(.4,0,.2,1) !important;
}}
[data-testid="stChatInputSubmitButton"] button:hover {{
    background: #00a880 !important;
    transform: scale(1.08) !important;
    box-shadow: 0 4px 14px rgba(0,196,154,0.4) !important;
}}

/* ── Expander arrow ──────────────────────────────────────────────────────── */
[data-testid="stExpander"] summary svg {{
    transition: transform 0.22s cubic-bezier(.4,0,.2,1) !important;
}}
[data-testid="stExpander"][open] summary svg {{ transform: rotate(90deg) !important; }}

/* ── Spinner ─────────────────────────────────────────────────────────────── */
.stSpinner > div {{ border-top-color: {C.TEAL} !important; }}

/* ── Header toolbar layout ───────────────────────────────────────────────── */
[data-testid="stHeader"] {{
    padding-right: 16px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: flex-end !important;
}}

/* ── Section labels consistency fix ─────────────────────────────────────── */
.nexus-section-label {{
    font-size: 0.63rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    color: {C.T5};
    margin-bottom: 6px;
    display: block;
}}

/* ── Animations ─────────────────────────────────────────────────────────── */
@keyframes nexus-pulse {{
    0%,100% {{ opacity:1; box-shadow: 0 0 0 0 rgba(220,38,38,0.4); }}
    50%     {{ opacity:.7; box-shadow: 0 0 0 5px rgba(220,38,38,0); }}
}}
@keyframes teal-pulse {{
    0%,100% {{ opacity:1; box-shadow: 0 0 0 0 rgba(0,196,154,0.4); }}
    50%     {{ opacity:.7; box-shadow: 0 0 0 5px rgba(0,196,154,0); }}
}}
@keyframes fadein {{
    from {{ opacity:0; transform:translateY(8px); }}
    to   {{ opacity:1; transform:translateY(0); }}
}}

/* ── Responsive ─────────────────────────────────────────────────────────── */
/* Tablet: 768-1024px */
@media (max-width: 1024px) {{
    .block-container {{ padding: 0 1.5rem 4rem !important; }}
    [data-testid="column"] {{ padding: 0 4px !important; }}
    [data-testid="stMetricValue"] {{ font-size: 1.6rem !important; }}
}}

/* Mobile landscape / large phone: 480-768px */
@media (max-width: 768px) {{
    .block-container {{ padding: 0 1rem 3.5rem !important; }}
    [data-testid="column"] {{ padding: 0 3px !important; }}
    [data-testid="stMetric"] {{ padding: 14px 14px 12px !important; }}
    [data-testid="stMetricValue"] {{ font-size: 1.4rem !important; }}
    [data-testid="stMetricLabel"] {{ font-size: 0.65rem !important; }}
}}

/* Mobile portrait: <480px */
@media (max-width: 480px) {{
    .block-container {{ padding: 0 0.6rem 3rem !important; }}
    [data-testid="stMetric"] {{ padding: 12px 12px 10px !important; border-radius: 10px !important; }}
    [data-testid="stMetricValue"] {{ font-size: 1.25rem !important; }}
    [data-testid="stExpander"] summary {{ padding: 12px 14px !important; font-size: 0.82rem !important; }}
    [data-testid="stExpander"] > div > div {{ padding: 12px 14px !important; }}
    .stButton > button {{ font-size: 0.75rem !important; padding: 8px 10px !important; }}
}}

/* Touch-friendly minimum tap targets */
@media (hover: none) and (pointer: coarse) {{
    .stButton > button {{ min-height: 44px !important; }}
    [data-testid="stChatInputSubmitButton"] button {{ min-height: 44px !important; min-width: 44px !important; }}
    summary {{ min-height: 44px !important; display: flex !important; align-items: center !important; }}
}}

</style>"""
