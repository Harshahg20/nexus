import streamlit as st
import pandas as pd
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from snowflake.snowpark import Session


@st.cache_resource
def get_session() -> Session:
    cfg = st.secrets["connections"]["snowflake"]
    with open(cfg["private_key_path"], "rb") as f:
        private_key = load_pem_private_key(f.read(), password=None)
    return Session.builder.configs({
        "account":     cfg["account"],
        "user":        cfg["user"],
        "private_key": private_key,
        "role":        cfg.get("role", "ACCOUNTADMIN"),
        "warehouse":   cfg.get("warehouse", "COMPUTE_WH"),
        "database":    cfg.get("database", "NEXUS_DB"),
    }).create()


@st.cache_data(ttl=300)
def query_df(sql: str) -> pd.DataFrame:
    return get_session().sql(sql).to_pandas()


def query_row(sql: str) -> dict:
    df = query_df(sql)
    if df.empty:
        return {}
    return df.iloc[0].to_dict()


def query_scalar(sql: str):
    df = query_df(sql)
    if df.empty:
        return None
    return df.iloc[0, 0]


# --- Cached data loaders for each UI section ---

def load_supplier_failure_impact() -> dict:
    return query_row("SELECT * FROM NEXUS_DB.SCENARIOS.V_SUPPLIER_FAILURE_IMPACT")


def load_supplier_failure_parameters() -> dict:
    return query_row("SELECT * FROM NEXUS_DB.SCENARIOS.V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS")


def load_supplier_failure_chain() -> pd.DataFrame:
    return query_df("SELECT * FROM NEXUS_DB.SCENARIOS.V_SUPPLIER_FAILURE_CHAIN")


def load_mitigation_comparison() -> pd.DataFrame:
    return query_df("SELECT * FROM NEXUS_DB.SCENARIOS.V_MITIGATION_COMPARISON")


def load_executive_risk_summary() -> dict:
    return query_row("SELECT * FROM NEXUS_DB.ANALYTICS.EXECUTIVE_RISK_SUMMARY")


def load_governed_metric_catalog() -> pd.DataFrame:
    return query_df("SELECT * FROM NEXUS_DB.ANALYTICS.V_NEXUS_GOVERNED_METRIC_CATALOG")
