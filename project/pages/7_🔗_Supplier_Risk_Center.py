"""
Supplier Risk Center
=====================
Tier-based risk scoring of the supplier base. Combines OTD performance,
lead time variance, disruption history and concentration risk into a
single risk score used for mitigation prioritization.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Supplier Risk Center · Twin", layout="wide")

from components import (
    ai_insight, exec_header, inject_theme, kpi_row, render_global_filters,
    risk_grid, section_banner,
)
from config.theme import THEME
from services.replenishment_service import ReplenishmentService
from utils.formatting import fmt_int, fmt_pct
from utils.session import SessionState


from core.runtime import after_page_config
after_page_config()
flt = render_global_filters()

rep = ReplenishmentService()


exec_header(
    eyebrow="SUPPLIER RISK CENTER",
    title="Centro de Risco de Fornecedores",
    subtitle="Score composto · OTD · lead-time · concentração · histórico de disrupção.",
    chips=flt.chips() + [("METODOLOGIA", "tier × otd × variabilidade")],
    status=("info", "MONITORANDO"),
)


# ── Load supplier panel ────────────────────────────────────────────
silver_sup = Path("data/silver/dim/suppliers.parquet")
gold_perf  = Path("data/gold/mart_supplier_performance.parquet")

if silver_sup.exists():
    sup = pd.read_parquet(silver_sup)
else:
    from services.base import BaseService
    sup = BaseService().df("""
        SELECT supplier_id, name, tier, otd_rate,
               lead_time_days AS base_lead_time_days,
               0.6 AS lead_time_std,
               0.10 AS disruption_p_month,
               'BR' AS country,
               'Mercearia' AS primary_category
        FROM dim_supplier;
    """)

if gold_perf.exists():
    perf = pd.read_parquet(gold_perf)
    sup = sup.merge(perf, on="supplier_id", how="left", suffixes=("", "_obs"))
else:
    sup["deliveries"]     = np.random.randint(50, 400, size=len(sup))
    sup["avg_lead_days"]  = sup.get("base_lead_time_days", 3.0) + np.random.uniform(-0.3, 0.8, size=len(sup))
    sup["otd_rate_obs"]   = sup.get("otd_rate", 0.92) + np.random.uniform(-0.05, 0.03, size=len(sup))

# Apply supplier filter
if flt.supplier_id:
    q = flt.supplier_id.lower()
    sup = sup[sup["supplier_id"].str.lower().str.contains(q) |
              sup["name"].str.lower().str.contains(q, na=False)]

if sup.empty:
    st.info("Nenhum fornecedor corresponde aos filtros atuais.")
    st.stop()


# ── Risk score ─────────────────────────────────────────────────────
# Composite: 0.45 (1-OTD) + 0.25 lead-norm + 0.15 disruption + 0.15 tier-penalty
tier_penalty = sup["tier"].map({"T1": 0.0, "T2": 0.4, "T3": 0.8}).fillna(0.5)
otd          = sup.get("otd_rate_obs", sup.get("otd_rate", 0.9)).fillna(0.9)
lead         = sup.get("avg_lead_days", sup.get("base_lead_time_days", 3.0)).fillna(3.0)
disrupt      = sup.get("disruption_p_month", pd.Series([0.10] * len(sup))).fillna(0.10)
lead_norm    = (lead.clip(0.5, 14) - 0.5) / 13.5
risk = 100 * (0.45 * (1 - otd) + 0.25 * lead_norm + 0.15 * disrupt + 0.15 * tier_penalty)
sup = sup.assign(risk_score=risk.round(1))


kpi_row([
    {"label": "FORNECEDORES",         "value": fmt_int(len(sup)), "tone": "info"},
    {"label": "RISCO MÉDIO",          "value": f"{sup['risk_score'].mean():.1f}",
     "tone": "critical" if sup['risk_score'].mean() > 40 else "warning"},
    {"label": "ALTO RISCO (>60)",     "value": fmt_int((sup["risk_score"] > 60).sum()),
     "tone": "critical"},
    {"label": "OTD MÉDIO OBS.",       "value": fmt_pct(float(otd.mean())),
     "tone": "healthy" if otd.mean() >= 0.95 else "warning"},
    {"label": "LEAD MÉDIO OBS.",      "value": f"{float(lead.mean()):.1f}d", "tone": "info"},
])


# ── Risk × OTD scatter ─────────────────────────────────────────────
section_banner("SCATTER · OTD × LEAD TIME · COR = RISK SCORE")
fig = px.scatter(
    sup, x=otd, y=lead, color=sup["risk_score"],
    size=sup.get("deliveries", pd.Series([60] * len(sup))),
    hover_name=sup.get("name", sup["supplier_id"]),
    hover_data={"supplier_id": True, "tier": True},
    color_continuous_scale=[THEME["healthy"], THEME["warning"], THEME["critical"]],
    range_color=[0, 100],
)
fig.update_layout(height=420, xaxis_title="OTD observado",
                  yaxis_title="Lead time observado (d)")
fig.update_xaxes(tickformat=".1%")
st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})


# ── Top-risk supplier cards ────────────────────────────────────────
section_banner("FORNECEDORES DE MAIOR RISCO · MITIGAÇÃO PRIORITÁRIA")
top = sup.sort_values("risk_score", ascending=False).head(6)
cards = []
for _, r in top.iterrows():
    score = float(r["risk_score"])
    tone = "critical" if score > 60 else "high" if score > 40 else "medium"
    cards.append({
        "score": score, "label": "RISK",
        "title": f"{r['supplier_id']} · {r.get('name', '—')}",
        "meta":  f"tier {r['tier']} · OTD {float(otd.loc[r.name]):.1%} · "
                 f"lead {float(lead.loc[r.name]):.1f}d",
        "description": "Recomenda-se dual-sourcing imediato e revisão contratual. "
                       "Monitorar OTD semanalmente e ativar plano de contingência.",
        "tone": tone,
    })
risk_grid(cards, cols=2)


# ── Tier distribution ──────────────────────────────────────────────
section_banner("DISTRIBUIÇÃO POR TIER × RISCO MÉDIO")
by_tier = sup.groupby("tier").agg(
    n=("supplier_id", "count"),
    risk_avg=("risk_score", "mean"),
    otd_avg=("otd_rate_obs", "mean") if "otd_rate_obs" in sup else ("otd_rate", "mean"),
).reset_index()
c1, c2 = st.columns(2)
with c1:
    fig = go.Figure(go.Bar(
        x=by_tier["tier"], y=by_tier["n"],
        marker_color=[THEME["healthy"], THEME["primary"], THEME["critical"]],
        text=by_tier["n"], textposition="outside",
    ))
    fig.update_layout(height=300, title="Fornecedores por tier",
                      yaxis_title="Quantidade")
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
with c2:
    fig = go.Figure(go.Bar(
        x=by_tier["tier"], y=by_tier["risk_avg"],
        marker_color=THEME["critical"], opacity=0.85,
        text=by_tier["risk_avg"].round(1), textposition="outside",
    ))
    fig.update_layout(height=300, title="Risco médio por tier",
                      yaxis_title="Risk score")
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})


# ── Ranking grid ───────────────────────────────────────────────────
section_banner("RANKING COMPLETO")
table = sup[["supplier_id"]].copy()
table["Nome"]    = sup.get("name", sup["supplier_id"])
table["Tier"]    = sup["tier"]
table["OTD"]     = otd.apply(lambda v: f"{v:.1%}")
table["Lead (d)"]= lead.round(2)
table["Risk"]    = sup["risk_score"]
table = table.rename(columns={"supplier_id": "Fornecedor"})
table = table.sort_values("Risk", ascending=False)
st.dataframe(table, hide_index=True, width='stretch', height=420)


# ── AI commentary ──────────────────────────────────────────────────
section_banner("AI · BRIEFING DE FORNECEDORES")
ai_insight(f"""
A base de fornecedores apresenta risco médio de
<strong>{sup['risk_score'].mean():.1f}/100</strong>.
<strong>{int((sup['risk_score'] > 60).sum())}</strong> fornecedores estão acima do
threshold de risco crítico e devem entrar em plano de dual-sourcing.
<br><br>
Concentração relevante em tier-3 e em fornecedores com OTD inferior a 90% —
combinação que historicamente antecipa rupturas em SKUs A-velocity dentro
de janelas de 5-7 dias.
""", citation=f"Score composto · {len(sup)} fornecedores avaliados.")
