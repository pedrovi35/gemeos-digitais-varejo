"""Risk card — large operational severity tile."""
from __future__ import annotations

import streamlit as st


def risk_card(
    *, score: float | int, label: str, title: str,
    meta: str | None = None, description: str | None = None,
    tone: str = "medium",
) -> None:
    """Render a single risk card.

    tone: 'critical' | 'high' | 'medium' | 'low'
    """
    tone = tone if tone in {"critical", "high", "medium", "low"} else "medium"
    meta_html = f"<div class='risk-card__meta'>{meta}</div>" if meta else ""
    desc_html = f"<div class='risk-card__desc'>{description}</div>" if description else ""
    score_value = f"{score:.0f}" if isinstance(score, (int, float)) else str(score)
    html = f"""
    <div class="risk-card risk-card--{tone}">
      <div class="risk-card__score">
        <div class="risk-card__score-value">{score_value}</div>
        <div class="risk-card__score-label">{label}</div>
      </div>
      <div class="risk-card__body">
        <div class="risk-card__title">{title}</div>
        {meta_html}
        {desc_html}
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def risk_grid(cards: list[dict], cols: int = 2) -> None:
    """Render a responsive grid of risk cards."""
    columns = st.columns(cols)
    for i, c in enumerate(cards):
        with columns[i % cols]:
            risk_card(**c)
