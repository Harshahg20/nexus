"""
NEXUS — Snowflake service layer.

All data access goes through this module.  Components should call the named
loader functions (load_*) rather than raw SQL so caching and error handling
are consistent.

Authentication: key-pair (RSA private key).  The unencrypted PEM file path
must be set in .streamlit/secrets.toml under
[connections.snowflake] private_key_path.  See secrets.toml.example for the
full format.

Error strategy
--------------
• get_session()      — raises NexusConfigError or NexusConnectionError with a
                        user-readable message (no raw traceback exposed).
• query_df / _row / _scalar — return empty DataFrame / {} / None on failure
                        and surface a warning via st.warning() so every
                        component degrades gracefully without a crash.
"""
from __future__ import annotations

import os
import streamlit as st
import pandas as pd

# SiS cache-decorator compatibility shims (cache_resource / cache_data added in 1.18)
# These must be defined *before* the decorated functions below.

def _sis_cache_resource(func):
    """
    Decorator shim for @st.cache_resource (added in Streamlit 1.18).
    Falls back to @st.experimental_singleton on older SiS runtimes, then
    to a plain no-op identity if neither is available.
    """
    if hasattr(st, "cache_resource"):
        return st.cache_resource(func)
    elif hasattr(st, "experimental_singleton"):
        return st.experimental_singleton(func)  # type: ignore[attr-defined]
    return func


def _sis_cache_data(ttl: int):
    """
    Decorator factory shim for @st.cache_data(ttl=...) (added in Streamlit 1.18).
    Falls back to @st.experimental_memo on older SiS runtimes, then to a
    plain no-op identity if neither is available.
    """
    if hasattr(st, "cache_data"):
        return st.cache_data(ttl=ttl)
    elif hasattr(st, "experimental_memo"):
        return st.experimental_memo(ttl=ttl)  # type: ignore[attr-defined]
    return lambda func: func


# ── Custom exceptions ─────────────────────────────────────────────────────────

class NexusConfigError(RuntimeError):
    """Missing or invalid configuration (key file, secrets, etc.)."""

class NexusConnectionError(RuntimeError):
    """Snowflake connection or query failure."""


# ── Session ───────────────────────────────────────────────────────────────────

@_sis_cache_resource
def get_session():
    """
    Build and return a Snowpark session.

    Detection order:
    1. Streamlit-in-Snowflake (SiS) — use the active session provided by the
       platform.  No credentials needed.
    2. Local development — key-pair (RSA) authentication via secrets.toml.

    Raises NexusConfigError  for bad config (missing key, secrets).
    Raises NexusConnectionError for Snowflake network/auth failures.
    """
    # ── SiS: the platform provides an active session ──────────────────────
    try:
        from snowflake.snowpark.context import get_active_session
        session = get_active_session()
    except Exception:
        pass  # not running inside Snowflake — fall through to local auth
    else:
        # get_active_session() succeeded → we are inside Snowflake SiS
        try:
            session.use_database("NEXUS_DB")
        except Exception:
            pass  # database context may already be set
        return session

    # ── Local: key-pair authentication via secrets.toml ───────────────────
    try:
        cfg = st.secrets["connections"]["snowflake"]
    except (KeyError, FileNotFoundError):
        raise NexusConfigError(
            "Snowflake credentials not found. "
            "Copy app/.streamlit/secrets.toml.example → app/.streamlit/secrets.toml "
            "and fill in your account details."
        )

    key_path = cfg.get("private_key_path", "")
    if not key_path:
        raise NexusConfigError(
            "private_key_path is missing from [connections.snowflake] in secrets.toml. "
            "See secrets.toml.example for the required format."
        )
    if not os.path.isfile(key_path):
        raise NexusConfigError(
            f"Private key file not found: {key_path!r}. "
            "Generate a key pair (see secrets.toml.example) and update the path."
        )

    try:
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
        with open(key_path, "rb") as f:
            private_key = load_pem_private_key(f.read(), password=None)
    except Exception as exc:
        raise NexusConfigError(
            f"Failed to load the private key from {key_path!r}: {exc}. "
            "Ensure the key is an unencrypted PKCS#8 PEM file."
        ) from exc

    try:
        from snowflake.snowpark import Session
        session = Session.builder.configs({
            "account":     cfg["account"],
            "user":        cfg["user"],
            "private_key": private_key,
            "role":        cfg.get("role", "ACCOUNTADMIN"),
            "warehouse":   cfg.get("warehouse", "COMPUTE_WH"),
            "database":    cfg.get("database", "NEXUS_DB"),
        }).create()
        return session
    except Exception as exc:
        raise NexusConnectionError(
            f"Could not connect to Snowflake (account={cfg.get('account', '?')}): {exc}"
        ) from exc


