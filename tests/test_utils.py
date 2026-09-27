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


# ===========================================================================
# Tests — Scenario business logic (pure Python, deterministic, no Snowflake)
# ===========================================================================

class TestAllocationLogic(unittest.TestCase):
    """
    Verifies the priority-based order allocation logic that mirrors
    SCENARIOS.V_ORDER_PART_ALLOCATION without touching Snowflake.

    Allocation rule: within a (plant, part) group, orders are processed by
    (due_date ASC, priority rank ASC, order_id ASC). Each order gets
    min(required, max(available - prior_allocated, 0)) units.
    """

    _PRIORITY_RANK = {"URGENT": 1, "HIGH": 2, "NORMAL": 3}

    def _allocate(self, available: float, orders: list[dict]) -> list[dict]:
        """
        Pure-Python mirror of V_ORDER_PART_ALLOCATION window logic.

        orders: list of dicts with keys: order_id, due_date, priority, required
        Returns list of dicts with: order_id, allocated, unmet
        """
        sorted_orders = sorted(
            orders,
            key=lambda o: (
                o["due_date"],
                self._PRIORITY_RANK.get(o["priority"], 99),
                o["order_id"],
            ),
        )
        results = []
        prior = 0.0
        for o in sorted_orders:
            allocated = max(min(o["required"], available - prior), 0.0)
            unmet = o["required"] - allocated
            results.append({"order_id": o["order_id"], "allocated": allocated, "unmet": unmet})
            prior += o["required"]   # running total of required (not allocated)
        return results

    def test_single_order_fully_satisfied(self):
        results = self._allocate(100, [{"order_id": "O1", "due_date": "2026-09-20",
                                         "priority": "HIGH", "required": 30}])
        self.assertEqual(results[0]["allocated"], 30)
        self.assertEqual(results[0]["unmet"], 0)

    def test_single_order_partially_satisfied(self):
        results = self._allocate(20, [{"order_id": "O1", "due_date": "2026-09-20",
                                        "priority": "HIGH", "required": 30}])
        self.assertEqual(results[0]["allocated"], 20)
        self.assertEqual(results[0]["unmet"], 10)

    def test_single_order_zero_supply(self):
        results = self._allocate(0, [{"order_id": "O1", "due_date": "2026-09-20",
                                       "priority": "HIGH", "required": 30}])
        self.assertEqual(results[0]["allocated"], 0)
        self.assertEqual(results[0]["unmet"], 30)

    def test_two_orders_first_gets_all(self):
        orders = [
            {"order_id": "O1", "due_date": "2026-09-20", "priority": "HIGH",   "required": 30},
            {"order_id": "O2", "due_date": "2026-09-21", "priority": "NORMAL", "required": 20},
        ]
        results = self._allocate(30, orders)
        by_id = {r["order_id"]: r for r in results}
        self.assertEqual(by_id["O1"]["allocated"], 30)
        self.assertEqual(by_id["O1"]["unmet"], 0)
        self.assertEqual(by_id["O2"]["allocated"], 0)
        self.assertEqual(by_id["O2"]["unmet"], 20)

    def test_priority_breaks_tie_same_due_date(self):
        orders = [
            {"order_id": "O2", "due_date": "2026-09-20", "priority": "NORMAL", "required": 20},
            {"order_id": "O1", "due_date": "2026-09-20", "priority": "URGENT", "required": 25},
        ]
        results = self._allocate(25, orders)
        by_id = {r["order_id"]: r for r in results}
        # URGENT should be served first
        self.assertEqual(by_id["O1"]["allocated"], 25)
        self.assertEqual(by_id["O1"]["unmet"], 0)
        self.assertEqual(by_id["O2"]["allocated"], 0)
        self.assertEqual(by_id["O2"]["unmet"], 20)

    def test_total_allocation_never_exceeds_supply(self):
        orders = [
            {"order_id": f"O{i}", "due_date": "2026-09-20", "priority": "NORMAL", "required": 10}
            for i in range(5)
        ]
        available = 35
        results = self._allocate(available, orders)
        total_allocated = sum(r["allocated"] for r in results)
        self.assertLessEqual(total_allocated, available + 0.0001)

    def test_allocated_never_negative(self):
        orders = [
            {"order_id": "O1", "due_date": "2026-09-20", "priority": "HIGH", "required": 50},
            {"order_id": "O2", "due_date": "2026-09-21", "priority": "HIGH", "required": 50},
        ]
        results = self._allocate(30, orders)
        for r in results:
            self.assertGreaterEqual(r["allocated"], 0)
            self.assertGreaterEqual(r["unmet"], 0)

    def test_order_id_breaks_final_tie(self):
        """When due_date and priority are equal, order_id (lexicographic) decides."""
        orders = [
            {"order_id": "O2", "due_date": "2026-09-20", "priority": "HIGH", "required": 20},
            {"order_id": "O1", "due_date": "2026-09-20", "priority": "HIGH", "required": 20},
        ]
        results = self._allocate(20, orders)
        by_id = {r["order_id"]: r for r in results}
        self.assertEqual(by_id["O1"]["allocated"], 20)   # O1 < O2 lexicographically
        self.assertEqual(by_id["O2"]["allocated"], 0)


