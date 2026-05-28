"""
Prova de Valor — controlled experiment that quantifies what the digital
twin would have prevented in a (cutoff, cutoff+H] window it never saw
during training. Lifts the curtain on:

    1. Predictive validity (out-of-time AUC, precision@k)
    2. Calibration (predicted risk vs realized rate)
    3. Operational value (events avoided, R$ saved, ROI of intervention)
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Prova de Valor · Gêmeo Digital",
                   page_icon="assets/favicon.svg", layout="wide")

from components import exec_header, kpi_row, section_banner   # noqa: E402
from components.calibration_chart import (                    # noqa: E402
    lead_time_distribution, precision_at_k_curve, reliability_diagram,
)
from core.runtime import after_page_config, sidebar_runtime_controls  # noqa: E402
from models.shared.registry import RuptureCode                # noqa: E402
from services.backtest_service import score_window            # noqa: E402
from services.counterfactual_service import aggregate, simulate  # noqa: E402
from utils.time_utils import now_tz                           # noqa: E402

after_page_config(show_health=False)
sidebar_runtime_controls()

exec_header(
    eyebrow="EXPERIMENTO CONTROLADO",
    title="Prova de Valor do Gêmeo Digital",
    subtitle=("Backtest walk-forward + contrafactual de intervenção · "
              "métricas out-of-time, ground truth do seed"),
    chips=[
        ("METODOLOGIA", "WALK-FORWARD"),
        ("UNIVERSOS", "BASELINE × TWIN"),
    ],
    status=("info", "EVIDÊNCIA"),
)

# ── Controles ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Parâmetros do experimento")
    today = pd.Timestamp(now_tz()).tz_localize(None).normalize()
    default_cutoff = (today - timedelta(days=21)).date()
    cutoff_date = st.date_input(
        "Data de corte (treina ≤ T, avalia > T)",
        value=default_cutoff,
        min_value=(today - timedelta(days=45)).date(),
        max_value=(today - timedelta(days=8)).date(),
    )
    horizon = st.slider("Horizonte de avaliação (dias)", 3, 14, 7)
    ruptures = st.multiselect(
        "Modelos avaliados",
        options=[c.value for c in RuptureCode],
        default=["R1", "R4"],
        help="R1 e R4 são os que passaram no backtest com sinal real.",
    )
    st.markdown("---")
    st.markdown("### Política de intervenção")
    top_k = st.slider("Top-k alertas por janela", 5, 80, 20)
    effectiveness = st.slider(
        "Eficácia da intervenção", 0.30, 0.95, 0.70, step=0.05,
        help="P(ruptura prevenida | alerta correto + ação executada)",
    )
    intervention_cost = st.number_input(
        "Custo por intervenção (R$)", min_value=0.0, value=50.0, step=10.0,
        help="Custo operacional de um pedido extra, transferência ou desbloqueio.",
    )

cutoff_ts = pd.Timestamp(cutoff_date)

# ── Roda backtest + contrafactual ───────────────────────────────────
@st.cache_data(ttl=900, show_spinner="Treinando modelos e simulando contrafactual…")
def _run(rupture_codes: tuple[str, ...], cutoff_iso: str, horizon: int,
         top_k: int, effectiveness: float, cost: float) -> dict:
    cutoff = pd.Timestamp(cutoff_iso)
    results = {}
    cfs = []
    for v in rupture_codes:
        code = RuptureCode(v)
        win = score_window(code, cutoff, horizon)
        cf = simulate(code, cutoff, horizon=horizon,
                      top_k=top_k, effectiveness=effectiveness,
                      intervention_unit_cost=cost)
        if win is None or cf is None:
            continue
        results[v] = {"scored": win.scored, "in_sample_auc": win.in_sample_auc,
                      "n_train": win.n_train, "cf": cf}
        cfs.append(cf)
    return {"per_rupture": results, "agg": aggregate(cfs)}

run = _run(tuple(ruptures), cutoff_ts.isoformat(), horizon,
           top_k, effectiveness, intervention_cost)

if not run["per_rupture"]:
    st.warning("Não há dados suficientes para a data escolhida. Tente um cutoff mais recente.")
    st.stop()

# ── Painel-resumo: deltas agregados ──────────────────────────────────
agg = run["agg"]
section_banner("DELTAS AGREGADOS · UNIVERSO A vs B")
kpi_row([
    {"label": "RUPTURAS BASELINE",      "value": f"{agg['baseline_events']:.0f}",
     "tone": "critical",
     "hint": f"realizadas em ({horizon}d após T)"},
    {"label": "RUPTURAS EVITADAS",      "value": f"{agg['events_avoided']:.1f}",
     "tone": "healthy",
     "delta": f"{agg['avoidance_rate']:.1%} de redução", "delta_dir": "up"},
    {"label": "PERDA EVITADA",          "value": f"R$ {agg['revenue_saved']:,.0f}",
     "tone": "healthy",
     "hint": f"baseline R$ {agg['baseline_lost_revenue']:,.0f}"},
    {"label": "CUSTO DE INTERVENÇÃO",   "value": f"R$ {agg['intervention_cost']:,.0f}",
     "tone": "warning"},
    {"label": "VALOR LÍQUIDO",          "value": f"R$ {agg['net_value']:,.0f}",
     "tone": "healthy" if agg["net_value"] >= 0 else "critical",
     "hint": "saved − cost"},
])

st.caption(
    "**Metodologia.** Modelos são re-treinados em janela observável ≤ T (sem"
    f" persistência), scoram entidades em T, e a comparação usa eventos *reais*"
    f" do seed em (T, T+{horizon}d]. O contrafactual aplica intervenção nos top-{top_k}"
    f" de maior risco; com eficácia {effectiveness:.0%}, prevenções esperadas = top-k × P(ruptura) × eficácia."
)

# ── Por rupture: KPIs preditivos + 3 gráficos ────────────────────────
for code_v, payload in run["per_rupture"].items():
    cf = payload["cf"]
    scored: pd.DataFrame = payload["scored"]

    section_banner(f"MODELO {code_v} · DIAGNÓSTICO PREDITIVO")
    # AUC out-of-time inline
    from sklearn.metrics import roc_auc_score, average_precision_score
    y, p = scored["realized"].values, scored["risk"].values
    auc_oot = roc_auc_score(y, p) if (y.sum() and y.sum() < len(y)) else float("nan")
    ap_oot  = average_precision_score(y, p) if (y.sum() and y.sum() < len(y)) else float("nan")
    top_realized = scored.head(top_k)["realized"].mean() if len(scored) else 0.0

    kpi_row([
        {"label": "AUC OUT-OF-TIME",  "value": f"{auc_oot:.3f}",
         "tone": "healthy" if auc_oot >= 0.65 else "warning" if auc_oot >= 0.55 else "critical",
         "hint": "≥0.65 = sinal forte · ≥0.55 = fraco · <0.55 = ruído"},
        {"label": "AVG PRECISION",    "value": f"{ap_oot:.3f}",
         "tone": "info", "hint": "área sob PR curve"},
        {"label": f"PRECISION@{top_k}", "value": f"{top_realized:.0%}",
         "tone": "healthy" if top_realized >= 0.25 else "warning",
         "hint": "% dos top-k que realmente ruptaram"},
        {"label": "EVITADAS (esperado)", "value": f"{cf.events_avoided:.1f}",
         "tone": "healthy", "delta": f"de {cf.baseline_events}", "delta_dir": "up"},
        {"label": "R$ EVITADO",       "value": f"R$ {cf.revenue_saved:,.0f}",
         "tone": "healthy"},
    ])

    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        st.plotly_chart(reliability_diagram(scored), width="stretch")
    with c2:
        st.plotly_chart(lead_time_distribution(scored, risk_threshold=0.5),
                        width="stretch")
    with c3:
        st.plotly_chart(precision_at_k_curve(scored), width="stretch")

    with st.expander(f"Drill-down · top-{top_k} entidades alertadas · {code_v}"):
        drill = cf.scored[cf.scored["alerted"] == 1].head(top_k)[
            ["entity_key", "risk", "realized", "lead_days",
             "daily_revenue", "lost_revenue_avoided"]
        ].copy()
        drill["risk"] = drill["risk"].round(3)
        drill["lost_revenue_avoided"] = drill["lost_revenue_avoided"].round(2)
        st.dataframe(drill, width="stretch", hide_index=True)

# ── Disclaimers ──────────────────────────────────────────────────────
section_banner("LIMITAÇÕES E INTERPRETAÇÃO")
st.markdown(
    """
    - **Dados sintéticos.** A "verdade" desta prova vem do seed determinístico
      ([database/seed.py](project/database/seed.py)). Em produção, a mesma metodologia
      é aplicável com dados reais sem alterar o pipeline — só os números mudam.
    - **Modelos válidos.** No backtest atual, apenas **R1** e **R4** generalizam
      out-of-time (AUC ≥ 0.65). R2/R3/R5 estão exibidos para transparência mas
      precisam de mais histórico ou redesenho de target.
    - **Custo da intervenção** é um proxy operacional editável na barra lateral.
      Em rede real, varia por SKU classe / canal logístico.
    - **Eficácia** parametrizável simula a fração de alertas que viram ação
      bem-sucedida. Estudos de campo em retail típico: 0.55–0.80.
    """
)