# ── Low-level query helpers ───────────────────────────────────────────────────
#
# Design: two-layer approach so that *errors are never silently cached*.
#
#   _query_df_cached(sql)  — @st.cache_data(ttl=300), raises on failure.
#                            Streamlit does NOT cache exceptions, so failed
#                            calls always fall through to a live retry.
#
#   query_df(sql)          — public, NOT cached.  Calls _query_df_cached and
#                            converts any exception into a user-visible
#                            st.error/st.warning + empty DataFrame.
#
# Consequence: if a Snowflake connection fails, the user sees an error banner
# on every page render until connectivity is restored — never a silent blank.

@_sis_cache_data(ttl=300)
def _query_df_cached(sql: str) -> pd.DataFrame:
    """
    Execute *sql* and return a DataFrame.

    This function is cached for 300 s.  Raises on any failure so the cache
    never stores a stale empty result — Streamlit does not cache exceptions.
    """
    return get_session().sql(sql).to_pandas()


def query_df(sql: str) -> pd.DataFrame:
    """
    Public query helper.  Returns empty DataFrame on any failure and surfaces
    a user-readable error banner via st.error / st.warning.

    Never displays a raw Python traceback.
    """
    try:
        return _query_df_cached(sql)
    except (NexusConfigError, NexusConnectionError) as exc:
        st.error(f"⚠ **Data source unavailable.** {exc}")
        return pd.DataFrame()
    except Exception as exc:
        # Strip internal details — log the full message to server console only
        import traceback
        traceback.print_exc()   # visible in `streamlit run` terminal, not in UI
        st.warning(
            "⚠ **A query failed** — this section shows no data. "
            "Check the Streamlit server log for details."
        )
        return pd.DataFrame()


def query_row(sql: str) -> dict:
    """Return the first row of *sql* as a dict, or {} if no rows / error."""
    df = query_df(sql)
    if df.empty:
        return {}
    return df.iloc[0].to_dict()


def query_scalar(sql: str):
    """Return the first cell of *sql*, or None if no rows / error."""
    df = query_df(sql)
    if df.empty:
        return None
    return df.iloc[0, 0]


# ── Scenario parameter helpers ────────────────────────────────────────────────

def is_unsupported_scenario(params: dict) -> tuple[bool, str]:
    """
    Legacy guard — kept for backward compatibility.
    Since 016_interactive_scenarios.sql enabled table-driven parameterization,
    any supplier or port loaded from SCENARIO_PARAMS is valid.
    Always returns (False, "").
    """
    return False, ""


# ── Interactive scenario parameter writers ────────────────────────────────────

