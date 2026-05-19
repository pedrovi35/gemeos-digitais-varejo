"""Operational timeline — vertical event ledger with severity rail."""
from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

import streamlit as st


_TONE_MAP = {
    "CRITICAL": "critical", "HIGH": "warning", "MEDIUM": "warning",
    "LOW": "healthy",       "INFO": "",
}


def timeline_card(items: Iterable[dict]) -> None:
    """Render a vertical operational timeline.

    Each item dict: {
      title: str, time: datetime|str, severity: str,
      meta: str | None, body: str | None
    }
    """
    inner = []
    for it in items:
        sev = (it.get("severity") or "INFO").upper()
        tone = _TONE_MAP.get(sev, "")
        cls = f"tl-item tl-item--{tone}" if tone else "tl-item"
        ts = it["time"]
        if isinstance(ts, datetime):
            ts = ts.strftime("%d/%m %H:%M")
        meta = f"<div class='tl-item__meta'>{it['meta']}</div>" if it.get("meta") else ""
        body = f"<div class='tl-item__body'>{it['body']}</div>" if it.get("body") else ""
        inner.append(
            f"<div class='{cls}'>"
            f"<div class='tl-item__head'>"
            f"<span class='tl-item__title'>{it['title']}</span>"
            f"<span class='tl-item__time'>{ts}</span>"
            f"</div>{meta}{body}</div>"
        )
    st.markdown(f"<div class='timeline'>{''.join(inner)}</div>", unsafe_allow_html=True)