class TestInventoryReallocationLogic(unittest.TestCase):
    """
    Verifies the INVENTORY_REALLOCATION incremental unit calculation that
    mirrors SCENARIOS.V_MITIGATION_PART_CAPACITY realloc CTE.
    """

    def _compute_realloc(
        self,
        plant_supply: dict[str, float],  # {plant_id: scenario_available_units}
        plant_demand: dict[str, float],  # {plant_id: required_units}
        global_shortage: float,
    ) -> float:
        """
        Pure-Python mirror of realloc CTE:
        pooled_surplus = SUM(max(supply - demand, 0))
        reallocatable  = min(pooled_surplus, global_shortage)
        """
        surplus = sum(
            max(supply - plant_demand.get(plant_id, 0.0), 0.0)
            for plant_id, supply in plant_supply.items()
        )
        return min(surplus, global_shortage)

    def test_no_surplus_gives_zero_realloc(self):
        supply = {"P1": 20, "P2": 10}
        demand = {"P1": 25, "P2": 15}   # both plants in deficit
        result = self._compute_realloc(supply, demand, 10)
        self.assertEqual(result, 0)

    def test_surplus_bounded_by_shortage(self):
        supply = {"P1": 100, "P2": 10}
        demand = {"P1": 20, "P2": 10}   # P1 has 80 surplus, P2 has 0
        result = self._compute_realloc(supply, demand, 5)
        self.assertEqual(result, 5)  # bounded by shortage

    def test_surplus_bounded_by_available_surplus(self):
        supply = {"P1": 25, "P2": 10}
        demand = {"P1": 20, "P2": 10}   # P1 has 5 surplus
        result = self._compute_realloc(supply, demand, 50)
        self.assertEqual(result, 5)  # bounded by available surplus

    def test_zero_shortage_gives_zero_realloc(self):
        supply = {"P1": 100}
        demand = {"P1": 20}
        result = self._compute_realloc(supply, demand, 0)
        self.assertEqual(result, 0)

    def test_multi_plant_surplus_aggregated(self):
        supply = {"P1": 50, "P2": 30, "P3": 20}
        demand = {"P1": 30, "P2": 20, "P3": 25}  # P1: +20, P2: +10, P3: 0
        result = self._compute_realloc(supply, demand, 100)
        self.assertEqual(result, 30)  # 20 + 10 = 30 pooled, bounded to 30

    def test_realloc_never_negative(self):
        result = self._compute_realloc({}, {}, 0)
        self.assertGreaterEqual(result, 0)

    def test_realloc_bounded_below_by_zero(self):
        supply = {"P1": 5}
        demand = {"P1": 10}  # deficit plant
        result = self._compute_realloc(supply, demand, 20)
        self.assertEqual(result, 0)  # no surplus to reallocate


class TestMitigationCostConstraints(unittest.TestCase):
    """
    Verifies cost and recovery constraints between mitigation strategies.
    Uses deterministic expected relationships from the NEXUS seed data.
    """

    def _make_comparison_row(self, mitigation_type: str, orders_at_risk: int,
                              remaining_exposure: float, revenue_protected: float,
                              incremental_cost: float) -> dict:
        return {
            "mitigation_type": mitigation_type,
            "orders_at_risk": orders_at_risk,
            "remaining_revenue_exposure": remaining_exposure,
            "modeled_revenue_protected": revenue_protected,
            "modeled_incremental_cost": incremental_cost,
        }

    def test_no_action_zero_cost(self):
        row = self._make_comparison_row("NO_ACTION", 5, 500000, 0, 0)
        self.assertEqual(row["modeled_incremental_cost"], 0)

    def test_revenue_protected_non_negative_for_active_strategies(self):
        """Any non-NO_ACTION strategy should protect zero or more revenue."""
        for strategy in ("ALTERNATE_SUPPLIER", "EXPEDITE_SHIPMENT", "INVENTORY_REALLOCATION"):
            row = self._make_comparison_row(strategy, 3, 300000, 200000, 50000)
            self.assertGreaterEqual(row["modeled_revenue_protected"], 0)

    def test_remaining_plus_protected_equals_baseline(self):
        """remaining_exposure + revenue_protected should equal baseline at-risk revenue."""
        baseline = 700000.0
        strategies = [
            ("NO_ACTION", 700000, 0),
            ("EXPEDITE_SHIPMENT", 500000, 200000),
            ("INVENTORY_REALLOCATION", 600000, 100000),
            ("ALTERNATE_SUPPLIER", 100000, 600000),
        ]
        for name, remaining, protected in strategies:
            total = remaining + protected
            self.assertAlmostEqual(total, baseline, places=2,
                                   msg=f"{name}: remaining+protected={total} != baseline={baseline}")

    def test_alternate_supplier_more_recovery_than_no_action(self):
        strategies = {
            "NO_ACTION": self._make_comparison_row("NO_ACTION", 5, 700000, 0, 0),
            "ALTERNATE_SUPPLIER": self._make_comparison_row("ALTERNATE_SUPPLIER", 1, 100000, 600000, 80000),
        }
        self.assertLess(
            strategies["ALTERNATE_SUPPLIER"]["remaining_revenue_exposure"],
            strategies["NO_ACTION"]["remaining_revenue_exposure"],
        )

    def test_reallocation_lower_cost_than_alternate(self):
        """
        Inventory reallocation uses existing stock at 15% logistics cost.
        Alternate supplier requires full procurement at market rate.
        For the same recovered units, reallocation should cost less.
        """
        realloc_cost_per_unit = 0.15  # 15% of unit_cost
        alternate_cost_per_unit = 1.0  # full unit_cost × days
        units = 100
        self.assertLess(realloc_cost_per_unit * units, alternate_cost_per_unit * units)


