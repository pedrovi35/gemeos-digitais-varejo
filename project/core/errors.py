"""Global error handling for Streamlit pages."""
from __future__ import annotations

import traceback
from collections.abc import Callable
from typing import Any, TypeVar

import streamlit as st

from config.logging import logger
from core.monitoring import record_error

T = TypeVar("T")


def run_safe(fn: Callable[[], T], *, context: str = "operation") -> T | None:
    """Execute `fn` and render a professional error panel on failure."""
    try:
        return fn()
    except Exception as exc:
        record_error()
        logger.exception(f"[{context}] {exc}")
        st.error(f"**Falha operacional** · `{context}`")
        with st.expander("Detalhes técnicos (suporte)"):
            st.code(traceback.format_exc(), language="text")
        st.info(
            "O runtime permanece ativo. Tente **Recarregar dados** na barra lateral "
            "ou reinicie a aplicação. Se o problema persistir, execute "
            "`python scripts/bootstrap.py` localmente."
        )
        return None


def render_error_page(title: str, message: str, *, hint: str | None = None) -> None:
    st.markdown(f"### {title}")
    st.warning(message)
    if hint:
        st.caption(hint)
