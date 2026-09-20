from __future__ import annotations
import json
import streamlit as st
from services.snowflake import get_session

AGENT_FQN = "NEXUS_DB.PUBLIC.NEXUS_SUPPLY_CHAIN_AGENT"


def invoke_agent(question: str, thread_id: int | None = None) -> dict:
    """Call the NEXUS agent via DATA_AGENT_RUN and return the parsed response."""
    messages = [{"role": "user", "content": [{"type": "text", "text": question}]}]
    body = {"messages": messages, "stream": False}

    if thread_id is not None:
        body["thread_id"] = thread_id
        body["parent_message_id"] = 0

    body_json = json.dumps(body).replace("'", "''")
    sql = (
        f"SELECT SNOWFLAKE.CORTEX.DATA_AGENT_RUN("
        f"  '{AGENT_FQN}',"
        f"  '{body_json}',"
        f"  TRUE"
        f") AS resp"
    )

    session = get_session()
    rows = session.sql(sql).collect()
    raw = str(rows[0]["RESP"])
    return json.loads(raw)


def extract_text(response: dict) -> str:
    """Pull all text blocks from the agent response content."""
    parts = []
    for block in response.get("content", []):
        if block.get("type") == "text":
            parts.append(block["text"])
    return "\n\n".join(parts)


def extract_suggested_queries(response: dict) -> list[str]:
    """Pull suggested follow-up queries from the response."""
    for block in response.get("content", []):
        if block.get("type") == "suggested_queries":
            return [q["query"] for q in block.get("suggested_queries", [])]
    return []
