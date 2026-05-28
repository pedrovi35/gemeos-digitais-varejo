"""
Gêmeo Digital de Varejo · Executive Control Tower
==================================================
Operational Intelligence platform for retail supply chain rupture prevention.
"""
from __future__ import annotations

# Secrets before any settings import (Streamlit Cloud + local .env)
from core.secrets import hydrate_settings_from_secrets
hydrate_settings_from_secrets()

import numpy as np
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Gêmeo Digital · Torre de Controle",
    page_icon="assets/favicon.svg",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "Gêmeo Digital de Varejo — Operational Intelligence"},
)

from analytics.network_health import NetworkHealthAnalytics
from analytics.stockout_analytics import StockoutAnalytics
from components import (
    ai_insight, exec_header, kpi_row, render_alert_feed,
    render_global_filters, section_banner,
)
from components.charts import kpi_gauge, kpi_radial
from components.fallback import offline_llm_banner
from config.settings import settings
from config.theme import THEME
from core.errors import run_safe
from core.runtime import after_page_config
from services.alert_service import AlertService
from services.kpi_service import KpiService
from services.sales_service import SalesService
from agents.ai_service import AIService
from utils.formatting import fmt_compact, fmt_currency, fmt_int, fmt_pct
from utils.session import SessionState

after_page_config()

flt = render_global_filters()
scope = flt.store_id

kpi_svc   = KpiService()
sales_svc = SalesService()
alert_svc = AlertService()
stockout  = StockoutAnalytics()
health    = NetworkHealthAnalytics()

if not settings.groq.api_key:
    offline_llm_banner()


