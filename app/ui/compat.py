"""
NEXUS UI Compatibility Helpers
Thin wrappers that degrade gracefully on older Streamlit versions
(e.g. Snowflake SiS warehouse runtime).
"""
import inspect
import streamlit as st


def st_rerun():
    """st.rerun() was added in 1.27; older SiS runtime only has experimental_rerun."""
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()  # type: ignore[attr-defined]


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
