"""System Console — health, metrics, cache, deploy diagnostics."""
from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Console do Sistema · Gêmeo Digital",
    page_icon="assets/favicon.svg",
    layout="wide",
)

from core.bootstrap import ensure_runtime
from core.health import check_health
from core.monitoring import get_metrics
from core.runtime import after_page_config, sidebar_runtime_controls
from config.settings import settings
from components import exec_header, section_banner
from utils.cache import invalidate_cache

after_page_config(show_health=False)
sidebar_runtime_controls()

exec_header(
    eyebrow="PLANO DE CONTROLE",
    title="System Console",
    subtitle="Health checks · performance · cache · deploy diagnostics",
    chips=[("ENV", settings.twin.env.upper()), ("VERSION", settings.version)],
    status=("info", "RUNTIME"),
)

health = check_health()
metrics = get_metrics()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Health", health.badge())
c2.metric("Boot", f"{(metrics.get('boot_ms') or 0):.0f} ms")
c3.metric("Queries", metrics["query_count"])
c4.metric("Errors", metrics["error_count"])

section_banner("VERIFICAÇÕES DE SAÚDE")
for k, v in health.checks.items():
    st.write(f"{'OK' if v else 'FALHA'} · **{k}** — {health.details.get(k, '—')}")

section_banner("PERFORMANCE · SESSÃO")
st.json({
    "avg_query_ms": round(metrics["avg_query_ms"], 2),
    "p95_query_ms": round(metrics["p95_query_ms"], 2),
    "light_seed": settings.twin.light_seed,
    "duckdb": str(settings.duckdb.path),
})

section_banner("AÇÕES")
if st.button("Invalidar todo o cache", type="primary"):
    invalidate_cache()
    ensure_runtime.clear()
    st.success("Cache limpo.")
    st.rerun()
