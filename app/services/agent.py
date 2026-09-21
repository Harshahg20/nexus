"""
NEXUS — Cortex Agent service layer.

Wraps DATA_AGENT_RUN calls to the NEXUS_SUPPLY_CHAIN_AGENT.

Modes
-----
• invoke_agent(question)   — blocking call with hard timeout (default 60 s).
                             Use in contexts where a spinner is shown.
• stream_agent(question)   — generator that yields text tokens as they arrive.
                             Use with st.write_stream() for perceived low-latency.

Error strategy
--------------
All errors are converted to NexusAgentError with a user-readable message so
callers never display raw Python tracebacks to end users.
"""
from __future__ import annotations

import json
import concurrent.futures
import streamlit as st
from services.snowflake import get_session, NexusConnectionError, NexusConfigError

AGENT_FQN    = "NEXUS_DB.PUBLIC.NEXUS_SUPPLY_CHAIN_AGENT"
AGENT_TIMEOUT = 60          # seconds — tune up if your warehouse is cold-starting
_EXECUTOR    = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="nexus-agent")


class NexusAgentError(RuntimeError):
    """Agent invocation or response-parsing failure."""


# ── Request helpers ───────────────────────────────────────────────────────────

def _build_body(question: str, thread_id: int | None, stream: bool) -> str:
    """Return a JSON body string safe to embed in a Snowflake SQL literal."""
    messages = [{"role": "user", "content": [{"type": "text", "text": question}]}]
    body: dict = {"messages": messages, "stream": stream}
    if thread_id is not None:
        body["thread_id"] = thread_id
        body["parent_message_id"] = 0
    try:
        return json.dumps(body).replace("'", "''")
    except (TypeError, ValueError) as exc:
        raise NexusAgentError(f"Failed to serialize agent request: {exc}") from exc


def _make_sql(body_json: str) -> str:
    return (
        f"SELECT SNOWFLAKE.CORTEX.DATA_AGENT_RUN("
        f"  '{AGENT_FQN}',"
        f"  '{body_json}',"
        f"  TRUE"
        f") AS resp"
    )


def _get_session_safe():
    """Wrap get_session so connection errors surface as NexusAgentError."""
    try:
        return get_session()
    except (NexusConfigError, NexusConnectionError) as exc:
        raise NexusAgentError(str(exc)) from exc
    except Exception as exc:
        raise NexusAgentError(
            "The NEXUS agent could not be reached — Snowflake connection failed. "
            "Check your credentials and try again."
        ) from exc


# ── Blocking invocation (with hard timeout) ───────────────────────────────────

def _run_blocking(question: str, thread_id: int | None) -> dict:
    """Execute a non-streaming agent call and return the parsed response dict."""
    body_json = _build_body(question, thread_id, stream=False)
    sql       = _make_sql(body_json)
    session   = _get_session_safe()
    try:
        rows = session.sql(sql).collect()
    except Exception as exc:
        raise NexusAgentError(
            "The NEXUS agent query failed. "
            "Check your Snowflake connection and ensure the Cortex Agent is deployed."
        ) from exc

    if not rows:
        raise NexusAgentError(
            "The agent returned an empty response. "
            "The Cortex Agent may be unavailable — please try again."
        )
    try:
        raw = str(rows[0]["RESP"])
        return json.loads(raw)
    except (KeyError, IndexError):
        raise NexusAgentError(
            "Unexpected agent response format (missing RESP column). "
            "The agent schema may have changed."
        )
    except json.JSONDecodeError as exc:
        raise NexusAgentError(
            f"Agent response could not be parsed as JSON ({exc}). "
            "The Cortex Agent may have returned an error message."
        ) from exc


