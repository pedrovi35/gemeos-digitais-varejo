"""
ML Operations Center — training, metrics, artifacts, batch scoring.
"""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="ML Operations Center", page_icon="assets/favicon.svg", layout="wide")

from components import exec_header, kpi_row, section_banner
from config.settings import settings
from core.runtime import after_page_config, sidebar_runtime_controls
from models.shared.pipeline import RiskPipeline
from models.shared.registry import MODEL_CATALOG, RuptureCode
from services.risk_service import get_risk_service

after_page_config(show_health=False)
sidebar_runtime_controls()
risk = get_risk_service()

exec_header(
    eyebrow="ML OPS",
    title="ML Operations Center",
    subtitle="Treinamento · validação temporal · SHAP · batch predictions · gold layer",
    chips=[("ARTIFACTS", str(settings.root / "models" / "artifacts"))],
    status=("info", "PIPELINE PRONTO"),
)

c1, c2, c3 = st.columns(3)
with c1:
    train_all = st.button("▶ Treinar R1–R5 (pipeline completo)", type="primary", width='stretch')
with c2:
    score_all = st.button("⟳ Batch score (sem retreinar)", width='stretch')
with c3:
    force_seed = st.button("↺ Re-seed warehouse", width='stretch')

if force_seed:
    seed_warehouse(force=True)
    st.success("Warehouse re-seeded.")

if train_all:
    with st.spinner("Pipeline: Feature Eng → Train → SHAP → Gold…"):
        results = risk.train_all()
        for r in results:
            st.success(f"{r.code}: AUC={r.metrics.roc_auc:.3f} F1={r.metrics.f1:.3f} · {r.n_rows:,} rows · {r.elapsed_s:.1f}s")

if score_all:
    with st.spinner("Scoring batch…"):
        out = RiskPipeline().score_all()
        for code, df in out.items():
            st.caption(f"{code}: {len(df):,} entidades scored")

section_banner("MÉTRICAS DE CLASSIFICAÇÃO · POR RUPTURA")
rows = []
for code in RuptureCode:
    meta = risk.model_metrics(code)
    if meta:
        rows.append({"ruptura": code.value, **{k: meta.get(k) for k in
            ("roc_auc", "precision", "recall", "f1", "n_train", "n_valid", "positive_rate")}})
if rows:
    import pandas as pd
    st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)
else:
    st.info("Nenhum artefato treinado. Execute o pipeline acima.")

section_banner("ARTEFATOS · REGISTRY")
art_root = settings.root / "models" / "artifacts"
if art_root.exists():
    for code in RuptureCode:
        p = art_root / code.value
        if p.exists():
            meta_path = p / "meta.json"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                st.markdown(f"**{code.value}** · features: {len(meta.get('feature_cols', []))} · "
                            f"target: `{meta.get('target_col')}`")
                st.caption(str(p))
else:
    st.warning(f"Diretório de artefatos ausente: {art_root}")

section_banner("GOLD LAYER · risk_scores")
gold = Path(settings.lake.gold) / "risk_scores"
if gold.exists():
    for sub in sorted(gold.iterdir()):
        latest = sub / "latest.parquet"
        if latest.exists():
            st.caption(f"{sub.name}: {latest.stat().st_size / 1024:.1f} KB")
else:
    st.caption("Gold layer vazio — treine os modelos primeiro.")
