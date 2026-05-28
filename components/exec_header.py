"""
Executive page header — premium hero band used at the top of every page.
"""
from __future__ import annotations

from collections.abc import Sequence
from html import escape

import streamlit as st

from config.settings import settings
from utils.time_utils import now_tz


def exec_header(
    *,
    eyebrow: str,
    title: str,
    subtitle: str | None = None,
    chips: Sequence[tuple[str, str]] | None = None,
    status: tuple[str, str] = ("healthy", "OPERAÇÃO NOMINAL"),
) -> None:
    chips = list(chips or [])
    eyebrow  = escape(eyebrow)
    title    = escape(title)
    subtitle = escape(subtitle) if subtitle else None

    tone_map = {
        "healthy":  ("#00D4AA", "rgba(0,212,170,0.12)", "rgba(0,212,170,0.35)"),
        "warning":  ("#FFB800", "rgba(255,184,0,0.12)",  "rgba(255,184,0,0.35)"),
        "critical": ("#FF3B5C", "rgba(255,59,92,0.12)",  "rgba(255,59,92,0.40)"),
        "info":     ("#4299FF", "rgba(66,153,255,0.10)", "rgba(66,153,255,0.30)"),
    }
    s_color, s_bg, s_border = tone_map.get(status[0], tone_map["healthy"])
    now = now_tz().strftime("%d/%m/%Y · %H:%M")
    sub_html = f"<p class='exec-hero__sub'>{subtitle}</p>" if subtitle else ""

    # Chips: filter context chips rendered as pills
    chips_html = ""
    for lbl, val in chips:
        chips_html += (
            f'<div class="eh-chip">'
            f'<span class="eh-chip__label">{escape(lbl)}</span>'
            f'<span class="eh-chip__value">{escape(val)}</span>'
            f'</div>'
        )

    # Meta row: env + ver + time (right side, subtle)
    meta_html = f"""
      <div class="eh-meta">
        <span class="eh-meta__item">v{settings.version}</span>
        <span class="eh-meta__sep">·</span>
        <span class="eh-meta__item">{settings.twin.env.upper()}</span>
        <span class="eh-meta__sep">·</span>
        <span class="eh-meta__item">{now}</span>
      </div>"""

    # Status badge
    status_html = f"""
      <div class="eh-status" style="
        background:{s_bg};
        border:1px solid {s_border};
        color:{s_color};
      ">
        <span class="eh-status__dot" style="background:{s_color};box-shadow:0 0 8px {s_color};"></span>
        <span class="eh-status__label">{status[1]}</span>
      </div>"""

    html = f"""
    <div class="exec-hero">
      <div class="exec-hero__top">
        <div class="exec-hero__left">
          <div class="exec-hero__eyebrow">{eyebrow}</div>
          <h1 class="exec-hero__h1">{title}</h1>
          {sub_html}
        </div>
        <div class="exec-hero__right">
          {meta_html}
          {status_html}
        </div>
      </div>
      {f'<div class="eh-chips-row">{chips_html}</div>' if chips_html else ''}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def section_banner(title: str, hint: str | None = None) -> None:
    # Inline fallback styles — banner stays usable even without theme CSS.
    s_wrap = (
        "display:flex;justify-content:space-between;align-items:center;gap:12px;"
        "padding:12px 18px;margin:28px 0 14px 0;"
        "background:linear-gradient(90deg,rgba(24,34,55,0.9) 0%,rgba(13,20,33,0.4) 100%);"
        "border-left:3px solid #4299FF;border-radius:0 6px 6px 0;"
    )
    s_title = (
        "font-size:11.5px;letter-spacing:2.2px;font-weight:700;text-transform:uppercase;"
        "color:#E8F0FE;font-family:ui-monospace,monospace;"
    )
    s_hint = "font-size:10.5px;color:#6B8AAF;font-family:ui-monospace,monospace;"
    hint_html = (
        f"<span class='section-banner__hint' style=\"{s_hint}\">{hint}</span>"
        if hint else ""
    )
    st.markdown(
        f"<div class='section-banner' style=\"{s_wrap}\">"
        f"<span class='section-banner__title' style=\"{s_title}\">{title}</span>"
        f"{hint_html}"
        f"</div>",
        unsafe_allow_html=True,
    )
