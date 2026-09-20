from __future__ import annotations
import streamlit as st
import streamlit.components.v1 as components
from services.agent import invoke_agent, extract_text, extract_suggested_queries
from ui.theme import C, FONT, SHADOW_MD

EXAMPLE_QUESTIONS = [
    "→  Which suppliers provide critical parts?",
    "→  What products depend on PART-104?",
    "→  What breaks if SUP-001 becomes unavailable?",
    "→  Which customers are exposed to PART-104?",
    "→  What mitigation options are available?",
    "→  What happens if PORT-TYO is disrupted?",
]

# Display labels without the → prefix (shown separately on hover via CSS)
_Q_CLEAN = [q.replace("→  ", "") for q in EXAMPLE_QUESTIONS]


def render():
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    # ── Section label + title ─────────────────────────────────────────────────
    st.markdown(
        f"<p style='font-size:0.63rem;font-weight:700;text-transform:uppercase;"
        f"letter-spacing:0.18em;color:{C.T5};margin-bottom:6px;font-family:{FONT};'>AI-Powered Intelligence</p>"
        f"<h3 style='font-size:1.35rem;font-weight:800;color:{C.T1};letter-spacing:-0.02em;"
        f"margin-bottom:4px;font-family:{FONT};'>Ask <span style=\"color:{C.TEAL};\">NEXUS</span></h3>"
        f"<p style='font-size:0.82rem;color:{C.T4};margin-bottom:20px;font-family:{FONT};'>"
        f"Ask anything about your supply chain in plain English — powered by Snowflake Cortex AI "
        f"and your governed semantic layer.</p>",
        unsafe_allow_html=True,
    )

    # ── Example questions header ──────────────────────────────────────────────
    st.markdown(
        f"<p style='font-size:0.62rem;font-weight:700;text-transform:uppercase;"
        f"letter-spacing:0.15em;color:{C.T5};margin-bottom:8px;font-family:{FONT};'>"
        f"Try asking</p>",
        unsafe_allow_html=True,
    )

    chip_cols = st.columns(3)
    for i, (q, label) in enumerate(zip(EXAMPLE_QUESTIONS, _Q_CLEAN)):
        with chip_cols[i % 3]:
            if st.button(q, key=f"nexus_chip_{i}"):
                _submit(label)
                st.rerun()

    st.write("")

    # ── Chat history ──────────────────────────────────────────────────────────
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask NEXUS about your supply chain…"):
        _submit(prompt)
        st.rerun()


def _submit(question: str):
    st.session_state.chat_messages.append({"role": "user", "content": question})
    try:
        with st.spinner("NEXUS is analyzing your supply chain…"):
            response = invoke_agent(question)
        text        = extract_text(response)
        suggestions = extract_suggested_queries(response)
        answer      = text
        if suggestions:
            answer += "\n\n---\n**Suggested follow-ups:**\n"
            for s in suggestions:
                answer += f"- {s}\n"
        st.session_state.chat_messages.append({"role": "assistant", "content": answer})
    except Exception as e:
        st.session_state.chat_messages.append(
            {"role": "assistant", "content": f"⚠ Error contacting NEXUS agent: {e}"}
        )
