"""Streamlit cache wrappers — single import surface for the whole app."""
from __future__ import annotations

from typing import Any, Callable

import streamlit as st


def cached_resource(ttl: int | None = None, show_spinner: bool = False) -> Callable:
    """Long-lived singletons (DB connections, models, clients)."""
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        return st.cache_resource(ttl=ttl, show_spinner=show_spinner)(fn)
    return decorator


def cached_data(ttl: int = 60, show_spinner: bool = False) -> Callable:
    """Short-lived computed data (queries, aggregations)."""
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        return st.cache_data(ttl=ttl, show_spinner=show_spinner)(fn)
    return decorator


def invalidate_cache() -> None:
    st.cache_data.clear()
    st.cache_resource.clear()
