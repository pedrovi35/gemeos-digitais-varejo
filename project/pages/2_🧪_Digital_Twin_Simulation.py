"""
Digital Twin Simulation
========================
Operational simulator. Apply scenarios to the live twin and observe
the projected operational impact before committing to a playbook.
"""
from __future__ import annotations

import json

import streamlit as st

st.set_page_config(page_title="Digital Twin Simulation · Twin", layout="wide")

from agents.copilot import OperationsCopilot
from analytics.what_if import WhatIfAnalytics
from components import (
    ai_insight, exec_header, inject_theme, kpi_row, render_global_filters,
    risk_grid, section_banner,
)
from services.kpi_service import KpiService
from simulation.engine import SimulationEngine
from simulation.scenarios import ScenarioCatalog
from utils.cache import cached_resource
from utils.formatting import fmt_currency, fmt_int, fmt_pct
from utils.session import SessionState


from core.runtime import after_page_config
after_page_config()
flt = render_global_filters()


@cached_resource()
def get_engine() -> SimulationEngine:
    return SimulationEngine()


engine  = get_engine()
kpi     = KpiService()
wif     = WhatIfAnalytics()
copilot = OperationsCopilot()


exec_header(
    eyebrow="DIGITAL TWIN · SIMULATION LAB",
    title="Simulação Operacional · Stress Test de Cenários",
    subtitle="Aplique disrupções ao gêmeo digital e projete o impacto antes da decisão.",
    chips=flt.chips() + [("ENGINE", "discrete-event"), ("TICKS", "configurable")],
    status=("info", "PRONTO PARA STRESS-TEST"),
)


# ── Scenario selector & parameters ─────────────────────────────────
left, right = st.columns([1.3, 2])

with left:
    section_banner("CATÁLOGO DE CENÁRIOS")
    options = ScenarioCatalog.all()
    code = st.radio(
        "Cenário", options=[s.code for s in options],
        format_func=lambda c: ScenarioCatalog.by_code(c).name,
        label_visibility="collapsed",
    )
    scenario = ScenarioCatalog.by_code(code)
    st.markdown(
        f"<div class='panel'><div class='panel__title'>{scenario.name}</div>"
        f"<div style='color:var(--text-muted); font-size:13px; margin-top:6px;'>"
        f"{scenario.description}</div>"
        f"<div style='margin-top:10px;'>"
        f"<span class='chip'>SEVERIDADE · <strong>{scenario.severity}</strong></span>"
        f"<span class='chip'>HORIZONTE · <strong>{scenario.horizon_hours}h</strong></span>"
        f"</div></div>",
        unsafe_allow_html=True,
    )

with right:
    section_banner("PARÂMETROS DE STRESS")
    p1, p2, p3 = st.columns(3)
    demand_shock = p1.slider("Multiplicador de demanda", 0.5, 3.0, 1.0, 0.05)
    supplier_otd = p2.slider("OTD do fornecedor",        0.40, 0.99, 0.95, 0.01)
    lead_time    = p3.slider("Lead time (dias)",         1, 14, 3)
    horizon      = st.slider("Horizonte de projeção (dias)", 1, 30, 7)
    run_col, sim_col = st.columns(2)
    run_what_if = run_col.button("▶ Projetar impacto", type="primary", width='stretch')
    run_sim     = sim_col.button("⚙ Rodar simulação (24 ticks)", width='stretch')


# ── What-if projection ─────────────────────────────────────────────
today = kpi.today(flt.store_id)
baseline_sl = float(today.get("service_level") or 0.98)
baseline_so = float(today.get("stockout_pct") or 0.015)
baseline_rev = float(today.get("revenue_today") or 250_000)

result = wif.project(
    baseline_service_level=baseline_sl, baseline_stockout_pct=baseline_so,
    baseline_daily_revenue=baseline_rev, demand_shock=demand_shock,
    supply_otd=supplier_otd, lead_time_days=lead_time, horizon_days=horizon,
)

