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
    # Inline fallbacks — keep layout legible even if the theme CSS isn't loaded.
    _S_ITEM = (
        "position:relative;margin-bottom:10px;padding:12px 14px;"
        "background:linear-gradient(160deg,#0F1A2C,#0D1421);"
        "border:1px solid #1E2E4A;border-radius:8px;"
    )
    _S_HEAD = (
        "display:flex;justify-content:space-between;align-items:baseline;"
        "gap:12px;flex-wrap:wrap;"
    )
    _S_TITLE = "font-size:13px;font-weight:600;color:#E8F0FE;"
    _S_TIME  = "font-size:10.5px;color:#6B8AAF;font-family:ui-monospace,monospace;white-space:nowrap;"
    _S_META  = "font-size:11px;color:#8EA8C3;margin-top:4px;font-family:ui-monospace,monospace;"
    _S_BODY  = "font-size:12.5px;color:#8EA8C3;margin-top:6px;line-height:1.55;"
    _S_WRAP  = "position:relative;padding-left:26px;"

    inner = []
    for it in items:
        sev = (it.get("severity") or "INFO").upper()
        tone = _TONE_MAP.get(sev, "")
        cls = f"tl-item tl-item--{tone}" if tone else "tl-item"
        ts = it["time"]
        if isinstance(ts, datetime):
            ts = ts.strftime("%d/%m %H:%M")
        meta = (
            f"<div class='tl-item__meta' style=\"{_S_META}\">{it['meta']}</div>"
            if it.get("meta") else ""
        )
        body = (
            f"<div class='tl-item__body' style=\"{_S_BODY}\">{it['body']}</div>"
            if it.get("body") else ""
        )
        inner.append(
            f"<div class='{cls}' style=\"{_S_ITEM}\">"
            f"<div class='tl-item__head' style=\"{_S_HEAD}\">"
            f"<span class='tl-item__title' style=\"{_S_TITLE}\">{it['title']}</span>"
            f"<span class='tl-item__time' style=\"{_S_TIME}\">{ts}</span>"
            f"</div>{meta}{body}</div>"
        )
    st.markdown(
        f"<div class='timeline' style=\"{_S_WRAP}\">{''.join(inner)}</div>",
        unsafe_allow_html=True,
    )
