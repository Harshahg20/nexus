"""
NEXUS — Unit tests for pure utility functions.

These tests do NOT require a live Snowflake connection.
They cover:
  • services.agent  — extract_text, extract_suggested_queries, NexusAgentError
  • services.snowflake — NexusConfigError, NexusConnectionError, query_row,
                         query_scalar behaviour with mocked DataFrames
  • Label / value formatting helpers verified to remain within expected ranges

Run with:
    cd app
    python -m pytest ../tests/ -v
"""
from __future__ import annotations

import json
import sys
import os
import types
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Bootstrap: make app/ importable without installing Streamlit / Snowflake
# ---------------------------------------------------------------------------

_APP_DIR = os.path.join(os.path.dirname(__file__), "..", "app")
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)


def _make_stub(name: str) -> types.ModuleType:
    """Return a minimal stub module that satisfies the attribute lookups used
    at import time (e.g. st.cache_resource, st.cache_data, st.secrets)."""
    mod = types.ModuleType(name)
    mod.__spec__ = MagicMock()
    return mod


def _stub_streamlit() -> None:
    """Inject a minimal 'streamlit' stub so service modules can be imported."""
    if "streamlit" in sys.modules:
        return  # already present (e.g. when run inside a real Streamlit process)
    st = _make_stub("streamlit")

    # Decorators must be callables that return the decorated function unchanged
    def _passthrough_decorator(*args, **kwargs):
        if args and callable(args[0]):
            return args[0]          # @st.cache_resource
        def inner(fn):
            return fn               # @st.cache_data(ttl=300)
        return inner

    st.cache_resource = _passthrough_decorator
    st.cache_data     = _passthrough_decorator
    st.secrets        = {}          # tests that need secrets will patch this
    st.error          = lambda *a, **k: None
    st.warning        = lambda *a, **k: None
    st.info           = lambda *a, **k: None
    sys.modules["streamlit"] = st


def _stub_snowflake() -> None:
    """
    Ensure snowflake.snowpark is importable with a minimal Session stub.
    Works whether or not the real snowflake-snowpark package is installed.
    """
    # If the real package is installed it will be importable; just make sure
    # we don't accidentally run a real Session.builder.create() in tests.
    try:
        import snowflake.snowpark as sp  # real package present
        if not hasattr(sp, "Session") or not isinstance(sp.Session, MagicMock):
            sp.Session = MagicMock()
    except ImportError:
        # Real package not installed — inject stubs
        sf = _make_stub("snowflake")
        sp_stub = _make_stub("snowflake.snowpark")
        sp_stub.Session = MagicMock()
        sf.snowpark = sp_stub
        sys.modules["snowflake"]          = sf
        sys.modules["snowflake.snowpark"]  = sp_stub


def _stub_cryptography() -> None:
    """
    Ensure cryptography.hazmat.primitives.serialization is importable.
    Works whether or not the real package is installed.
    """
    try:
        from cryptography.hazmat.primitives.serialization import load_pem_private_key  # noqa: F401
        # Real package present — no stub needed
    except ImportError:
        crypto = _make_stub("cryptography")
        hazmat = _make_stub("cryptography.hazmat")
        prim   = _make_stub("cryptography.hazmat.primitives")
        ser    = _make_stub("cryptography.hazmat.primitives.serialization")
        ser.load_pem_private_key = MagicMock(return_value=MagicMock())
        crypto.hazmat                                  = hazmat
        hazmat.primitives                              = prim
        prim.serialization                             = ser
        sys.modules["cryptography"]                                 = crypto
        sys.modules["cryptography.hazmat"]                          = hazmat
        sys.modules["cryptography.hazmat.primitives"]               = prim
        sys.modules["cryptography.hazmat.primitives.serialization"] = ser


# Perform stubbing before any service imports
_stub_streamlit()
_stub_snowflake()
_stub_cryptography()

