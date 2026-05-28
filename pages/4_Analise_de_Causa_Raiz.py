"""
AI Root Cause Analysis · Operational Intelligence Console
==========================================================
Front-end for the AI layer. The user does NOT talk to a generic chatbot —
they interact with a routed operational analyst that:

  1. Classifies the question (intent routing).
  2. Loads a quantitative dossier from DuckDB.
  3. Invokes the specialist agent (Rupture / Forecast / Simulation / Supplier / Ops).
  4. Returns a structured AnalysisResponse rendered as an executive report.

Memory persists across turns inside the session.
"""
from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Análise de Causa-Raiz (IA) · Gêmeo Digital", layout="wide")

from agents.ai_service import AIService
from agents.memory import get_memory
from agents.schemas import Intent
from components import (
    exec_header, inject_theme, render_analysis, render_global_filters,
    section_banner,
)
from config.settings import settings
from utils.session import SessionState


from core.runtime import after_page_config
after_page_config()
flt = render_global_filters()

ai = AIService()
SESSION_ID = "ui:rca"


# ── Hero ───────────────────────────────────────────────────────────
hc = ai.healthcheck()
exec_header(
    eyebrow="IA · INTELIGÊNCIA OPERACIONAL",
    title="Root Cause Analysis Console",
    subtitle="Analista operacional roteado · investigação · evidência · recomendação.",
    chips=flt.chips() + [("LLM", settings.groq.model),
                         ("AGENTES", str(len(set(hc.get('agents', [])))))],
    status=("info" if hc["online"] else "warning",
            "LLM ONLINE" if hc["online"] else "LLM OFFLINE · sem GROQ_API_KEY"),
)


# ── Sidebar controls ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("### CONSOLE AI")
    intent_force = st.selectbox(
        "Forçar agente",
        options=["AUTO"] + [i.value for i in Intent if i not in {Intent.UNSAFE}],
        format_func=lambda x: "Auto-roteamento" if x == "AUTO" else x.replace("_", " ").title(),
    )
    if st.button("🗑 Limpar memória da sessão", width='stretch'):
        get_memory().reset(SESSION_ID)
        SessionState.set("rca_history", [])
        st.rerun()


# ── Anchor questions (operational, not chitchat) ───────────────────
section_banner("PERGUNTAS-ÂNCORA · INTELIGÊNCIA OPERACIONAL",
               hint="ground-truth: warehouse 24h")

anchors = [
    ("Por que houve ruptura nos SKUs de maior velocidade hoje?",            Intent.RUPTURE_INVESTIGATION),
    ("Qual a causa-raiz da degradação de service level nas últimas 48h?",   Intent.ROOT_CAUSE),
    ("Quais SKUs possuem maior risco operacional na próxima janela de 72h?", Intent.RUPTURE_INVESTIGATION),
    ("E se o lead time do fornecedor T1 subir +2 dias por uma semana?",     Intent.SIMULATION_WHATIF),
    ("Quais fornecedores violaram o SLA de OTD recentemente?",              Intent.SUPPLIER_ANALYSIS),
    ("Há viés sistemático no forecast nas categorias de maior volume?",     Intent.FORECAST_INSIGHT),
]
cols = st.columns(3)
trigger_query: str | None = None
for i, (q, _) in enumerate(anchors):
    if cols[i % 3].button(q, key=f"anchor_{i}", width='stretch'):
        trigger_query = q


# ── Direct input ───────────────────────────────────────────────────
section_banner("CONSULTA OPERACIONAL")
user_query = st.chat_input("Pergunte como um analista de supply chain (pt-BR)…")
if user_query:
    trigger_query = user_query


# ── History (rendered as structured analyses) ──────────────────────
history = SessionState.get("rca_history", [])

if trigger_query:
    scope: dict = {"store_id": flt.store_id, "category": flt.category}
    if intent_force != "AUTO":
        # Bypass routing: call the corresponding agent directly
        target = Intent(intent_force)
        agent  = ai._agents[target]
        with st.spinner(f"Executando {agent.agent_name} agent…"):
            response = agent.analyze(trigger_query, scope=scope)
    else:
        with st.spinner("Roteando · carregando contexto · consultando LLM…"):
            response = ai.analyze(trigger_query, scope=scope, session_id=SESSION_ID)
    history.append({"query": trigger_query, "response": response})
    SessionState.set("rca_history", history)


# ── Render in reverse chronological order ─────────────────────────
for entry in reversed(history):
    section_banner(f"{entry['query'][:120]}",
                   hint=f"agent={entry['response'].agent} · "
                        f"intent={entry['response'].intent.value}")
    render_analysis(entry["response"])


# ── Empty state ────────────────────────────────────────────────────
if not history and not trigger_query:
    st.markdown(
        "<div class='panel'><div class='panel__title'>👋 CONSOLE DE INVESTIGAÇÃO</div>"
        "<div style='color:var(--text-muted); font-size:13px; margin-top:8px;'>"
        "Selecione uma <strong>pergunta-âncora</strong> acima ou escreva sua própria "
        "consulta. O sistema vai (1) classificar a intenção, (2) consultar o "
        "warehouse para construir um dossiê quantitativo, (3) acionar o agente "
        "especialista correto e (4) retornar uma análise executiva estruturada."
        "</div></div>", unsafe_allow_html=True,
    )