def update_supplier_failure_params(
    supplier_id: str,
    capacity_reduction_pct: float,
    duration_days: int,
) -> bool:
    """
    Write new supplier failure parameters to SCENARIO_PARAMS.

    Triggers a MERGE so every downstream view picks up the new values on the
    next query (cache is cleared by the caller via _clear_scenario_cache()).

    Returns True on success, False on any database error.
    """
    try:
        session = get_session()
        # Audit old values first
        session.sql(
            f"""
            INSERT INTO NEXUS_DB.SCENARIOS.SCENARIO_PARAM_AUDIT
                (scenario_type, param_key, old_value, new_value)
            SELECT
                'SUPPLIER_FAILURE',
                param_key,
                param_value,
                CASE param_key
                    WHEN 'supplier_id'            THEN '{supplier_id}'
                    WHEN 'capacity_reduction_pct' THEN '{capacity_reduction_pct:.1f}'
                    WHEN 'duration_days'          THEN '{duration_days}'
                END
            FROM NEXUS_DB.SCENARIOS.SCENARIO_PARAMS
            WHERE scenario_type = 'SUPPLIER_FAILURE'
              AND param_key IN ('supplier_id','capacity_reduction_pct','duration_days')
            """
        ).collect()

        session.sql(
            f"""
            MERGE INTO NEXUS_DB.SCENARIOS.SCENARIO_PARAMS t
            USING (
                SELECT 'SUPPLIER_FAILURE' AS scenario_type, 'supplier_id'            AS param_key, '{supplier_id}'                 AS param_value UNION ALL
                SELECT 'SUPPLIER_FAILURE',                   'capacity_reduction_pct',               '{capacity_reduction_pct:.1f}'               UNION ALL
                SELECT 'SUPPLIER_FAILURE',                   'duration_days',                        '{duration_days}'
            ) s ON t.scenario_type = s.scenario_type AND t.param_key = s.param_key
            WHEN MATCHED     THEN UPDATE SET t.param_value = s.param_value, t.updated_at = CURRENT_TIMESTAMP()
            WHEN NOT MATCHED THEN INSERT (scenario_type, param_key, param_value) VALUES (s.scenario_type, s.param_key, s.param_value)
            """
        ).collect()
        return True
    except Exception as exc:
        import traceback
        traceback.print_exc()
        return False


def update_port_disruption_params(
    port_id: str,
    disruption_pct: float,
    duration_days: int,
) -> bool:
    """
    Write new port disruption parameters to SCENARIO_PARAMS.
    Returns True on success, False on any database error.
    """
    try:
        session = get_session()
        session.sql(
            f"""
            MERGE INTO NEXUS_DB.SCENARIOS.SCENARIO_PARAMS t
            USING (
                SELECT 'PORT_DISRUPTION' AS scenario_type, 'port_id'        AS param_key, '{port_id}'             AS param_value UNION ALL
                SELECT 'PORT_DISRUPTION',                   'disruption_pct',               '{disruption_pct:.1f}'               UNION ALL
                SELECT 'PORT_DISRUPTION',                   'duration_days',                '{duration_days}'
            ) s ON t.scenario_type = s.scenario_type AND t.param_key = s.param_key
            WHEN MATCHED     THEN UPDATE SET t.param_value = s.param_value, t.updated_at = CURRENT_TIMESTAMP()
            WHEN NOT MATCHED THEN INSERT (scenario_type, param_key, param_value) VALUES (s.scenario_type, s.param_key, s.param_value)
            """
        ).collect()
        return True
    except Exception as exc:
        import traceback
        traceback.print_exc()
        return False


def clear_scenario_cache() -> None:
    """
    Bust the Streamlit data cache so scenario query results are re-fetched
    from Snowflake after parameter changes.  Handles both st.cache_data and
    legacy experimental_memo runtimes.
    """
    if hasattr(st, "cache_data"):
        try:
            st.cache_data.clear()
        except Exception:
            pass
    if hasattr(st, "experimental_memo"):
        try:
            st.experimental_memo.clear()  # type: ignore[attr-defined]
        except Exception:
            pass


# ── Named data loaders (consumed by UI components) ────────────────────────────

def load_supplier_failure_impact() -> dict:
    """
    Aggregate KPI row for the active supplier-failure scenario.

    Source: NEXUS_DB.SCENARIOS.V_SUPPLIER_FAILURE_IMPACT (1 row).
    Metric scope: counts from the allocation engine — only orders/customers/
    parts where the shortage allocation produced a deficit.
    """
    return query_row("SELECT * FROM NEXUS_DB.SCENARIOS.V_SUPPLIER_FAILURE_IMPACT")


def load_supplier_failure_parameters() -> dict:
    """
    Active scenario configuration (supplier ID, capacity reduction, duration).

    Source: NEXUS_DB.SCENARIOS.V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS (1 row).
    """
    return query_row("SELECT * FROM NEXUS_DB.SCENARIOS.V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS")


