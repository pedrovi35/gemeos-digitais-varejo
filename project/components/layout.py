"""Top-level layout primitives — header, sidebar context, theme injection."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from config.settings import settings
from utils.time_utils import now_tz


_CSS_PATHS = (
    settings.root / "assets" / "css" / "theme.css",
    settings.root / "assets" / "css" / "premium.css",
)


def inject_theme() -> None:
    """Inject base + premium CSS, plus Inter webfont, once per session."""
    if st.session_state.get("_theme_loaded"):
        return
    st.markdown(
        "<link rel='preconnect' href='https://fonts.googleapis.com'>"
        "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700"
        "&family=JetBrains+Mono:wght@400;500&display=swap' rel='stylesheet'>",
        unsafe_allow_html=True,
    )
    css_blocks = []
    for path in _CSS_PATHS:
        if Path(path).exists():
            css_blocks.append(Path(path).read_text(encoding="utf-8"))
    if css_blocks:
        st.markdown(f"<style>{''.join(css_blocks)}</style>", unsafe_allow_html=True)
    st.session_state["_theme_loaded"] = True


def render_topbar(*, page_title: str, subtitle: str | None = None,
                  status_label: str = "OPERAÇÃO NOMINAL") -> None:
    now = now_tz().strftime("%d/%m/%Y · %H:%M:%S")
    sub = subtitle or settings.tagline
    html = f"""
    <div class="ops-topbar">
      <div class="ops-topbar__brand">
        <div class="ops-topbar__logo">RT</div>
        <div>
          <div class="ops-topbar__sub">{sub}</div>
          <div class="ops-topbar__title">{page_title}</div>
        </div>
      </div>
      <div class="ops-topbar__meta">
        <span class="ops-topbar__chip">v{settings.version}</span>
        <span class="ops-topbar__chip">ENV · <strong>{settings.twin.env.upper()}</strong></span>
        <span class="ops-topbar__chip">{now}</span>
        <span class="ops-topbar__chip">
          <span class="ops-topbar__pulse"></span>&nbsp; <strong>{status_label}</strong>
        </span>
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_sidebar_context() -> None:
    """Global sidebar — store/scope selector visible across all pages."""
    from config.constants import DEFAULT_STORES
    from utils.session import SessionState

    with st.sidebar:
        st.markdown("### CONTEXTO OPERACIONAL")
        store_options = ["ALL"] + [s["store_id"] for s in DEFAULT_STORES]
        labels = {"ALL": "Toda a rede"} | {s["store_id"]: f"{s['store_id']} · {s['name']}" for s in DEFAULT_STORES}
        chosen = st.selectbox(
            "Escopo",
            options=store_options,
            index=store_options.index(SessionState.get("selected_store", "ST-001"))
                  if SessionState.get("selected_store", "ST-001") in store_options else 0,
            format_func=lambda x: labels[x],
            label_visibility="collapsed",
        )
        SessionState.set("selected_store", chosen)
        st.divider()
        st.caption(f"**Twin tick**: {settings.twin.tick_seconds}s")
        st.caption(f"**Horizonte**: {settings.twin.horizon_days} dias")
        st.caption(f"**Timezone**: {settings.twin.timezone}")


def section_divider() -> None:
    st.markdown("<div class='ops-divider'></div>", unsafe_allow_html=True)
