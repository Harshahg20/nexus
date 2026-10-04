"""
NEXUS UI Compatibility Helpers
Thin wrappers that degrade gracefully on older Streamlit versions
(e.g. Snowflake SiS warehouse runtime, pre-1.27).

Covered APIs
------------
st_rerun()              st.rerun()        added 1.27  → falls back to experimental_rerun
st_dataframe()          st.dataframe()    strips hide_index on pre-1.18 runtimes
st_toast()              st.toast()        added 1.25  → falls back to st.info
st_cache_resource()     decorator shim    added 1.18  → falls back to experimental_singleton
st_cache_data()         decorator shim    added 1.18  → falls back to experimental_memo
"""
import inspect
import streamlit as st


# ── st.rerun ──────────────────────────────────────────────────────────────────

def st_rerun():
    """st.rerun() was added in 1.27; older SiS runtime only has experimental_rerun."""
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()  # type: ignore[attr-defined]


# ── st.dataframe ──────────────────────────────────────────────────────────────

def st_dataframe(df, **kwargs):
    """
    Drop-in replacement for st.dataframe that strips kwargs unsupported
    by the current Streamlit version (e.g. hide_index on pre-1.18 runtimes).
    The index is reset/dropped so rows still appear clean even without hide_index.
    """
    supported = inspect.signature(st.dataframe).parameters

    # Always reset the index so the numeric index column is 0-based and
    # unobtrusive — important when hide_index is not available.
    df = df.reset_index(drop=True)

    # Strip unsupported keyword args rather than crashing.
    safe_kwargs = {k: v for k, v in kwargs.items() if k in supported}

    return st.dataframe(df, **safe_kwargs)


# ── st.toast ──────────────────────────────────────────────────────────────────

def st_toast(message: str, **kwargs):
    """
    st.toast() was added in 1.25.  Falls back to st.info() on older SiS runtimes
    so the user still sees the message even without the toast widget.
    """
    if hasattr(st, "toast"):
        st.toast(message, **kwargs)
    else:
        st.info(message)


# ── @st.cache_resource decorator shim ────────────────────────────────────────

def st_cache_resource(func):
    """
    Decorator replacement for @st.cache_resource (added in 1.18).

    Usage:
        @st_cache_resource
        def get_session(): ...

    Falls back through:
      1. st.cache_resource          (≥ 1.18)
      2. st.experimental_singleton  (< 1.18, very old SiS)
      3. No caching (identity)      (extremely old runtimes — avoids hard crash)
    """
    if hasattr(st, "cache_resource"):
        return st.cache_resource(func)
    elif hasattr(st, "experimental_singleton"):
        return st.experimental_singleton(func)  # type: ignore[attr-defined]
    return func


# ── @st.cache_data decorator-factory shim ────────────────────────────────────

def st_cache_data(**decorator_kwargs):
    """
    Decorator factory replacement for @st.cache_data(...) (added in 1.18).

    Usage:
        @st_cache_data(ttl=300)
        def my_query(sql): ...

    Falls back through:
      1. st.cache_data(**kwargs)          (≥ 1.18)
      2. st.experimental_memo(**kwargs)   (< 1.18, very old SiS)
      3. No caching (identity)            (extremely old runtimes — avoids hard crash)
    """
    if hasattr(st, "cache_data"):
        return st.cache_data(**decorator_kwargs)
    elif hasattr(st, "experimental_memo"):
        return st.experimental_memo(**decorator_kwargs)  # type: ignore[attr-defined]
    # Last resort: no-op identity decorator
    return lambda func: func
