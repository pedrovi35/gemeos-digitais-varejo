"""Live alert feed component."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from components.status_badge import status_badge


def render_alert_feed(df: pd.DataFrame, *, max_rows: int = 8) -> None:
    if df.empty:
        st.info("Nenhum alerta aberto. Operação dentro dos parâmetros.")
        return
    for _, row in df.head(max_rows).iterrows():
        badge = status_badge(row["severity"], inline=True)
        ts = pd.to_datetime(row["raised_ts"]).strftime("%d/%m %H:%M")
        scope = f"{row['store_id'] or '—'} · {row['sku_id'] or '—'}"
        html = f"""
        <div class="panel" style="padding:12px 14px; margin-bottom:8px;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>{badge} &nbsp; <strong>{row['title']}</strong></div>
            <span style="font-family:var(--mono); font-size:11px; color:var(--text-dim);">{ts}</span>
          </div>
          <div style="margin-top:6px; color:var(--text-muted); font-size:12.5px;">{row.get('message','') or ''}</div>
          <div style="margin-top:6px; font-size:11px; color:var(--text-dim); font-family:var(--mono);">{scope}</div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)