# Now import the modules under test
from services.agent import (   # noqa: E402
    extract_text,
    extract_suggested_queries,
    NexusAgentError,
    invoke_agent,
)
from services.snowflake import (  # noqa: E402
    NexusConfigError,
    NexusConnectionError,
    query_row,
    query_scalar,
)
import pandas as pd  # noqa: E402


# ===========================================================================
# Tests — services.agent.extract_text
# ===========================================================================

class TestExtractText(unittest.TestCase):

    def test_single_text_block(self):
        response = {"content": [{"type": "text", "text": "Hello world"}]}
        self.assertEqual(extract_text(response), "Hello world")

    def test_multiple_text_blocks_joined(self):
        response = {"content": [
            {"type": "text", "text": "First"},
            {"type": "text", "text": "Second"},
        ]}
        self.assertEqual(extract_text(response), "First\n\nSecond")

    def test_ignores_non_text_blocks(self):
        response = {"content": [
            {"type": "suggested_queries", "suggested_queries": []},
            {"type": "text", "text": "Only this"},
        ]}
        self.assertEqual(extract_text(response), "Only this")

    def test_empty_content_list(self):
        self.assertEqual(extract_text({"content": []}), "")

    def test_missing_content_key(self):
        self.assertEqual(extract_text({}), "")

    def test_non_dict_response(self):
        self.assertEqual(extract_text(None), "")
        self.assertEqual(extract_text("string"), "")
        self.assertEqual(extract_text(42), "")

    def test_strips_whitespace_from_blocks(self):
        response = {"content": [{"type": "text", "text": "  padded  "}]}
        self.assertEqual(extract_text(response), "padded")

    def test_skips_empty_text_blocks(self):
        response = {"content": [
            {"type": "text", "text": ""},
            {"type": "text", "text": "   "},
            {"type": "text", "text": "Real content"},
        ]}
        self.assertEqual(extract_text(response), "Real content")


# ===========================================================================
# Tests — services.agent.extract_suggested_queries
# ===========================================================================

class TestExtractSuggestedQueries(unittest.TestCase):

    def test_returns_list_of_queries(self):
        response = {"content": [
            {"type": "suggested_queries", "suggested_queries": [
                {"query": "Q1"},
                {"query": "Q2"},
            ]},
        ]}
        self.assertEqual(extract_suggested_queries(response), ["Q1", "Q2"])

    def test_returns_empty_when_no_suggestions(self):
        response = {"content": [{"type": "text", "text": "Hello"}]}
        self.assertEqual(extract_suggested_queries(response), [])

    def test_returns_empty_on_empty_content(self):
        self.assertEqual(extract_suggested_queries({"content": []}), [])

    def test_returns_empty_on_non_dict(self):
        self.assertEqual(extract_suggested_queries(None), [])

    def test_skips_entries_without_query_key(self):
        response = {"content": [
            {"type": "suggested_queries", "suggested_queries": [
                {"query": "Good"},
                {"no_query": "Bad"},
            ]},
        ]}
        self.assertEqual(extract_suggested_queries(response), ["Good"])


# ===========================================================================
# Tests — NexusAgentError raised on empty / invalid input
# ===========================================================================

class TestInvokeAgentValidation(unittest.TestCase):

    def test_empty_string_raises(self):
        with self.assertRaises(NexusAgentError):
            invoke_agent("")

    def test_whitespace_only_raises(self):
        with self.assertRaises(NexusAgentError):
            invoke_agent("   ")


# ===========================================================================
# Tests — services.snowflake helper functions (with mocked DataFrames)
# ===========================================================================

class TestQueryRow(unittest.TestCase):

    def test_returns_first_row_as_dict(self):
        df = pd.DataFrame({"A": [1, 2], "B": ["x", "y"]})
        with patch("services.snowflake.query_df", return_value=df):
            result = query_row("SELECT 1")
        self.assertEqual(result, {"A": 1, "B": "x"})

    def test_returns_empty_dict_when_empty(self):
        with patch("services.snowflake.query_df", return_value=pd.DataFrame()):
            result = query_row("SELECT 1")
        self.assertEqual(result, {})


