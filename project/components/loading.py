"""Loading state helpers."""
from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Generator

import streamlit as st


@contextmanager
def loading_panel(label: str = "Carregando dados operacionais…") -> Generator[None, None, None]:
    with st.spinner(label):
        yield


def skeleton_kpi_row(n: int = 4) -> None:
    cols = st.columns(n)
    for c in cols:
        with c:
            st.markdown("<div class='ops-skeleton ops-skeleton--kpi'></div>", unsafe_allow_html=True)