def _render_main() -> None:
    today_kpi = kpi_svc.today(scope)
    trend_30d = kpi_svc.trend(days=30, store_id=scope)

    hs = health.score()
    status_tone  = "healthy" if hs >= 85 else "warning" if hs >= 70 else "critical"
    exec_header(
        eyebrow="TORRE DE CONTROLE EXECUTIVA",
        title="Centro de Operações · Supply Chain Intelligence",
        subtitle=settings.tagline,
        chips=flt.chips() + [("SCORE", f"{hs:.0f}/100"), ("GRADE", health.grade())],
        status=(status_tone, health.status_label()),
    )

    revenue = float(today_kpi.get("revenue_today") or 0)
    units   = int(today_kpi.get("units_today") or 0)
    sl      = float(today_kpi.get("service_level") or 0)
    so      = float(today_kpi.get("stockout_pct") or 0)
    fill    = float(today_kpi.get("fill_rate") or 0)
    mape    = float(today_kpi.get("forecast_mape") or 0)
    otif    = (sl + fill) / 2.0
    op_risk = max(0.0, min(100.0, (so * 100 * 6) + ((1 - sl) * 100 * 3) + (mape * 100 * 1.5)))

    kpi_row([
        {"label": "RECEITA · HOJE",    "value": fmt_currency(revenue),
         "delta": "operação ativa",    "delta_dir": "up",  "tone": "info"},
        {"label": "UNIDADES VENDIDAS", "value": fmt_compact(units),  "tone": "info"},
        {"label": "SERVICE LEVEL",     "value": fmt_pct(sl),
         "delta": "target 98.5%",      "delta_dir": "up" if sl >= 0.985 else "down",
         "tone": "healthy" if sl >= 0.985 else "warning"},
        {"label": "OTIF",              "value": fmt_pct(otif),
         "tone": "healthy" if otif >= 0.96 else "warning"},
        {"label": "RUPTURA",           "value": fmt_pct(so),
         "tone": "critical" if so > 0.02 else "healthy"},
        {"label": "OP. RISK INDEX",    "value": f"{op_risk:.0f}",
         "tone": "critical" if op_risk > 35 else "warning" if op_risk > 18 else "healthy"},
    ])

    section_banner("SAÚDE OPERACIONAL · INTELIGÊNCIA DA REDE")
    c1, c2, c3 = st.columns([1.0, 1.5, 1.5])

    with c1:
        st.plotly_chart(kpi_gauge(hs, title="Network Health Score"),
                        width="stretch", config={"displayModeBar": False})
        radar_vals = {
            "Nível Serviço": sl * 100, "Fill Rate": fill * 100,
            "OTIF":           otif * 100, "Previsão": (1 - mape) * 100,
            "Disponibilidade": (1 - so) * 100,
        }
        st.plotly_chart(kpi_radial(radar_vals), width="stretch",
                        config={"displayModeBar": False})

    with c2:
        section_banner("RECEITA · TENDÊNCIA 30 DIAS")
        if not trend_30d.empty:
            rev = trend_30d["revenue"].values
            dates = trend_30d["snapshot_date"].values
            colors = [THEME["critical"] if r < rev.mean() * 0.85 else
                      THEME["warning"] if r < rev.mean() * 0.95 else
                      THEME["primary"] for r in rev]
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=dates, y=rev,
                marker=dict(color=colors, opacity=0.88,
                            line=dict(width=0)),
                hovertemplate="<b>%{x}</b><br>Receita: R$ %{y:,.0f}<extra></extra>",
            ))
            avg = float(np.mean(rev))
            fig.add_hline(y=avg, line_dash="dot", line_color=THEME["text_dim"],
                         line_width=1, opacity=0.6,
                         annotation_text=f"Média R${avg:,.0f}",
                         annotation_font_color=THEME["text_muted"],
                         annotation_font_size=10)
            fig.update_layout(
                height=260, showlegend=False,
                margin=dict(l=8, r=8, t=8, b=8),
                xaxis=dict(tickfont=dict(size=10), tickangle=-35),
                yaxis=dict(tickformat=",.0f"),
            )
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        else:
            st.info("Aguardando dados de receita.")

        section_banner("DISPONIBILIDADE POR STORE")
        sl_df = sales_svc.revenue_by_category(days=7)
        if not sl_df.empty:
            fig2 = go.Figure(go.Bar(
                x=sl_df["revenue"], y=sl_df["category"],
                orientation="h",
                marker=dict(
                    color=sl_df["revenue"],
                    colorscale=[[0, THEME["bg_overlay"]], [0.5, THEME["primary"]], [1, THEME["tertiary"]]],
                    opacity=0.9,
                ),
                hovertemplate="<b>%{y}</b><br>R$ %{x:,.0f}<extra></extra>",
            ))
            fig2.update_layout(height=200, showlegend=False, margin=dict(l=8, r=8, t=8, b=8))
            st.plotly_chart(fig2, width="stretch", config={"displayModeBar": False})

    with c3:
        section_banner("TOP RISCOS OPERACIONAIS")
        risk = stockout.risk_surface().head(5)
        if risk.empty:
            st.info("Sem riscos materiais detectados.")
        else:
            from components.risk_card import risk_card
            for _, r in risk.iterrows():
                score = float(r["risk_score"])
                risk_card(
                    score=score, label="RISCO %",
                    title=f"{r['category']} · {r['store_id']}",
                    meta=f"{int(r['skus'])} SKUs monitorados",
                    description=f"Score de ruptura: {score:.1f}% do mix em criticidade.",
                    tone="critical" if score >= 25 else "high" if score >= 15 else "medium",
                )

    section_banner("INSIGHT DE IA · INTELIGÊNCIA OPERACIONAL")
    lost_7d = stockout.lost_sales_estimate(days=7)
    ai_body = (
        f"**Network Health Score:** {hs:.0f}/100 — {health.status_label()}. "
        f"**Service Level:** {fmt_pct(sl)} · **OTIF:** {fmt_pct(otif)} · "
        f"**Ruptura:** {fmt_pct(so)}. "
        f"**Perda estimada 7 dias:** {fmt_currency(lost_7d)}. "
        f"**Risk Index:** {op_risk:.0f}/100 — "
        + ("situação requer atenção imediata." if op_risk > 35 else
           "operação dentro dos parâmetros." if op_risk < 18 else
           "monitorar indicadores de abastecimento.")
    )
    ai_insight(ai_body, citation=f"Digital Twin v{settings.version} · {from_utils()}")

    section_banner("ALERTAS ATIVOS · PRIORIDADE")
    render_alert_feed(alert_svc.open(), max_rows=8)

    st.markdown(
        f"<div class='ops-footer'>"
        f"<span><strong>{settings.name}</strong> v{settings.version}</span>"
        f"<span>DuckDB · XGBoost · LightGBM · Groq</span>"
        f"<span>Operational Intelligence Platform</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


def from_utils() -> str:
    from utils.time_utils import now_tz
    return now_tz().strftime("%d/%m/%Y %H:%M")


run_safe(_render_main, context="Executive Control Tower")
