"""
Reusable rupture center page renderer — enterprise observability layout
shared across R1–R5 specialized pages.
"""
from __future__ import annotations

import streamlit as st

from components import exec_header, kpi_row, section_banner
from components.ml_charts import (
    feature_importance_bar, risk_matrix_heatmap, risk_timeline, shap_waterfall,
)
from components.charts import stockout_heatmap
from config.theme import THEME
from models.shared.registry import MODEL_CATALOG, RuptureCode
from services.risk_service import get_risk_service
from utils.formatting import fmt_pct


def render_rupture_center(
    code: RuptureCode,
    *,
    eyebrow: str,
    title: str,
    subtitle: str,
    icon: str = "🛰️",
) -> None:
    from core.runtime import after_page_config, render_page_filters
    after_page_config()
    flt = render_page_filters()
    risk = get_risk_service()
    spec = MODEL_CATALOG[code]
    score_col = spec.output

    scored = risk.score_rupture(code)
    if flt.store_id and "store_id" in scored.columns:
        scored = scored[scored["store_id"] == flt.store_id]

    avg_risk = float(scored[score_col].mean()) if not scored.empty else 0.0
    crit = int((scored["risk_level"] == "CRITICAL").sum()) if "risk_level" in scored.columns else 0
    high = int(scored["risk_level"].isin(["HIGH", "CRITICAL"]).sum()) if "risk_level" in scored.columns else 0
    metrics = risk.model_metrics(code)
    kpis = risk.operational_kpis(flt.store_id)

    exec_header(
        eyebrow=eyebrow,
        title=title,
        subtitle=subtitle,
        chips=flt.chips() + [
            ("RISCO MÉDIO", fmt_pct(avg_risk)),
            ("CRÍTICOS", str(crit)),
            ("AUC", f"{metrics.get('roc_auc', 0):.2f}" if metrics else "heurístico"),
        ],
        status=("critical" if avg_risk > 0.6 else "warning" if avg_risk > 0.35 else "healthy",
                "RISCO ELEVADO" if avg_risk > 0.5 else "SOB OBSERVAÇÃO"),
    )

    kpi_row([
        {"label": "SCORE MÉDIO", "value": fmt_pct(avg_risk),
         "tone": "critical" if avg_risk > 0.6 else "warning"},
        {"label": "ENTIDADES CRÍTICAS", "value": str(crit), "tone": "critical" if crit else "healthy"},
        {"label": "ALTO + CRÍTICO", "value": str(high), "tone": "warning"},
        {"label": "FILL RATE", "value": fmt_pct(kpis["fill_rate"]), "tone": "info"},
        {"label": "RUPTURA REDE", "value": fmt_pct(kpis["rupture_pct"]),
         "tone": "critical" if kpis["rupture_pct"] > 0.02 else "healthy"},
    ])

    section_banner("RANKING OPERACIONAL · TOP RISCOS", hint=score_col)
    top = scored.nlargest(20, score_col) if not scored.empty else scored
    if top.empty:
        st.info("Sem scores disponíveis. Execute o treinamento em ML Operations Center.")
    else:
        display_cols = [c for c in ["store_id", "sku_id", "supplier_id", "entity_key",
                                    score_col, "risk_level", "d"] if c in top.columns]
        st.dataframe(
            top[display_cols].style.background_gradient(
                subset=[score_col], cmap="Reds", vmin=0, vmax=1,
            ),
            width='stretch', hide_index=True,
        )

    c1, c2 = st.columns(2)
    with c1:
        section_banner("TIMELINE DE RISCO")
        st.plotly_chart(risk_timeline(scored, score_col=score_col),
                        width='stretch', config={"displayModeBar": False})
    with c2:
        section_banner("IMPORTÂNCIA GLOBAL · MODELO")
        from models.shared.registry import get_model
        imp = get_model(code).explainer.feature_importance()
        st.plotly_chart(feature_importance_bar(imp),
                        width='stretch', config={"displayModeBar": False})

    section_banner("EXPLICABILIDADE SHAP · ENTIDADE SELECIONADA")
    if not top.empty:
        entities = top["entity_key"].tolist() if "entity_key" in top.columns else []
        if entities:
            chosen = st.selectbox("Entidade", entities, key=f"entity_{code.value}")
            row = top[top["entity_key"] == chosen].iloc[0]
            entity = {c: row[c] for c in ["store_id", "sku_id", "supplier_id"] if c in row.index}
            expl = risk.explain(code, entity)
            st.plotly_chart(
                shap_waterfall(expl.top_drivers, title=f"Waterfall SHAP · {chosen}"),
                width='stretch', config={"displayModeBar": False},
            )
            drivers_txt = " · ".join(
                f"**{d.feature}** → {d.impact_pct:+.0f}%"
                for d in expl.top_drivers[:4]
            )
            st.markdown(
                f"<motion-div class='ops-insight'>"
                f"<strong>Drivers operacionais:</strong> {drivers_txt}</div>",
                unsafe_allow_html=True,
            )
            if expl.counterfactuals:
                for cf in expl.counterfactuals:
                    st.caption(f"↳ {cf}")

    if code != RuptureCode.R5 and not scored.empty and "store_id" in scored.columns:
        section_banner("MAPA DE CALOR · LOJA")
        heat = scored.groupby("store_id")[score_col].mean().reset_index()
        heat["category"] = code.value
        st.plotly_chart(
            stockout_heatmap(heat.assign(risk_score=heat[score_col] * 100),
                             x="store_id", y="category", z="risk_score"),
            width='stretch', config={"displayModeBar": False},
        )
