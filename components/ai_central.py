"""
Central de IA — sidebar widget that produces a holistic system report
in plain Portuguese using Groq, so the user does not need to navigate
page by page to know what is happening.
"""
from __future__ import annotations

import streamlit as st

from agents.groq_client import GroqClient
from analytics.network_health import NetworkHealthAnalytics
from analytics.stockout_analytics import StockoutAnalytics
from services.alert_service import AlertService
from services.kpi_service import KpiService


_SYS_PROMPT = (
    "Você é o copiloto operacional do Gêmeo Digital de Varejo. "
    "Recebe um snapshot estruturado do sistema e produz um RELATÓRIO EXECUTIVO "
    "em português do Brasil, em markdown, organizado em seções: "
    "1) Visão geral da operação · 2) Saúde da rede · 3) Ruptura e perdas · "
    "4) Fornecedores e abastecimento · 5) Alertas ativos · 6) Recomendações priorizadas. "
    "Seja direto, use bullets curtos e números do snapshot. "
    "Nunca invente métricas fora do snapshot. Máximo ~400 palavras."
)


def _collect_snapshot(store_id: str | None) -> dict:
    kpi   = KpiService()
    hlt   = NetworkHealthAnalytics()
    stock = StockoutAnalytics()
    alrt  = AlertService()

    snap: dict = {"scope": store_id or "rede inteira"}
    try:
        snap["kpis_hoje"] = kpi.today(store_id)
    except Exception as e:
        snap["kpis_hoje"] = {"erro": str(e)}
    try:
        snap["network_health"] = {
            "score": round(float(hlt.score()), 1),
            "grade": hlt.grade(),
            "status": hlt.status_label(),
        }
    except Exception as e:
        snap["network_health"] = {"erro": str(e)}
    try:
        rs = stock.risk_surface().head(5)
        snap["top_risco_ruptura"] = rs.to_dict(orient="records") if not rs.empty else []
        snap["perda_estimada_7d"] = float(stock.lost_sales_estimate(days=7))
    except Exception as e:
        snap["top_risco_ruptura"] = {"erro": str(e)}
    try:
        al = alrt.open()
        snap["alertas_abertos"] = int(len(al)) if al is not None else 0
        if al is not None and not al.empty:
            cols = [c for c in ("severity", "category", "message") if c in al.columns]
            snap["alertas_amostra"] = al[cols].head(6).to_dict(orient="records")
    except Exception as e:
        snap["alertas_abertos"] = {"erro": str(e)}
    return snap


def _build_report(snapshot: dict) -> str:
    llm = GroqClient()
    if not llm.online:
        return (
            "**Modo offline.** A IA Groq não está configurada — defina `GROQ_API_KEY` "
            "para gerar o relatório consolidado."
        )
    payload = (
        "Snapshot do sistema (JSON-like):\n\n"
        f"{snapshot}\n\n"
        "Gere o relatório executivo conforme as instruções do sistema."
    )
    return llm.complete(
        [
            {"role": "system", "content": _SYS_PROMPT},
            {"role": "user",   "content": payload},
        ],
        temperature=0.3,
        max_tokens=900,
    )


def render_ai_central(store_id: str | None = None) -> None:
    """Render the AI sidebar widget. Call from inside the sidebar block."""
    st.markdown("### CENTRAL DE IA")
    st.caption("Resumo automático do sistema inteiro, sem precisar abrir aba por aba.")

    if st.button("Gerar relatório do sistema", type="primary", use_container_width=True,
                 key="ai_central_btn"):
        with st.spinner("Coletando snapshot e consultando a IA…"):
            snap = _collect_snapshot(store_id)
            st.session_state["ai_central_report"] = _build_report(snap)

    report = st.session_state.get("ai_central_report")
    if report:
        with st.expander("Relatório consolidado", expanded=True):
            st.markdown(report)
            if st.button("Limpar relatório", key="ai_central_clear",
                         use_container_width=True):
                st.session_state.pop("ai_central_report", None)
                st.rerun()
