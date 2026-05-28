"""KPI card primitives — improved visual hierarchy."""
from __future__ import annotations

import streamlit as st


def kpi_card(
    label: str,
    value: str,
    *,
    delta: str | None = None,
    delta_dir: str | None = None,
    tone: str = "info",
    hint: str | None = None,
) -> None:
    """Render a single KPI tile.

    tone: 'info' | 'healthy' | 'warning' | 'critical'
    delta_dir: 'up' | 'down' | None
    """
    tone_colors = {
        "healthy":  ("#00D4AA", "rgba(0,212,170,0.10)",  "rgba(0,212,170,0.25)"),
        "warning":  ("#FFB800", "rgba(255,184,0,0.10)",   "rgba(255,184,0,0.25)"),
        "critical": ("#FF3B5C", "rgba(255,59,92,0.10)",   "rgba(255,59,92,0.30)"),
        "info":     ("#4299FF", "rgba(66,153,255,0.08)",  "rgba(66,153,255,0.25)"),
    }
    accent, bg_tint, _ = tone_colors.get(tone, tone_colors["info"])

    delta_html = ""
    if delta:
        if delta_dir == "up":
            arrow, dcol = "▲", "#00D4AA"
        elif delta_dir == "down":
            arrow, dcol = "▼", "#FF3B5C"
        else:
            arrow, dcol = "·", "#8EA8C3"
        delta_html = (
            f"<div style='font-size:11px;margin-top:4px;font-family:var(--mono);color:{dcol};'>"
            f"{arrow} {delta}</div>"
        )

    hint_html = (
        f"<div style='font-size:10px;margin-top:6px;color:var(--text-dim);font-family:var(--mono);'>{hint}</div>"
        if hint else ""
    )

    html = f"""
    <div style="
      background: linear-gradient(160deg, #0D1421 0%, #0F1A2C 100%);
      border: 1px solid #1E2E4A;
      border-top: 2px solid {accent};
      border-radius: 10px;
      padding: 18px 20px 16px;
      position: relative;
      transition: border-color 160ms, box-shadow 160ms;
      box-shadow: 0 2px 12px rgba(0,0,0,0.45);
      background-image: radial-gradient(circle at 0% 0%, {bg_tint} 0%, transparent 60%),
                        linear-gradient(160deg, #0D1421 0%, #0F1A2C 100%);
    ">
      <div style="
        font-size:10px; font-weight:700; letter-spacing:1.8px;
        color:#6B8AAF; text-transform:uppercase; font-family:var(--sans);
        margin-bottom:10px;
      ">{label}</div>
      <div style="
        font-size:32px; font-weight:700; color:#E8F0FE;
        font-variant-numeric:tabular-nums; letter-spacing:-0.025em; line-height:1;
      ">{value}</div>
      {delta_html}
      {hint_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def kpi_row(items: list[dict]) -> None:
    """Render a row of KPI cards."""
    cols = st.columns(len(items), gap="medium")
    for col, item in zip(cols, items, strict=True):
        with col:
            kpi_card(
                label=item["label"],
                value=item["value"],
                delta=item.get("delta"),
                delta_dir=item.get("delta_dir"),
                tone=item.get("tone", "info"),
                hint=item.get("hint"),
            )