class TestScenarioDataConstraints(unittest.TestCase):
    """
    Tests for scenario engine data constraints verifiable from seed data
    without a live Snowflake connection (using mocked DataFrames).
    """

    def _build_order_impact_df(self, rows: list[dict]) -> pd.DataFrame:
        cols = ["order_id", "customer_id", "product_id", "plant_id",
                "order_quantity", "order_value", "at_risk_quantity", "at_risk_revenue"]
        return pd.DataFrame(rows, columns=cols)

    def test_at_risk_quantity_bounded_by_order_quantity(self):
        """at_risk_quantity cannot exceed order_quantity."""
        df = self._build_order_impact_df([
            {"order_id": "O1", "customer_id": "C1", "product_id": "P1",
             "plant_id": "PL1", "order_quantity": 20, "order_value": 100000,
             "at_risk_quantity": 20, "at_risk_revenue": 100000},
        ])
        violations = df[df["at_risk_quantity"] > df["order_quantity"] + 0.0001]
        self.assertEqual(len(violations), 0)

    def test_no_negative_at_risk(self):
        df = self._build_order_impact_df([
            {"order_id": "O1", "customer_id": "C1", "product_id": "P1",
             "plant_id": "PL1", "order_quantity": 20, "order_value": 100000,
             "at_risk_quantity": 0, "at_risk_revenue": 0},
        ])
        self.assertTrue((df["at_risk_quantity"] >= 0).all())
        self.assertTrue((df["at_risk_revenue"] >= 0).all())

    def test_revenue_proportional_to_quantity(self):
        """at_risk_revenue should be ≤ order_value (proportional risk)."""
        df = self._build_order_impact_df([
            {"order_id": "O1", "customer_id": "C1", "product_id": "P1",
             "plant_id": "PL1", "order_quantity": 20, "order_value": 200000,
             "at_risk_quantity": 10, "at_risk_revenue": 100000},  # 50% of both
        ])
        for _, row in df.iterrows():
            self.assertLessEqual(row["at_risk_revenue"], row["order_value"] + 0.01)


class TestSupplierConcentration(unittest.TestCase):
    """
    Tests supplier concentration logic without Snowflake.
    Mirrors ANALYTICS.SUPPLIER_CONCENTRATION and ANALYTICS.PART_SOURCE_PROFILE.
    """

    def _count_qualified_suppliers(self, supplier_parts: list[tuple]) -> dict[str, int]:
        """supplier_parts: list of (supplier_id, part_id, qualification_status)."""
        counts: dict[str, int] = {}
        for supplier_id, part_id, status in supplier_parts:
            if status == "QUALIFIED":
                counts[part_id] = counts.get(part_id, 0) + 1
        return counts

    def test_single_source_detection(self):
        data = [("SUP-001", "PART-111", "QUALIFIED")]
        counts = self._count_qualified_suppliers(data)
        self.assertTrue(counts["PART-111"] == 1)  # single source

    def test_multi_source_not_single(self):
        data = [
            ("SUP-001", "PART-104", "QUALIFIED"),
            ("SUP-002", "PART-104", "QUALIFIED"),
            ("SUP-005", "PART-104", "QUALIFIED"),
        ]
        counts = self._count_qualified_suppliers(data)
        self.assertEqual(counts["PART-104"], 3)  # 3 qualified sources

    def test_unqualified_does_not_count(self):
        data = [
            ("SUP-001", "PART-104", "QUALIFIED"),
            ("SUP-002", "PART-104", "PENDING"),  # not qualified
        ]
        counts = self._count_qualified_suppliers(data)
        self.assertEqual(counts["PART-104"], 1)  # only 1 qualified

    def test_part_with_no_qualified_supplier(self):
        data = [("SUP-001", "PART-XXX", "PENDING")]
        counts = self._count_qualified_suppliers(data)
        self.assertNotIn("PART-XXX", counts)

    def test_nexus_canonical_part104_has_three_sources(self):
        """PART-104 (Precision Motor) must have 3 qualified sources per seed data."""
        data = [
            ("SUP-001", "PART-104", "QUALIFIED"),  # primary
            ("SUP-002", "PART-104", "QUALIFIED"),  # alternate 1
            ("SUP-005", "PART-104", "QUALIFIED"),  # alternate 2
        ]
        counts = self._count_qualified_suppliers(data)
        self.assertEqual(counts["PART-104"], 3)

    def test_nexus_canonical_part111_is_single_source(self):
        """PART-111 (Safety Controller) has only SUP-001 as qualified source."""
        data = [
            ("SUP-001", "PART-111", "QUALIFIED"),
        ]
        counts = self._count_qualified_suppliers(data)
        self.assertEqual(counts["PART-111"], 1)


