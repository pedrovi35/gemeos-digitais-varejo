"""
Operational Timeline
=====================
Ledger observability — chronological surface of every event the twin
emitted: sales spikes, replenishments, deliveries, supplier delays,
ruptures, promotion starts/ends.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Linha do Tempo Operacional · Gêmeo Digital", layout="wide")

from components import (
    exec_header, inject_theme, kpi_row, render_global_filters, section_banner,
    timeline_card,
)
from config.theme import THEME
from services.event_service import EventService
from utils.formatting import fmt_int
from utils.session import SessionState


from core.runtime import after_page_config
after_page_config()
flt = render_global_filters()

events = EventService()


# ── Hero ───────────────────────────────────────────────────────────
exec_header(
    eyebrow="LINHA DO TEMPO OPERACIONAL",
    title="Timeline Operacional · Observability Ledger",
    subtitle="Ledger imutável de todos os eventos que o gêmeo digital observou.",
    chips=flt.chips() + [("LEDGER", "append-only")],
    status=("info", "STREAM ATIVO"),
)


# ── Controls ───────────────────────────────────────────────────────
c1, c2, c3 = st.columns([1, 1, 2])
with c1:
    window = st.selectbox("Janela", [1, 4, 12, 24, 72], index=3,
                          format_func=lambda h: f"Últimas {h}h")
with c2:
    limit = st.slider("Eventos", 50, 1000, 250, 50)
with c3:
    sev_filter = st.multiselect(
        "Severidade", ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"],
        default=["MEDIUM", "HIGH", "CRITICAL"],
    )


recent = events.recent(limit=limit)
hist   = events.histogram(hours=window)

if not recent.empty and sev_filter:
    recent = recent[recent["severity"].isin(sev_filter)]

total = len(recent)
critical = int((recent.get("severity", pd.Series([])).eq("CRITICAL")).sum()) if not recent.empty else 0
high     = int((recent.get("severity", pd.Series([])).eq("HIGH")).sum())     if not recent.empty else 0

kpi_row([
    {"label": "EVENTOS · TOTAL",     "value": fmt_int(total),    "tone": "info"},
    {"label": "CRÍTICOS",            "value": fmt_int(critical), "tone": "critical" if critical else "healthy"},
    {"label": "HIGH",                "value": fmt_int(high),     "tone": "warning"  if high else "healthy"},
    {"label": "TIPOS DISTINTOS",     "value": fmt_int(recent["event_type"].nunique() if not recent.empty else 0)},
    {"label": "JANELA",              "value": f"{window}h",      "tone": "info"},
])


# ── Histogram by event-type ────────────────────────────────────────
section_banner("DENSIDADE DE EVENTOS · TIPO × TEMPO", hint=f"janela {window}h")
if not hist.empty:
    pivot = hist.pivot_table(index="bucket", columns="event_type", values="n", aggfunc="sum").fillna(0)
    fig = go.Figure()
    for col, c in zip(pivot.columns, THEME["palette"]):
        h = c.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        fill = f"rgba({r},{g},{b},0.33)"
        fig.add_trace(go.Scatter(
            x=pivot.index, y=pivot[col], mode="lines", stackgroup="one",
            name=col, line=dict(width=0.5, color=c), fillcolor=fill,
        ))
    fig.update_layout(height=320, hovermode="x unified",
                      margin=dict(l=30, r=20, t=20, b=40))
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
else:
    st.info("Stream vazio na janela — execute uma simulação para popular o ledger.")


# ── Causality timeline ─────────────────────────────────────────────
section_banner("LINHA DO TEMPO CAUSAL", hint="severidade ↓")
if recent.empty:
    st.info("Sem eventos para exibir.")
else:
    items = []
    for _, row in recent.head(40).iterrows():
        items.append({
            "title":    row.get("event_type", "—"),
            "time":     pd.to_datetime(row["event_ts"]),
            "severity": row.get("severity", "INFO"),
            "meta":     f"{row.get('store_id') or '—'} · {row.get('sku_id') or '—'}",
            "body":     None,
        })
    timeline_card(items)


# ── Raw ledger ─────────────────────────────────────────────────────
section_banner("LEDGER BRUTO")
st.dataframe(recent, hide_index=True, width='stretch', height=420)
