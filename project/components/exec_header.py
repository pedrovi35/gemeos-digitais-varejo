"""
Executive page header — premium hero band used at the top of every page.

Renders a structured banner with title, subtitle, breadcrumb context and
a row of live operational chips (env, version, time, status, etc.).
"""
from __future__ import annotations

from collections.abc import Sequence

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
    """Render the executive hero band.

    chips: list of (label, value) pairs; renders as monospace pill chips.
    status: (tone, label) where tone ∈ healthy|warning|critical|info.
    """
    chips = list(chips or [])
    chips_html = "".join(
        f"<span class='exec-hero__chip'><span style='color:var(--text-dim);font-size:9px;letter-spacing:1.5px;text-transform:uppercase;'>{lbl}</span>&nbsp;<strong>{val}</strong></span>"
        for lbl, val in chips
    )
    tone_map = {
        "healthy":  ("var(--healthy)",  "exec-hero__chip--status-healthy"),
        "warning":  ("var(--warning)",  "exec-hero__chip--status-warning"),
        "critical": ("var(--critical)", "exec-hero__chip--status-critical"),
        "info":     ("var(--info)",     ""),
    }
    tone_color, tone_cls = tone_map.get(status[0], ("var(--healthy)", "exec-hero__chip--status-healthy"))
    now = now_tz().strftime("%d/%m %H:%M")
    sub = f"<div class='exec-hero__sub'>{subtitle}</div>" if subtitle else ""
    eyebrow_html = f"<div class='exec-hero__eyebrow'>{eyebrow}</div>" if eyebrow else ""
    html = f"""
    <div class="exec-hero">
      <div class="exec-hero__row">
        <div>
          {eyebrow_html}
          <div class="exec-hero__h1">{title}</div>
          {sub}
        </div>
        <div class="exec-hero__chips">
          {chips_html}
          <span class="exec-hero__chip"><span style='font-size:9px;color:var(--text-dim);'>VER</span>&nbsp;<strong>v{settings.version}</strong></span>
          <span class="exec-hero__chip"><span style='font-size:9px;color:var(--text-dim);'>ENV</span>&nbsp;<strong>{settings.twin.env.upper()}</strong></span>
          <span class="exec-hero__chip" style="font-size:10.5px;color:var(--text-dim);">{now}</span>
          <span class="exec-hero__chip {tone_cls}" style="color:{tone_color};">
            <span class="exec-hero__pulse" style="background:{tone_color}; box-shadow: 0 0 10px {tone_color};"></span>
            <strong>{status[1]}</strong>
          </span>
        </div>
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def section_banner(title: str, hint: str | None = None) -> None:
    """A subtle section heading band — use as a left-bordered marker."""
    hint_html = f"<span class='section-banner__hint'>{hint}</span>" if hint else ""
    st.markdown(
        f"<div class='section-banner'><span class='section-banner__title'>{title}</span>{hint_html}</div>",
        unsafe_allow_html=True,
    )