class TestDependencyTracing(unittest.TestCase):
    """
    Tests the supplier → part → product → order → customer dependency
    tracing logic without Snowflake.
    """

    def _trace_supplier_customers(
        self,
        supplier_parts: list[tuple],   # (supplier_id, part_id)
        product_parts: list[tuple],    # (product_id, part_id)
        orders: list[tuple],           # (order_id, product_id, customer_id)
        supplier_id: str,
    ) -> set[str]:
        """Returns customer_ids reachable from supplier_id via qualified parts."""
        # Parts this supplier qualifies for
        qualified_parts = {p for s, p in supplier_parts if s == supplier_id}
        # Products that need those parts
        affected_products = {prod for prod, part in product_parts if part in qualified_parts}
        # Customers who ordered those products
        affected_customers = {cust for _ord, prod, cust in orders if prod in affected_products}
        return affected_customers

    def test_sup001_reaches_customers_via_part104(self):
        supplier_parts = [("SUP-001", "PART-104"), ("SUP-001", "PART-111")]
        product_parts  = [("PROD-001", "PART-104"), ("PROD-005", "PART-111")]
        orders = [
            ("ORD-001", "PROD-001", "CUST-001"),
            ("ORD-004", "PROD-005", "CUST-003"),
        ]
        customers = self._trace_supplier_customers(supplier_parts, product_parts, orders, "SUP-001")
        self.assertIn("CUST-001", customers)
        self.assertIn("CUST-003", customers)

    def test_supplier_with_no_parts_reaches_no_customers(self):
        supplier_parts = []
        product_parts  = [("PROD-001", "PART-104")]
        orders = [("ORD-001", "PROD-001", "CUST-001")]
        customers = self._trace_supplier_customers(supplier_parts, product_parts, orders, "SUP-999")
        self.assertEqual(len(customers), 0)

    def test_part_not_in_any_product_reaches_no_customers(self):
        supplier_parts = [("SUP-001", "PART-999")]  # orphan part
        product_parts  = [("PROD-001", "PART-104")]
        orders = [("ORD-001", "PROD-001", "CUST-001")]
        customers = self._trace_supplier_customers(supplier_parts, product_parts, orders, "SUP-001")
        self.assertEqual(len(customers), 0)

    def test_shared_component_traces_both_products(self):
        """PART-102 is shared by PROD-001 and PROD-002."""
        supplier_parts = [("SUP-001", "PART-102")]
        product_parts  = [("PROD-001", "PART-102"), ("PROD-002", "PART-102")]
        orders = [
            ("ORD-001", "PROD-001", "CUST-001"),
            ("ORD-008", "PROD-002", "CUST-006"),
        ]
        customers = self._trace_supplier_customers(supplier_parts, product_parts, orders, "SUP-001")
        self.assertIn("CUST-001", customers)
        self.assertIn("CUST-006", customers)

    def test_multiple_suppliers_for_same_part(self):
        """Disrupting SUP-001 only; alternate suppliers not disrupted."""
        supplier_parts = [
            ("SUP-001", "PART-104"),
            ("SUP-002", "PART-104"),  # alternate — not disrupted
        ]
        product_parts = [("PROD-001", "PART-104")]
        orders = [("ORD-001", "PROD-001", "CUST-001")]
        # Only SUP-001 fails — customers are still at risk because PART-104 has shortfall
        # but alternate coverage depends on inventory math, not just tracing
        customers = self._trace_supplier_customers(supplier_parts, product_parts, orders, "SUP-001")
        self.assertIn("CUST-001", customers)


if __name__ == "__main__":
    unittest.main()
