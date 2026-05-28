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


@st.cache_data(show_spinner=False)
def _css_bundle() -> str:
    """Read & concatenate CSS files once per process (cached on disk paths)."""
    blocks: list[str] = []
    for path in _CSS_PATHS:
        if Path(path).exists():
            blocks.append(Path(path).read_text(encoding="utf-8"))
    return "".join(blocks)


def inject_theme() -> None:
    """Inject base + premium CSS, plus Inter webfont.

    Must run on every page render — Streamlit multi-page apps rebuild the DOM
    on each navigation, so a session-state guard would leave subsequent pages
    unstyled. The CSS body itself is cached via `_css_bundle()`.
    """
    st.markdown(
        "<link rel='preconnect' href='https://fonts.googleapis.com'>"
        "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700"
        "&family=JetBrains+Mono:wght@400;500&display=swap' rel='stylesheet'>",
        unsafe_allow_html=True,
    )
    css = _css_bundle()
    if css:
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


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
    """Global sidebar — brand, scope selector, live status, config & footer."""
    from config.constants import DEFAULT_STORES
    from utils.session import SessionState

    env = settings.twin.env.upper()
    env_tone = {"PROD": "#FF3B5C", "STAGING": "#FFB800"}.get(env, "#4299FF")

    with st.sidebar:
        # ── Brand header ────────────────────────────────────────────
        st.markdown(
            f"""
            <div style="
                display:flex;align-items:center;gap:10px;
                padding:14px 4px 16px 4px;margin-bottom:6px;
                border-bottom:1px solid #1E2E4A;
            ">
              <div style="
                width:36px;height:36px;border-radius:9px;
                background:linear-gradient(135deg,#4299FF 0%,#7B5CFF 100%);
                display:flex;align-items:center;justify-content:center;
                color:#fff;font-weight:700;font-size:13px;letter-spacing:0.5px;
                font-family:ui-monospace,monospace;
                box-shadow:0 2px 10px rgba(66,153,255,0.35);
              ">RT</div>
              <div style="display:flex;flex-direction:column;line-height:1.15;">
                <span style="
                  font-size:12.5px;font-weight:700;color:#E8F0FE;letter-spacing:0.2px;
                ">{settings.name}</span>
                <span style="
                  font-size:9.5px;color:#6B8AAF;letter-spacing:1.5px;
                  text-transform:uppercase;font-family:ui-monospace,monospace;
                  margin-top:2px;
                ">v{settings.version} · <span style="color:{env_tone};">{env}</span></span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Scope selector ──────────────────────────────────────────
        st.markdown(
            "<div style='font-size:10px;letter-spacing:2px;font-weight:700;"
            "text-transform:uppercase;color:#6B8AAF;font-family:ui-monospace,monospace;"
            "margin:10px 0 6px 2px;'>ESCOPO OPERACIONAL</div>",
            unsafe_allow_html=True,
        )
        store_options = ["ALL"] + [s["store_id"] for s in DEFAULT_STORES]
        labels = {"ALL": "Toda a rede"} | {
            s["store_id"]: f"{s['store_id']} · {s['name']}" for s in DEFAULT_STORES
        }
        current = SessionState.get("selected_store", "ST-001")
        chosen = st.selectbox(
            "Escopo",
            options=store_options,
            index=store_options.index(current) if current in store_options else 0,
            format_func=lambda x: labels[x],
            label_visibility="collapsed",
        )
        SessionState.set("selected_store", chosen)

        # Selected-scope chip with live dot
        st.markdown(
            f"""
            <div style="
                display:flex;align-items:center;gap:8px;
                padding:8px 10px;margin-top:8px;
                background:linear-gradient(90deg,rgba(0,212,170,0.08),transparent);
                border:1px solid rgba(0,212,170,0.25);
                border-left:2px solid #00D4AA;border-radius:6px;
            ">
              <span style="
                width:7px;height:7px;border-radius:50%;background:#00D4AA;
                box-shadow:0 0 8px #00D4AA;
                animation:pulse 1.8s ease-in-out infinite;
              "></span>
              <span style="
                font-size:10px;color:#8EA8C3;font-family:ui-monospace,monospace;
                letter-spacing:0.5px;
              ">LIVE · tick {settings.twin.tick_seconds}s</span>
            </div>
            <style>
              @keyframes pulse {{
                0%,100% {{ opacity:1; transform:scale(1); }}
                50%     {{ opacity:0.55; transform:scale(0.85); }}
              }}
            </style>
            """,
            unsafe_allow_html=True,
        )

        # ── Runtime configuration card ──────────────────────────────
        st.markdown(
            "<div style='font-size:10px;letter-spacing:2px;font-weight:700;"
            "text-transform:uppercase;color:#6B8AAF;font-family:ui-monospace,monospace;"
            "margin:18px 0 6px 2px;'>RUNTIME</div>",
            unsafe_allow_html=True,
        )
        row_style = (
            "display:flex;justify-content:space-between;align-items:center;"
            "padding:7px 10px;font-size:11px;font-family:ui-monospace,monospace;"
        )
        label_style = "color:#6B8AAF;letter-spacing:0.5px;"
        value_style = "color:#E8F0FE;font-weight:600;"
        st.markdown(
            f"""
            <div style="
                background:linear-gradient(160deg,#0F1A2C,#0D1421);
                border:1px solid #1E2E4A;border-radius:8px;overflow:hidden;
            ">
              <div style="{row_style}border-bottom:1px solid #1E2E4A;">
                <span style="{label_style}">Horizonte</span>
                <span style="{value_style}">{settings.twin.horizon_days}d</span>
              </div>
              <div style="{row_style}border-bottom:1px solid #1E2E4A;">
                <span style="{label_style}">Timezone</span>
                <span style="{value_style}">{settings.twin.timezone}</span>
              </div>
              <div style="{row_style}">
                <span style="{label_style}">Tick</span>
                <span style="{value_style}">{settings.twin.tick_seconds}s</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Footer ──────────────────────────────────────────────────
        st.markdown(
            f"""
            <div style="
                margin-top:22px;padding-top:12px;border-top:1px solid #1E2E4A;
                font-size:9.5px;color:#5D7A9C;font-family:ui-monospace,monospace;
                letter-spacing:1.2px;text-transform:uppercase;text-align:center;
                line-height:1.6;
            ">
              {settings.tagline}
            </div>
            """,
            unsafe_allow_html=True,
        )


def section_divider() -> None:
    st.markdown("<div class='ops-divider'></div>", unsafe_allow_html=True)
