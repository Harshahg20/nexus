import streamlit as st
from services.agent import invoke_agent, extract_text, extract_suggested_queries

EXAMPLE_QUESTIONS = [
    "Which suppliers provide critical parts?",
    "What products depend on PART-104?",
    "What breaks if SUP-001 becomes unavailable?",
    "Which customers are exposed to PART-104?",
    "What mitigation options are available?",
    "What happens if PORT-TYO is disrupted?",
]


def render():
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    st.markdown(
        '<div style="color:#8892b0; font-size:0.75rem; margin-bottom:8px;">'
        "Ask about suppliers, dependencies, disruptions, customers, or mitigation tradeoffs.</div>",
        unsafe_allow_html=True,
    )

    with st.expander("Example questions", expanded=False):
        for q in EXAMPLE_QUESTIONS:
            if st.button(q, key=f"eq_{q[:20]}"):
                _submit(q)
                st.rerun()

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask NEXUS..."):
        _submit(prompt)
        st.rerun()


def _submit(question: str):
    st.session_state.chat_messages.append({"role": "user", "content": question})
    try:
        with st.spinner("NEXUS is analyzing..."):
            response = invoke_agent(question)
        text = extract_text(response)
        suggestions = extract_suggested_queries(response)
        answer = text
        if suggestions:
            answer += "\n\n---\n**Follow-up questions:**\n"
            for s in suggestions:
                answer += f"- {s}\n"
        st.session_state.chat_messages.append({"role": "assistant", "content": answer})
    except Exception as e:
        st.session_state.chat_messages.append(
            {"role": "assistant", "content": f"Error contacting NEXUS agent: {e}"}
        )
