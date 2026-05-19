"""
Streamlit page runtime — call `after_page_config()` immediately after `st.set_page_config`.
"""
from __future__ import annotations

import streamlit as st

from components.layout import inject_theme, render_sidebar_context
from components.global_filters import render_global_filters
from config.settings import settings
from core.bootstrap import ensure_runtime
from core.errors import run_safe
from core.health import check_health
from core.monitoring import get_metrics
from utils.session import SessionState


def after_page_config(*, show_health: bool = True) -> None:
    """
    Standard page initialization:
      bootstrap → theme → session → sidebar → health banner
    """
    with st.spinner("Inicializando Gêmeo Digital · Supply Chain Tower…"):
        status = ensure_runtime()

    SessionState.init()
    inject_theme()
    render_sidebar_context()

    if show_health:
        _render_runtime_strip(status)

    # Expose filters lazily via session — pages call render_global_filters() when needed
    if "flt" not in st.session_state:
        st.session_state["flt_ready"] = True


def render_page_filters():
    """Lazy filter bar — call from pages that need scope."""
    return render_global_filters()


def _render_runtime_strip(status) -> None:
    health = check_health()
    metrics = get_metrics()
    cols = st.columns([1.2, 1, 1, 1])
    with cols[0]:
        st.caption(
            f"**{settings.name}** v{settings.version} · "
            f"{'☁️ Cloud' if status.cloud else '💻 Local'} · "
            f"{'Light seed' if status.light_seed else 'Full seed'}"
        )
    with cols[1]:
        st.caption(f"Boot **{status.boot_ms:.0f}ms**")
    with cols[2]:
        st.caption(f"Health **{health.badge()}**")
    with cols[3]:
        st.caption(f"Queries avg **{metrics['avg_query_ms']:.0f}ms**")

    if not health.healthy:
        from components.fallback import render_degraded_banner  # lazy to avoid circular
        render_degraded_banner(health)


def sidebar_runtime_controls() -> None:
    """Optional sidebar controls for ops / demo."""
    with st.sidebar:
        st.markdown("### RUNTIME")
        if st.button("↺ Recarregar warehouse", width='stretch'):
            ensure_runtime.clear()
            st.cache_data.clear()
            st.rerun()
        if st.button("🗑 Limpar cache", width='stretch'):
            st.cache_data.clear()
            st.rerun()
        metrics = get_metrics()
        st.caption(f"Erros sessão: {metrics['error_count']}")
        st.caption(f"Queries: {metrics['query_count']}")