def load_supplier_failure_chain() -> pd.DataFrame:
    """
    Full cascade chain for the active supplier-failure scenario.

    Source: NEXUS_DB.SCENARIOS.V_SUPPLIER_FAILURE_CHAIN (multi-row).
    Scope: all orders, parts, plants, products, and customers that appear in
    the disruption cascade — including those partially fulfilled.  Counts
    derived from this view may be broader than the KPI strip, which uses only
    the shortage-allocation engine output.
    """
    return query_df("SELECT * FROM NEXUS_DB.SCENARIOS.V_SUPPLIER_FAILURE_CHAIN")


def load_mitigation_comparison() -> pd.DataFrame:
    """
    Three modeled mitigation strategies with cost/recovery metrics.

    Source: NEXUS_DB.SCENARIOS.V_MITIGATION_COMPARISON (3 rows).
    Note: outputs are deterministic model results — not operational guarantees.
    """
    return query_df("SELECT * FROM NEXUS_DB.SCENARIOS.V_MITIGATION_COMPARISON")


def load_executive_risk_summary() -> dict:
    """
    Executive-level aggregate risk summary.

    Source: NEXUS_DB.ANALYTICS.EXECUTIVE_RISK_SUMMARY (1 row).
    """
    return query_row("SELECT * FROM NEXUS_DB.ANALYTICS.EXECUTIVE_RISK_SUMMARY")


def load_governed_metric_catalog() -> pd.DataFrame:
    """
    Governed metric catalog for the Evidence section.

    Source: NEXUS_DB.ANALYTICS.V_NEXUS_GOVERNED_METRIC_CATALOG.
    """
    return query_df("SELECT * FROM NEXUS_DB.ANALYTICS.V_NEXUS_GOVERNED_METRIC_CATALOG")


# ── Interactive scenario support loaders ──────────────────────────────────────

def load_suppliers_list() -> pd.DataFrame:
    """
    Available suppliers for the interactive supplier-failure selector.
    Source: NEXUS_DB.SCENARIOS.V_AVAILABLE_SUPPLIERS.
    """
    return query_df("SELECT * FROM NEXUS_DB.SCENARIOS.V_AVAILABLE_SUPPLIERS")


def load_ports_list() -> pd.DataFrame:
    """
    Available ports for the interactive port-disruption selector.
    Source: NEXUS_DB.SCENARIOS.V_AVAILABLE_PORTS.
    """
    return query_df("SELECT * FROM NEXUS_DB.SCENARIOS.V_AVAILABLE_PORTS")


def load_port_disruption_parameters() -> dict:
    """
    Active port disruption configuration (port ID, disruption %, duration).
    Source: NEXUS_DB.SCENARIOS.V_ACTIVE_PORT_DISRUPTION_PARAMETERS (1 row).
    """
    return query_row("SELECT * FROM NEXUS_DB.SCENARIOS.V_ACTIVE_PORT_DISRUPTION_PARAMETERS")


def load_port_disruption_impact() -> dict:
    """
    Aggregate KPI row for the active port-disruption scenario.
    Source: NEXUS_DB.SCENARIOS.V_PORT_DISRUPTION_IMPACT (1 row).
    """
    return query_row("SELECT * FROM NEXUS_DB.SCENARIOS.V_PORT_DISRUPTION_IMPACT")


def load_freight_shock_summary() -> dict:
    """
    Aggregate KPI row for the freight shock scenario.
    Source: NEXUS_DB.SCENARIOS.V_FREIGHT_SHOCK_SUMMARY (1 row).
    """
    return query_row("SELECT * FROM NEXUS_DB.SCENARIOS.V_FREIGHT_SHOCK_SUMMARY")


def load_freight_shock_chain() -> pd.DataFrame:
    """
    Per-part sourcing options under the freight shock scenario.
    Source: NEXUS_DB.SCENARIOS.V_FREIGHT_SHOCK_CHAIN.
    """
    return query_df(
        "SELECT part_id, supplier_id, supplier_name, required_units, "
        "protected_units, uncovered_units, modeled_freight_cost, lead_time_days "
        "FROM NEXUS_DB.SCENARIOS.V_FREIGHT_SHOCK_CHAIN "
        "ORDER BY part_id, modeled_freight_cost"
    )