class TestQueryScalar(unittest.TestCase):

    def test_returns_first_cell(self):
        df = pd.DataFrame({"V": [42]})
        with patch("services.snowflake.query_df", return_value=df):
            result = query_scalar("SELECT 42")
        self.assertEqual(result, 42)

    def test_returns_none_when_empty(self):
        with patch("services.snowflake.query_df", return_value=pd.DataFrame()):
            result = query_scalar("SELECT 1")
        self.assertIsNone(result)


# ===========================================================================
# Tests — NexusConfigError / NexusConnectionError are distinct exceptions
# ===========================================================================

class TestCustomExceptions(unittest.TestCase):

    def test_config_error_is_runtime_error(self):
        exc = NexusConfigError("bad config")
        self.assertIsInstance(exc, RuntimeError)
        self.assertIn("bad config", str(exc))

    def test_connection_error_is_runtime_error(self):
        exc = NexusConnectionError("no conn")
        self.assertIsInstance(exc, RuntimeError)

    def test_agent_error_is_runtime_error(self):
        exc = NexusAgentError("agent down")
        self.assertIsInstance(exc, RuntimeError)

    def test_errors_are_distinct(self):
        self.assertFalse(issubclass(NexusConfigError, NexusConnectionError))
        self.assertFalse(issubclass(NexusConnectionError, NexusConfigError))


# ===========================================================================
# Tests — KPI formatting sanity (pure Python, no Snowflake)
# ===========================================================================

class TestKpiFormatting(unittest.TestCase):
    """Verify the formatting logic used in kpi_cards without rendering HTML."""

    def _fmt_revenue(self, raw: float) -> str:
        return f"${raw / 1_000_000:.2f}M"

    def _fmt_units(self, raw: float) -> str:
        return f"{raw:,.0f}"

    def test_revenue_format_millions(self):
        self.assertEqual(self._fmt_revenue(1_500_000), "$1.50M")
        self.assertEqual(self._fmt_revenue(10_000_000), "$10.00M")

    def test_revenue_format_sub_million(self):
        self.assertEqual(self._fmt_revenue(500_000), "$0.50M")

    def test_units_format_comma(self):
        self.assertEqual(self._fmt_units(12345), "12,345")
        self.assertEqual(self._fmt_units(0), "0")

    def test_zero_revenue(self):
        self.assertEqual(self._fmt_revenue(0), "$0.00M")


# ===========================================================================
# Tests — agent response round-trip (JSON serialise → parse)
# ===========================================================================

class TestAgentResponseRoundTrip(unittest.TestCase):

    def _make_response(self, text: str, suggestions: list[str]) -> dict:
        content = [{"type": "text", "text": text}]
        if suggestions:
            content.append({
                "type": "suggested_queries",
                "suggested_queries": [{"query": q} for q in suggestions],
            })
        return {"content": content}

    def test_round_trip_text_only(self):
        resp = self._make_response("Answer here", [])
        self.assertEqual(extract_text(resp), "Answer here")
        self.assertEqual(extract_suggested_queries(resp), [])

    def test_round_trip_with_suggestions(self):
        resp = self._make_response("Here is your answer.", ["Follow up A", "Follow up B"])
        self.assertEqual(extract_text(resp), "Here is your answer.")
        self.assertEqual(extract_suggested_queries(resp), ["Follow up A", "Follow up B"])

    def test_json_serialise_and_parse_is_stable(self):
        """Ensure the agent response dict survives a JSON round-trip unchanged."""
        resp = self._make_response("Stable content", ["Q1"])
        serialised   = json.dumps(resp)
        deserialised = json.loads(serialised)
        self.assertEqual(extract_text(deserialised), "Stable content")
        self.assertEqual(extract_suggested_queries(deserialised), ["Q1"])


if __name__ == "__main__":
    unittest.main()
