"""
Inventory Health
=================
Espelho operacional do estoque · ABC pareto · cobertura · forecast.
"""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Saúde de Estoque · Gêmeo Digital", layout="wide")

from analytics.abc_analysis import ABCAnalysis
from analytics.stockout_analytics import StockoutAnalytics
from components import (
    coverage_histogram, exec_header, inject_theme, kpi_row,
    render_global_filters, section_banner, stockout_heatmap,
)
from components.charts import gauge_compact
from config.theme import THEME
from services.forecast_service import ForecastService
from services.inventory_service import InventoryService
from services.replenishment_service import ReplenishmentService
from utils.formatting import fmt_int, fmt_pct
from utils.session import SessionState


from core.runtime import after_page_config
after_page_config()
flt = render_global_filters()

inv      = InventoryService()
stockout = StockoutAnalytics()
fc       = ForecastService()
rep      = ReplenishmentService()
abc      = ABCAnalysis()


# ── Hero ───────────────────────────────────────────────────────────
exec_header(
    eyebrow="SAÚDE DE ESTOQUE",
    title="Saúde de Estoque · Espelho Operacional",
    subtitle="Estado vivo de SKU × loja · ABC · cobertura · forecast.",
    chips=flt.chips(),
    status=("info", "ESPELHO ATUALIZADO"),
)


snap = inv.live_snapshot(flt.store_id, flt.category)
if snap.empty:
    st.warning("Sem snapshot disponível.")
    st.stop()


# ── KPIs ───────────────────────────────────────────────────────────
total = len(snap)
at_risk = int(snap["status"].isin(["CRITICAL", "STOCKOUT"]).sum())
overstocked = int((snap["status"] == "OVERSTOCKED").sum())
avg_cover = float(snap["days_of_cover"].mean() or 0)

kpi_row([
    {"label": "SKUs MONITORADOS", "value": fmt_int(total),                   "tone": "info"},
    {"label": "EM RISCO",         "value": fmt_int(at_risk),
     "tone": "critical" if at_risk else "healthy"},
    {"label": "OVERSTOCK",        "value": fmt_int(overstocked),             "tone": "warning"},
    {"label": "COBERTURA MÉDIA",  "value": f"{avg_cover:.1f}d",              "tone": "info"},
    {"label": "RISK SHARE",       "value": fmt_pct(at_risk / max(1, total)),
     "tone": "critical" if (at_risk / max(1, total)) > 0.05 else "healthy"},
])


# ── Distribution & risk map row ────────────────────────────────────
c1, c2 = st.columns([1.2, 1])
with c1:
    section_banner("DISTRIBUIÇÃO DE COBERTURA · REDE")
    cover = inv.coverage_distribution()
    if not cover.empty:
        st.plotly_chart(coverage_histogram(cover),
                        width='stretch', config={"displayModeBar": False})
with c2:
    section_banner("MAPA DE RISCO · LOJA × CATEGORIA")
    risk = stockout.risk_surface()
    if not risk.empty:
        st.plotly_chart(stockout_heatmap(risk, x="store_id", y="category", z="risk_score"),
                        width='stretch', config={"displayModeBar": False})


# ── ABC analysis ───────────────────────────────────────────────────
section_banner("ANÁLISE ABC · PARETO DE RECEITA · 30 DIAS")
abc_df = abc.classify(days=30)
if not abc_df.empty:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=list(range(1, len(abc_df) + 1)), y=abc_df["revenue"],
        marker_color=[THEME["healthy"] if c == "A" else THEME["primary"] if c == "B" else THEME["text_dim"]
                      for c in abc_df["class"]],
        name="Receita",
    ))
    fig.add_trace(go.Scatter(
        x=list(range(1, len(abc_df) + 1)), y=abc_df["cum_pct"] * 100,
        yaxis="y2", name="% acumulado",
        line=dict(color=THEME["warning"], width=2.4),
    ))
    fig.update_layout(
        height=320,
        yaxis=dict(title="Receita (R$)"),
        yaxis2=dict(title="% acumulado", overlaying="y", side="right",
                    range=[0, 105], ticksuffix="%"),
        margin=dict(l=30, r=40, t=10, b=40),
    )
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})

    abc_a = int((abc_df["class"] == "A").sum())
    abc_b = int((abc_df["class"] == "B").sum())
    abc_c = int((abc_df["class"] == "C").sum())
    kpi_row([
        {"label": "CLASSE A · 80%",  "value": fmt_int(abc_a), "tone": "healthy"},
        {"label": "CLASSE B · 15%",  "value": fmt_int(abc_b), "tone": "info"},
        {"label": "CLASSE C · 5%",   "value": fmt_int(abc_c), "tone": "warning"},
        {"label": "RECEITA TOTAL",   "value": f"R$ {abc_df['revenue'].sum():,.0f}".replace(",", "."), "tone": "info"},
    ])


# ── SKU grid ───────────────────────────────────────────────────────
section_banner("VISÃO SKU × LOJA · SNAPSHOT VIVO")
view = snap.rename(columns={
    "store_id": "Loja", "sku_id": "SKU", "description": "Descrição",
    "category": "Categoria", "velocity_class": "Vel.", "on_hand": "On-hand",
    "on_order": "Em pedido", "reorder_point": "ROP", "safety_stock": "SS",
    "days_of_cover": "Cobertura (d)", "status": "Status",
})[["Loja", "SKU", "Descrição", "Categoria", "Vel.", "On-hand", "Em pedido",
    "ROP", "SS", "Cobertura (d)", "Status"]]
st.dataframe(view, hide_index=True, width='stretch', height=440,
             column_config={"Cobertura (d)": st.column_config.NumberColumn(format="%.1f")})