section_banner("PROJEÇÃO · BASELINE vs CENÁRIO")
kpi_row([
    {"label": "SL · BASELINE",        "value": fmt_pct(result.baseline_service_level),
     "tone": "healthy"},
    {"label": "SL · PROJETADO",       "value": fmt_pct(result.projected_service_level),
     "tone": "healthy" if result.projected_service_level >= 0.98 else "warning"},
    {"label": "RUPTURA · BASELINE",   "value": fmt_pct(result.baseline_stockout_pct),
     "tone": "info"},
    {"label": "RUPTURA · PROJETADA",  "value": fmt_pct(result.projected_stockout_pct),
     "tone": "critical" if result.projected_stockout_pct > 0.05 else "warning"},
    {"label": "PERDA · PROJETADA",    "value": fmt_currency(result.projected_lost_revenue),
     "tone": "critical"},
    {"label": "CONFIANÇA",            "value": fmt_pct(result.confidence),
     "tone": "info"},
])


# ── Execute simulation ─────────────────────────────────────────────
if run_sim:
    with st.status("Aplicando cenário ao Digital Twin…", expanded=True) as status:
        engine.reset()
        engine.apply_scenario(scenario)
        st.write(f"✓ Cenário aplicado: **{scenario.name}**")
        stats = engine.run(ticks=24)
        st.write(f"✓ Ticks executados: **{stats.ticks}** · eventos: **{stats.events}**")
        st.write(f"✓ Stockouts: **{stats.stockouts}** · reorders: **{stats.reorders}**")
        status.update(label="Simulação concluída", state="complete")
    SessionState.set("last_scenario", {
        "code": scenario.code, "name": scenario.name,
        "events": stats.events, "stockouts": stats.stockouts, "reorders": stats.reorders,
    })


# ── Risk cards (impact breakdown) ──────────────────────────────────
section_banner("ANATOMIA DO IMPACTO")
risk_grid([
    {"score": result.projected_lost_revenue / 1000, "label": "R$ k",
     "title": "Receita em risco no horizonte",
     "meta":  f"horizonte {horizon}d · cenário {scenario.code}",
     "description": "Estimativa direta a partir da queda de service level multiplicada pela "
                    "receita média diária da loja/rede.",
     "tone": "critical"},
    {"score": (result.projected_stockout_pct - result.baseline_stockout_pct) * 100,
     "label": "ΔPP", "title": "Deterioração da ruptura",
     "meta":  "vs. linha de base",
     "description": "Aumento estimado da taxa de ruptura ao final do horizonte de projeção.",
     "tone": "high"},
    {"score": (result.baseline_service_level - result.projected_service_level) * 100,
     "label": "ΔPP", "title": "Queda de service level",
     "meta":  "vs. linha de base",
     "description": "Penalidade composta de demanda + OTD ruim + lead time.",
     "tone": "high"},
    {"score": lead_time, "label": "DIAS", "title": "Lead time efetivo",
     "meta":  "parâmetro de stress",
     "description": "Lead time considerado nesta simulação — quanto maior, maior o gap de cobertura.",
     "tone": "medium"},
], cols=2)


# ── AI briefing ────────────────────────────────────────────────────
if run_what_if:
    section_banner("AI · BRIEFING EXECUTIVO")
    with st.spinner("Gerando briefing via Groq…"):
        projection_json = json.dumps({
            "scenario": scenario.name,
            "baseline_service_level": result.baseline_service_level,
            "projected_service_level": result.projected_service_level,
            "projected_stockout_pct": result.projected_stockout_pct,
            "projected_lost_revenue": result.projected_lost_revenue,
            "demand_shock": demand_shock, "supplier_otd": supplier_otd,
            "lead_time_days": lead_time, "horizon_days": horizon,
        }, indent=2)
        brief = copilot.scenario_brief(scenario.name, projection_json)
    ai_insight(brief, citation=f"Cenário · {scenario.code} · horizonte {horizon}d")
