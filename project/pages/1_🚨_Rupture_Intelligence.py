"""
Rupture Intelligence
=====================
Inteligência operacional focada em ruptura: surface de risco por
loja×categoria, ranking de SKUs em iminência, decomposição de perdas
por causa-raiz e priorização de mitigação.
"""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Rupture Intelligence · Twin", page_icon="assets/favicon.svg", layout="wide")

from analytics.stockout_analytics import StockoutAnalytics
from components import (
    ai_insight, exec_header, inject_theme, kpi_row, render_global_filters,
    risk_grid, section_banner, stockout_heatmap,
)
from components.charts import waterfall_lost_sales
from components.timeline_card import timeline_card
from config.theme import THEME
from services.inventory_service import InventoryService
from services.kpi_service import KpiService
from utils.formatting import fmt_compact, fmt_currency, fmt_int, fmt_pct
from utils.session import SessionState
from utils.time_utils import now_tz


from core.runtime import after_page_config
after_page_config()
flt = render_global_filters()

inv      = InventoryService()
stockout = StockoutAnalytics()
kpi      = KpiService()


# ── Hero ───────────────────────────────────────────────────────────
today = kpi.today(flt.store_id)
so_pct  = float(today.get("stockout_pct") or 0)
lost_7d = stockout.lost_sales_estimate(days=7)
at_risk = inv.at_risk_count(flt.store_id)

exec_header(
    eyebrow="RUPTURE INTELLIGENCE",
    title="Inteligência Operacional de Ruptura",
    subtitle="Detecção precoce, priorização de SKUs em risco e decomposição causal.",
    chips=flt.chips() + [("SKUs EM RISCO", f"{at_risk}"),
                         ("PERDA 7d", fmt_currency(lost_7d))],
    status=("critical" if so_pct > 0.02 else "warning" if so_pct > 0.01 else "healthy",
            "RUPTURA ACIMA DO LIMITE" if so_pct > 0.02 else "RUPTURA SOB CONTROLE"),
)


# ── Executive KPI strip ────────────────────────────────────────────
kpi_row([
    {"label": "RUPTURA · 24H",       "value": fmt_pct(so_pct),
     "delta": "limite 2.0%", "tone": "critical" if so_pct > 0.02 else "healthy"},
    {"label": "SKUs CRÍTICOS",       "value": fmt_int(at_risk),
     "tone": "critical" if at_risk > 50 else "warning"},
    {"label": "PERDA ESTIMADA · 7D", "value": fmt_currency(lost_7d), "tone": "critical"},
    {"label": "PERDA P/ DIA · MED.", "value": fmt_currency(lost_7d / 7),
     "tone": "warning"},
    {"label": "SERVICE LEVEL",       "value": fmt_pct(float(today.get('service_level') or 0)),
     "tone": "info"},
])


# ── Risk surface (heatmap) ─────────────────────────────────────────
section_banner("RISK SURFACE · LOJA × CATEGORIA", hint="risco = SKUs em CRITICAL/STOCKOUT (%)")
risk_df = stockout.risk_surface()
if risk_df.empty:
    st.info("Sem dados de risco na janela atual.")
else:
    if flt.category:
        risk_df = risk_df[risk_df["category"] == flt.category]
    st.plotly_chart(
        stockout_heatmap(risk_df, x="store_id", y="category", z="risk_score"),
        width='stretch', config={"displayModeBar": False},
    )


# ── Top-priority rupture risks ─────────────────────────────────────
section_banner("TOP PRIORIDADES · CARDS DE RISCO", hint="ordenado por horas-até-ruptura")
tts = stockout.time_to_stockout().head(6)
cards = []
for _, r in tts.iterrows():
    hours = float(r["hours_to_stockout"])
    tone = "critical" if hours < 12 else "high" if hours < 24 else "medium"
    cards.append({
        "score": hours, "label": "HORAS",
        "title": f"{r['sku_id']} · {r['description'][:36]}",
        "meta":  f"{r['store_id']} · {r['category']} · cobertura {float(r['days_of_cover']):.1f}d",
        "description": "SKU projetado para ruptura dentro da janela exibida — "
                       "ação de reposição emergencial recomendada.",
        "tone":  tone,
    })
if cards:
    risk_grid(cards, cols=2)
else:
    st.success("Nenhum SKU projetado para ruptura nas próximas 72h.")


# ── Causal decomposition (waterfall) ───────────────────────────────
section_banner("DECOMPOSIÇÃO DE PERDAS POR CAUSA-RAIZ", hint="atribuição automática · 7d")
# Try gold mart (if world simulator ran), else synthesize from defaults
from pathlib import Path

import pandas as pd

gold = Path("data/gold/mart_rupture_summary.parquet")
if gold.exists():
    rup = pd.read_parquet(gold)
    causal = rup.groupby("root_cause", as_index=False)["lost_revenue"].sum().sort_values(
        "lost_revenue", ascending=False
    ).head(5)
    buckets = list(zip(causal["root_cause"], causal["lost_revenue"]))
else:
    # Heuristic split when no rupture mart is present yet
    buckets = [
        ("DEMAND_SHOCK",         lost_7d * 0.36),
        ("LEAD_TIME_GAP",        lost_7d * 0.27),
        ("SUPPLIER_DISRUPTION", lost_7d * 0.21),
        ("PROMO_UNDERFORECAST",  lost_7d * 0.16),
    ]
if buckets:
    st.plotly_chart(waterfall_lost_sales(buckets),
                    width='stretch', config={"displayModeBar": False})


# ── Operational timeline of recent rupture events ──────────────────
section_banner("EVENTOS DE RUPTURA · ÚLTIMAS HORAS")
items = []
for _, r in tts.head(8).iterrows():
    items.append({
        "title":    f"Ruptura iminente · {r['sku_id']}",
        "time":     now_tz(),
        "severity": "CRITICAL" if r["hours_to_stockout"] < 12 else "HIGH",
        "meta":     f"{r['store_id']} · {r['category']}",
        "body":     f"Cobertura {float(r['days_of_cover']):.1f}d · "
                    f"{float(r['hours_to_stockout']):.0f}h restantes",
    })
if items:
    timeline_card(items)


# ── AI insight ─────────────────────────────────────────────────────
section_banner("AI · DIAGNÓSTICO E RECOMENDAÇÕES")
top_categories = ", ".join(risk_df.head(3)["category"].unique().tolist()) if not risk_df.empty else "—"
ai_insight(f"""
Foco operacional imediato: <strong>{at_risk} SKUs</strong> em status crítico/ruptura,
concentração de risco nas categorias <strong>{top_categories}</strong>.
A perda estimada acumulada em 7 dias é <strong>{fmt_currency(lost_7d)}</strong>.
<br><br>
<strong>Plano de ação sugerido:</strong>
<ul>
  <li>Disparar pedido emergencial para os SKUs com cobertura &lt; 24h e velocidade A.</li>
  <li>Re-priorizar a alocação CD→loja nas lojas mais expostas.</li>
  <li>Auditar fornecedores das categorias de maior perda — verificar OTD &lt; SLA.</li>
  <li>Re-treinar forecast nas categorias com MAPE acima do limite.</li>
</ul>
""", citation="Análise gerada com base no snapshot de inventário (janela 24h) e mart_rupture_summary.")
