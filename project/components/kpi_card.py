"""Custom KPI card primitives."""
from __future__ import annotations

import streamlit as st


def kpi_card(label: str, value: str, *, delta: str | None = None,
             delta_dir: str | None = None, tone: str = "info") -> None:
    """Render a single KPI tile.

    tone: 'info' | 'healthy' | 'warning' | 'critical'
    delta_dir: 'up' | 'down' | None
    """
    delta_html = ""
    if delta:
        dcls = f"kpi__delta kpi__delta--{delta_dir}" if delta_dir else "kpi__delta"
        arrow = "▲" if delta_dir == "up" else "▼" if delta_dir == "down" else "·"
        delta_html = f"<div class='{dcls}'>{arrow} {delta}</div>"
    html = f"""
    <div class="kpi kpi--{tone}">
      <div class="kpi__label">{label}</div>
      <div class="kpi__value">{value}</div>
      {delta_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def kpi_row(items: list[dict]) -> None:
    """Render a row of KPI cards. Each dict: {label, value, delta?, delta_dir?, tone?}."""
    cols = st.columns(len(items))
    for col, item in zip(cols, items, strict=True):
        with col:
            kpi_card(
                label=item["label"], value=item["value"],
                delta=item.get("delta"), delta_dir=item.get("delta_dir"),
                tone=item.get("tone", "info"),
            )