def invoke_agent(
    question: str,
    thread_id: int | None = None,
    timeout: float = AGENT_TIMEOUT,
) -> dict:
    """
    Call the NEXUS Cortex agent (blocking, with hard timeout).

    Parameters
    ----------
    question  : Natural-language query (must be non-empty).
    thread_id : Optional conversation thread ID for multi-turn sessions.
    timeout   : Hard wall-clock timeout in seconds (default 60 s).
                Raises NexusAgentError on timeout — no silent hang.

    Returns the parsed agent response dict.
    Raises NexusAgentError on any failure.
    """
    if not question or not question.strip():
        raise NexusAgentError("Question must not be empty.")

    future = _EXECUTOR.submit(_run_blocking, question, thread_id)
    try:
        return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        future.cancel()
        raise NexusAgentError(
            f"The agent did not respond within {timeout:.0f} seconds. "
            "Your Snowflake warehouse may be resuming — try again in a moment, "
            "or ask a shorter question."
        )
    except NexusAgentError:
        raise
    except Exception as exc:
        raise NexusAgentError(
            "An unexpected error occurred while contacting the NEXUS agent."
        ) from exc


# ── Streaming invocation (yields text tokens) ─────────────────────────────────

def stream_agent(
    question: str,
    thread_id: int | None = None,
    timeout: float = AGENT_TIMEOUT,
):
    """
    Generator that yields text token strings from a streaming agent response.

    Use with Streamlit's st.write_stream():
        response_text = st.write_stream(stream_agent("your question"))

    Each yielded value is a non-empty string chunk.  If no streaming data
    arrives within *timeout* seconds, NexusAgentError is raised.

    Falls back to the blocking path if streaming is not supported by the
    installed Snowflake connector version.
    """
    if not question or not question.strip():
        raise NexusAgentError("Question must not be empty.")

    body_json = _build_body(question, thread_id, stream=True)
    sql       = _make_sql(body_json)
    session   = _get_session_safe()

    try:
        # Use the underlying connector cursor for lazy row-by-row iteration
        # (avoids collecting all rows into memory before yielding the first token).
        raw_conn = session.connection
        cursor   = raw_conn.cursor()
        try:
            cursor.execute(sql)
            deadline = __import__("time").time() + timeout
            yielded_any = False

            for row in cursor:
                if __import__("time").time() > deadline:
                    raise NexusAgentError(
                        f"Streaming response exceeded {timeout:.0f} s timeout."
                    )
                try:
                    chunk = json.loads(str(row[0]))
                except (json.JSONDecodeError, IndexError):
                    continue

                text = extract_text(chunk)
                if text:
                    yielded_any = True
                    yield text

            if not yielded_any:
                raise NexusAgentError(
                    "The agent stream produced no text. "
                    "Try again or rephrase your question."
                )
        finally:
            cursor.close()

    except NexusAgentError:
        raise
    except AttributeError:
        # Older connector without .connection attribute — fall back to blocking
        result = invoke_agent(question, thread_id, timeout=timeout)
        text   = extract_text(result)
        if text:
            yield text
        else:
            raise NexusAgentError("The agent returned no readable text.")
    except Exception as exc:
        raise NexusAgentError(
            "The streaming agent connection failed. "
            "Check your Snowflake connection and try again."
        ) from exc


# ── Response parsing helpers ──────────────────────────────────────────────────

def extract_text(response: dict) -> str:
    """
    Pull all text blocks from an agent response.

    Returns an empty string if the response contains no text content.
    Safe against None, non-dict, or malformed inputs.
    """
    if not isinstance(response, dict):
        return ""
    parts = []
    for block in response.get("content", []):
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text", "").strip()
            if text:
                parts.append(text)
    return "\n\n".join(parts)


def extract_suggested_queries(response: dict) -> list[str]:
    """
    Pull suggested follow-up queries from an agent response.

    Returns an empty list if none are present.
    """
    if not isinstance(response, dict):
        return []
    for block in response.get("content", []):
        if isinstance(block, dict) and block.get("type") == "suggested_queries":
            return [
                q["query"]
                for q in block.get("suggested_queries", [])
                if isinstance(q, dict) and "query" in q
            ]
    return []
