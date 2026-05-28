"""Fallback / empty / degraded UI states."""
from __future__ import annotations

import streamlit as st


def empty_state(title: str, body: str, *, action: str | None = None) -> None:
    st.markdown(
        f"<div class='ops-empty'>"
        f"<div class='ops-empty__title'>{title}</div>"
        f"<div class='ops-empty__body'>{body}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    if action:
        st.caption(action)


def render_degraded_banner(health) -> None:
    failed = [k for k, v in health.checks.items() if not v]
    st.warning(
        f"**Modo degradado** — componentes indisponíveis: {', '.join(failed)}. "
        f"Algumas visualizações podem usar heurísticas ou dados parciais."
    )
    with st.expander("Diagnóstico do runtime"):
        for k, v in health.details.items():
            st.text(f"{k}: {v}")


def offline_llm_banner() -> None:
    st.info(
        "**AI Offline** — Configure `GROQ_API_KEY` em Secrets (Cloud) ou `.env` (local). "
        "O restante da torre de controle opera normalmente com dados do warehouse."
    )
