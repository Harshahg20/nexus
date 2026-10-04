from __future__ import annotations
import streamlit as st
from services.agent import (
    stream_agent,
    extract_suggested_queries,
    invoke_agent,
    NexusAgentError,
)
from ui.theme import C, FONT
from ui.compat import st_rerun, st_toast

# (label shown on button, full question submitted to agent)
EXAMPLE_QUESTIONS: list[tuple[str, str]] = [
    ("→ Critical part suppliers?",      "Which suppliers provide critical parts?"),
    ("→ PART-104 dependencies?",        "What products depend on PART-104?"),
    ("→ SUP-001 failure impact?",       "What breaks if SUP-001 becomes unavailable?"),
    ("→ PART-104 customer exposure?",   "Which customers are exposed to PART-104?"),
    ("→ Available mitigations?",        "What mitigation options are available?"),
    ("→ PORT-TYO disruption impact?",   "What happens if PORT-TYO is disrupted?"),
]

_AGENT_NOTE = (
    "Powered by **Snowflake Cortex AI** and your governed semantic layer. "
    "Answers reflect data in Snowflake — not real-time external sources."
)


def render_sidebar_input() -> None:
    """
    Renders the Ask NEXUS text input inside the sidebar.
    Called only when st.chat_input is NOT available (SiS warehouse runtime).
    This keeps the input always visible regardless of scroll position.
    """
    if hasattr(st, "chat_input"):
        return  # Modern Streamlit: chat_input auto-pins to bottom; nothing needed here

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    st.markdown(
        f"<div style='margin-top:4px;margin-bottom:6px;"
        f"font-size:0.62rem;font-weight:700;text-transform:uppercase;"
        f"letter-spacing:0.14em;color:{C.TEAL};font-family:{FONT};'>"
        f"Ask NEXUS (Cortex AI)</div>",
        unsafe_allow_html=True,
    )
    with st.form(key="nexus_sidebar_chat_form", clear_on_submit=True):
        prompt_text = st.text_input(
            "",
            placeholder="e.g. What breaks if SUP-001 fails?",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Ask ▶", use_container_width=True)
    if submitted and prompt_text.strip():
        _submit(prompt_text.strip())
        st_rerun()


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

    # (Quick prompts live in the fixed bottom bar — click 💡 to reveal)

    # ── Chat history ──────────────────────────────────────────────────────────
    _HAS_CHAT_MSG = hasattr(st, "chat_message")
    for msg in st.session_state.chat_messages:
        if _HAS_CHAT_MSG:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        else:
            prefix = "🧑 **You**" if msg["role"] == "user" else "🤖 **NEXUS**"
            st.markdown(f"{prefix}: {msg['content']}")
            st.divider()

    # ── Input ────────────────────────────────────────────────────────────────
    if hasattr(st, "chat_input"):
        # Modern Streamlit / localhost: auto-pins to bottom of page
        if prompt := st.chat_input("Ask NEXUS about your supply chain…"):
            stripped = prompt.strip()
            if stripped:
                _submit_streaming(stripped)
            else:
                st_toast("Please enter a question before submitting.", icon="✏️")
    else:
        # SiS: bottom padding so fixed bar doesn't cover last content item
        st.markdown("<div style='height:80px'></div>", unsafe_allow_html=True)

    # ── Fixed bottom bar (always renders for SiS) ─────────────────────────
    if not hasattr(st, "chat_input"):
        _render_fixed_bar()

    # ── Provenance note ───────────────────────────────────────────────────────
    st.caption(_AGENT_NOTE)


def _submit_streaming(question: str) -> None:
    """
    Stream the agent response token-by-token using st.write_stream.

    Falls back to a blocking call (with spinner) if streaming fails.
    The full streamed text is appended to chat_messages so history renders
    correctly on re-render.
    """
    st.session_state.chat_messages.append({"role": "user", "content": question})

    if hasattr(st, "chat_message"):
        with st.chat_message("user"):
            st.markdown(question)
    else:
        st.markdown(f"🧑 **You**: {question}")

    _ctx = st.chat_message("assistant") if hasattr(st, "chat_message") else st.container()
    with _ctx:
        try:
            if hasattr(st, "write_stream"):
                response_text: str = st.write_stream(stream_agent(question))
            else:
                with st.spinner("NEXUS is analyzing…"):
                    response = invoke_agent(question)
                from services.agent import extract_text
                response_text = extract_text(response)
                st.markdown(response_text)

            # Fetch suggested queries from a lightweight blocking call
            # (stream response does not include them in every chunk)
            suggestions = _fetch_suggestions(question)
            if suggestions:
                suggestion_md = "\n\n---\n**Suggested follow-ups:**\n" + "".join(
                    f"- {s}\n" for s in suggestions
                )
                st.markdown(suggestion_md)
                response_text += suggestion_md

            st.session_state.chat_messages.append(
                {"role": "assistant", "content": response_text}
            )

        except NexusAgentError as exc:
            _show_agent_error(exc)
        except Exception:
            _show_generic_error()


def _submit(question: str) -> None:
    """
    Blocking submit used by example-question chip buttons.
    (Chips trigger st.rerun() after this, so streaming is not possible there.)
    """
    st.session_state.chat_messages.append({"role": "user", "content": question})
    try:
        with st.spinner("NEXUS is analyzing your supply chain…"):
            response = invoke_agent(question)

        from services.agent import extract_text  # local import avoids circular
        text        = extract_text(response)
        suggestions = extract_suggested_queries(response)

        if not text:
            text = (
                "The agent returned a response but contained no readable text. "
                "Try rephrasing your question."
            )

        answer = text
        if suggestions:
            answer += "\n\n---\n**Suggested follow-ups:**\n"
            for s in suggestions:
                answer += f"- {s}\n"

        st.session_state.chat_messages.append({"role": "assistant", "content": answer})

    except NexusAgentError as exc:
        st.session_state.chat_messages.append(
            {"role": "assistant", "content": _error_md(exc)}
        )
    except Exception:
        st.session_state.chat_messages.append(
            {"role": "assistant", "content": _generic_error_md()}
        )


def _fetch_suggestions(question: str) -> list[str]:
    """
    Attempt to retrieve suggested follow-ups from the blocking agent response.
    Returns [] on any failure — suggestions are non-critical.
    """
    try:
        response = invoke_agent(question)
        return extract_suggested_queries(response)
    except Exception:
        return []


def _error_md(exc: NexusAgentError) -> str:
    return (
        f"⚠ **NEXUS could not answer this question.**\n\n"
        f"{exc}\n\n"
        "*If this persists, verify the Cortex Agent deployment and your Snowflake connection.*"
    )


def _generic_error_md() -> str:
    return (
        "⚠ **An unexpected error occurred.**\n\n"
        "Please try again. If the problem persists, check the Streamlit server log."
    )


def _show_agent_error(exc: NexusAgentError) -> None:
    st.error(_error_md(exc))
    st.session_state.chat_messages.append(
        {"role": "assistant", "content": _error_md(exc)}
    )


def _show_generic_error() -> None:
    st.error(_generic_error_md())
    st.session_state.chat_messages.append(
        {"role": "assistant", "content": _generic_error_md()}
    )


def _render_fixed_bar() -> None:
    """
    Fixed bottom chat bar for SiS (no st.chat_input).
    Uses plain st.button + st.text_input — NO st.form, works in all SiS versions.
    The entire bar is CSS position:fixed so it never scrolls away.
    """
    if "nexus_show_prompts" not in st.session_state:
        st.session_state.nexus_show_prompts = True
    if "fbar_ver" not in st.session_state:
        st.session_state.fbar_ver = 0   # bumped after submit to clear input field

    show = st.session_state.nexus_show_prompts

    # ── Quick-prompt banner (default open) ───────────────────────────────
    if show:
        h_label, h_close = st.columns([11, 1])
        with h_label:
            st.markdown(
                f"<p style='font-size:0.62rem;font-weight:700;text-transform:uppercase;"
                f"letter-spacing:0.14em;color:{C.T4};margin:4px 0 6px;"
                f"font-family:{FONT};'>✦ Try asking — click any prompt</p>",
                unsafe_allow_html=True,
            )
        with h_close:
            if st.button("✕", key="fbar_close", help="Dismiss prompts"):
                st.session_state.nexus_show_prompts = False
                st_rerun()

        chip_cols = st.columns(3)
        for i, (chip_label, question) in enumerate(EXAMPLE_QUESTIONS):
            with chip_cols[i % 3]:
                if st.button(chip_label, key=f"fbar_chip_{i}"):
                    _submit(question)
                    st_rerun()

        st.markdown(
            f"<div style='height:1px;background:{C.BORDER};margin:8px 0 4px;'></div>",
            unsafe_allow_html=True,
        )

    # ── Input row (always visible) ────────────────────────────────────────
    c_bulb, c_input, c_send = st.columns([1, 9, 1])
    with c_bulb:
        if st.button("💡", key="fbar_toggle", help="Toggle quick prompts"):
            st.session_state.nexus_show_prompts = not show
            st_rerun()
    with c_input:
        # version-keyed so bumping fbar_ver clears the field after submit
        typed = st.text_input(
            "ask_nexus_bar",
            placeholder="Ask NEXUS about your supply chain…",
            label_visibility="collapsed",
            key=f"fbar_input_{st.session_state.fbar_ver}",
        )
    with c_send:
        if st.button("▶", key="fbar_send"):
            if typed and typed.strip():
                st.session_state.fbar_ver += 1
                st.session_state.nexus_show_prompts = True
                _submit(typed.strip())
                st_rerun()

