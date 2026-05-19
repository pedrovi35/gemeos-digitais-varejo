"""Status badge component."""
from __future__ import annotations

import streamlit as st


_TONE_MAP = {
    "HEALTHY":  "healthy",  "WARNING":  "warning",
    "CRITICAL": "critical", "STOCKOUT": "critical",
    "OVERSTOCKED": "info",  "INFO":     "info",
    "LOW": "info", "MEDIUM": "warning", "HIGH": "critical",
}


def status_badge(label: str, *, tone: str | None = None, inline: bool = False) -> str:
    cls = _TONE_MAP.get((tone or label).upper(), "info")
    html = f"<span class='badge badge--{cls}'>{label}</span>"
    if inline:
        return html
    st.markdown(html, unsafe_allow_html=True)
    return html
