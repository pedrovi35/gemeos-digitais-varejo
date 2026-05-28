"""
Rupture Control Tower — unified observability across R1–R5.
"""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Torre de Controle de Ruptura · Gêmeo Digital", page_icon="assets/favicon.svg", layout="wide")

from agents.ai_service import AIService
from components import exec_header, inject_theme, kpi_row, render_global_filters, section_banner
from components.ml_charts import risk_matrix_heatmap, rupture_radar
from components.charts import kpi_gauge
from config.theme import THEME
from models.shared.registry import MODEL_CATALOG, RuptureCode
from services.risk_service import get_risk_service
from utils.formatting import fmt_pct
from utils.session import SessionState


from core.runtime import after_page_config
after_page_config()
flt = render_global_filters()
risk = get_risk_service()
tower = risk.tower_summary(store_id=flt.store_id)
kpis = risk.operational_kpis(flt.store_id)

exec_header(
    eyebrow="INTELIGÊNCIA OPERACIONAL",
    title="Rupture Control Tower",
    subtitle="Torre de controle preditiva · 5 rupturas críticas de abastecimento",
    chips=flt.chips() + [("NRI", f"{tower['network_risk_index']:.0f}/100")],
    status=("critical" if tower["network_risk_index"] > 55 else "warning",
            "MALHA SOB PRESSÃO" if tower["network_risk_index"] > 45 else "OBSERVAÇÃO ATIVA"),
)

kpi_row([
    {"label": "NETWORK RISK INDEX", "value": f"{tower['network_risk_index']:.0f}",
     "tone": "critical" if tower["network_risk_index"] > 55 else "warning"},
    {"label": "FILL RATE", "value": fmt_pct(kpis["fill_rate"]), "tone": "info"},
    {"label": "OTIF", "value": fmt_pct(kpis["otif"]), "tone": "healthy"},
    {"label": "FORECAST ACC.", "value": fmt_pct(kpis["forecast_accuracy"]), "tone": "info"},
    {"label": "RUPTURA %", "value": fmt_pct(kpis["rupture_pct"]),
     "tone": "critical" if kpis["rupture_pct"] > 0.02 else "healthy"},
    {"label": "SERVICE LEVEL", "value": fmt_pct(kpis["service_level"]), "tone": "info"},
])

c1, c2, c3 = st.columns([1.1, 1.4, 1.5])
with c1:
    st.plotly_chart(kpi_gauge(tower["network_risk_index"], title="Network Risk Index"),
                    width='stretch', config={"displayModeBar": False})
    st.plotly_chart(rupture_radar(tower["ruptures"]),
                    width='stretch', config={"displayModeBar": False})
with c2:
    section_banner("PAINEL DE RUPTURAS · R1–R5")
    for r in tower["ruptures"]:
        col_a, col_b, col_c = st.columns([2, 1, 1])
        with col_a:
            st.markdown(f"**{r['code']}** · {r['name']}")
            st.progress(min(1.0, r["avg_risk"]), text=f"Risco médio {r['avg_risk']:.0%}")
        with col_b:
            st.metric("Críticos", r["critical_count"])
        with col_c:
            st.metric("Entidades", r["entities"])
with c3:
    section_banner("TOP ENTIDADES · RISCO COMPOSTO")
    if tower["top_entities"]:
        import pandas as pd
        top_df = pd.DataFrame(tower["top_entities"])
        st.dataframe(top_df, width='stretch', hide_index=True)
    else:
        st.info("Execute treinamento em ML Operations Center.")

section_banner("MATRIZ DE RISCO · ENTIDADE × RUPTURA")
matrix = risk.composite_matrix(flt.store_id)
st.plotly_chart(risk_matrix_heatmap(matrix.head(25)),
                width='stretch', config={"displayModeBar": False})

section_banner("IA · INTERPRETAÇÃO EXECUTIVA DOS MODELOS")
if st.button("Gerar briefing Groq dos modelos preditivos", type="primary"):
    with st.spinner("Montando contexto operacional + Groq…"):
        resp = AIService().interpret_ml_risk(store_id=flt.store_id)
        from components import render_analysis
        render_analysis(resp)