def load_resilience_score() -> dict:
    """
    Composite supply chain resilience score (0–100) and component breakdown.
    Source: NEXUS_DB.ANALYTICS.V_SUPPLY_CHAIN_RESILIENCE_SCORE (1 row).
    """
    return query_row("SELECT * FROM NEXUS_DB.ANALYTICS.V_SUPPLY_CHAIN_RESILIENCE_SCORE")


def load_scenario_params_history() -> pd.DataFrame:
    """
    Audit log of scenario parameter changes.
    Source: NEXUS_DB.SCENARIOS.SCENARIO_PARAM_AUDIT.
    """
    return query_df(
        "SELECT scenario_type, param_key, old_value, new_value, changed_at "
        "FROM NEXUS_DB.SCENARIOS.SCENARIO_PARAM_AUDIT "
        "ORDER BY changed_at DESC LIMIT 20"
    )


def generate_executive_brief(
    impact: dict,
    params: dict,
    model: str = "mistral-large2",
) -> str:
    """
    Use Snowflake Cortex COMPLETE to generate a 2-paragraph executive brief
    describing the active scenario impact and recommended mitigations.

    Returns the brief text, or an empty string on any error.
    """
    supplier = params.get("FAILED_SUPPLIER_ID", "SUP-001")
    capacity = float(params.get("CAPACITY_REDUCTION_PCT", 100) or 100)
    duration = int(params.get("DURATION_DAYS", 14) or 14)
    revenue  = float(impact.get("REVENUE_EXPOSURE", 0) or 0)
    orders   = int(impact.get("ORDERS_AT_RISK", 0) or 0)
    customers = int(impact.get("CUSTOMERS_EXPOSED", 0) or 0)
    parts    = int(impact.get("AFFECTED_PARTS", 0) or 0)
    plants   = int(impact.get("AFFECTED_PLANTS", 0) or 0)
    units    = int(impact.get("UNITS_AT_RISK", 0) or 0)

    prompt = (
        "You are a senior supply chain risk analyst. Write a concise two-paragraph "
        "executive brief in plain business English. No markdown headers. No bullet points. "
        "Use the exact numbers provided.\\n\\n"
        f"SCENARIO: Supplier {supplier} loses {capacity:.0f}% of production capacity "
        f"for {duration} days.\\n\\n"
        f"IMPACT (from NEXUS deterministic allocation engine):\\n"
        f"- Revenue at Risk: ${revenue/1_000_000:.2f}M\\n"
        f"- Orders Disrupted: {orders}\\n"
        f"- Customers Exposed: {customers}\\n"
        f"- Parts with Shortage: {parts}\\n"
        f"- Manufacturing Plants Affected: {plants}\\n"
        f"- Units at Risk: {units:,}\\n\\n"
        "Paragraph 1 (3 sentences): State the business impact and urgency level — "
        "use the specific revenue figure and customer count.\\n"
        "Paragraph 2 (3 sentences): Recommend the two highest-leverage mitigations "
        "(choose from: expedite in-transit shipments, activate alternate qualified suppliers, "
        "reallocate inventory from low-risk plants). Be specific and actionable."
    )

    # Escape single quotes for SQL literal embedding
    safe_prompt = prompt.replace("'", "\\'")

    try:
        session = get_session()
        rows = session.sql(
            f"SELECT SNOWFLAKE.CORTEX.COMPLETE('{model}', '{safe_prompt}') AS brief"
        ).collect()
        if rows:
            return str(rows[0]["BRIEF"]).strip()
    except Exception as exc:
        # Fall back to a simpler model if primary unavailable
        try:
            session2 = get_session()
            rows2 = session2.sql(
                f"SELECT SNOWFLAKE.CORTEX.COMPLETE('llama3.1-70b', '{safe_prompt}') AS brief"
            ).collect()
            if rows2:
                return str(rows2[0]["BRIEF"]).strip()
        except Exception:
            pass
    return ""
