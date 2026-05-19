"""
Analysis Report — uniform renderer for AnalysisResponse.

Every agent returns the same shape; this component is the *only* surface
the UI uses to display analyst output. Keeps look & feel consistent across
every page that consumes the AI layer.
"""
from __future__ import annotations

import streamlit as st

from agents.schemas import AnalysisResponse


_CONF_COLOR = {"LOW": "var(--critical)", "MEDIUM": "var(--warning)", "HIGH": "var(--healthy)"}
_PRIO_COLOR = {"P1": "var(--critical)", "P2": "var(--warning)",  "P3": "var(--primary)"}


def render_analysis(response: AnalysisResponse) -> None:
    """Render an analyst response with the executive template."""
    # ── Hero band ───────────────────────────────────────────────────
    intent_lbl = response.intent.value.replace("_", " ").title()
    conf_color = _CONF_COLOR.get(response.confidence.value, "var(--primary)")
    st.markdown(
        f"""<div class="ai-panel">
              <div class="ai-panel__head">
                <span class="ai-dot"></span>
                AI ANALYSIS · {response.agent.upper()} · {intent_lbl}
              </div>
              <div class="ai-panel__body" style="font-weight:500; font-size:14.5px;">
                {response.headline}
              </div>
              <div class="ai-panel__cite">
                conf. <strong style="color:{conf_color}">{response.confidence.value}</strong>
                · trace <code>{response.trace_id or '—'}</code>
                · model {response.model or '—'}
              </div>
            </div>""",
        unsafe_allow_html=True,
    )

    # ── Markdown narrative ──────────────────────────────────────────
    st.markdown(response.summary)

    # ── Evidence table ──────────────────────────────────────────────
    if response.evidence:
        st.markdown("#### Evidências quantitativas (snapshot do warehouse)")
        ev_rows = [{"Métrica": e.label, "Valor": e.value,
                    "Fonte": e.source, "Peso": f"{e.weight:.2f}"} for e in response.evidence]
        st.dataframe(ev_rows, hide_index=True, width='stretch', height=180)

    # ── Recommendations badges ──────────────────────────────────────
    if response.recommendations:
        st.markdown("#### Recomendações operacionais")
        for r in response.recommendations:
            color = _PRIO_COLOR.get(r.priority, "var(--primary)")
            st.markdown(
                f"<div class='panel' style='display:flex; gap:14px; padding:10px 14px; margin-bottom:6px;'>"
                f"<span class='badge' style='background:rgba(59,130,246,0.10); color:{color};"
                f" border:1px solid {color};'>{r.priority}</span>"
                f"<div><strong>{r.title}</strong>"
                f"<div style='color:var(--text-muted); font-size:12.5px;'>{r.detail}</div></div>"
                f"</div>",
                unsafe_allow_html=True,
            )
