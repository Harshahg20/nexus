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


# ── Custom exceptions ─────────────────────────────────────────────────────────

class NexusConfigError(RuntimeError):
    """Missing or invalid configuration (key file, secrets, etc.)."""

class NexusConnectionError(RuntimeError):
    """Snowflake connection or query failure."""


# ── Session ───────────────────────────────────────────────────────────────────

@st.cache_resource
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

@st.cache_data(ttl=300)
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

# These are the only scenario parameters seeded in the database.
# Any UI-level attempt to run a different scenario will return empty data.
SUPPORTED_SCENARIOS: dict[str, dict] = {
    "supplier_failure": {
        "supplier_id":            "SUP-001",
        "capacity_reduction_pct": 100,
        "duration_days":          14,
        "description":            "SUP-001 · 100% capacity loss · 14 days",
    },
    "port_disruption": {
        "port_id":     "PORT-TYO",
        "description": "PORT-TYO closure",
    },
    "freight_shock": {
        "description": "Global freight cost shock",
    },
}


def is_unsupported_scenario(params: dict) -> tuple[bool, str]:
    """
    Compare *params* (from V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS) against the
    seeded scenario configuration.

    Returns (unsupported: bool, guidance: str).

    guidance is a user-readable explanation of what IS supported when the
    scenario appears to be outside the seeded parameters.
    """
    if not params:
        return False, ""   # empty params are handled by the component

    sup = SUPPORTED_SCENARIOS["supplier_failure"]
    sid      = str(params.get("FAILED_SUPPLIER_ID", "")).upper()
    cap      = float(params.get("CAPACITY_REDUCTION_PCT", 0) or 0)
    duration = int(params.get("DURATION_DAYS", 0) or 0)

    mismatches = []
    if sid and sid != sup["supplier_id"]:
        mismatches.append(f"supplier `{sid}` (only `{sup['supplier_id']}` is seeded)")
    if cap and abs(cap - sup["capacity_reduction_pct"]) > 0.1:
        mismatches.append(
            f"capacity reduction `{cap:.0f}%` "
            f"(only `{sup['capacity_reduction_pct']:.0f}%` is seeded)"
        )
    if duration and duration != sup["duration_days"]:
        mismatches.append(
            f"duration `{duration} days` (only `{sup['duration_days']} days` is seeded)"
        )

    if mismatches:
        guidance = (
            "The active scenario parameters differ from the seeded configuration: "
            + "; ".join(mismatches) + ". "
            "The Snowflake scenario engine only has data for "
            f"**{sup['description']}**. "
            "Update `V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS` in Snowflake to match the "
            "seeded values, or re-run `006_scenario_engine.sql` with the desired parameters."
        )
        return True, guidance

    return False, ""


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
