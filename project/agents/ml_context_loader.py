"""
ML operational context for Groq interpretation.

Models predict → this loader assembles dossier → Groq explains executively.
"""
from __future__ import annotations

from typing import Any

from models.shared.registry import MODEL_CATALOG, RuptureCode
from services.risk_service import get_risk_service


def load_ml_rupture_context(
    *,
    rupture_code: str | None = None,
    store_id: str | None = None,
    entity_key: str | None = None,
) -> dict[str, Any]:
    risk = get_risk_service()
    codes = [RuptureCode(rupture_code)] if rupture_code else list(RuptureCode)
    rupture_scores: list[dict] = []
    explanations: list[dict] = []

    for code in codes:
        spec = MODEL_CATALOG[code]
        df = risk.score_rupture(code)
        if store_id and "store_id" in df.columns:
            df = df[df["store_id"] == store_id]
        if df.empty:
            continue
        col = spec.output
        top = df.nlargest(5, col)
        rupture_scores.append({
            "rupture": code.value,
            "name": spec.name,
            "avg_risk": float(df[col].mean()),
            "critical": int((df["risk_level"] == "CRITICAL").sum()) if "risk_level" in df.columns else 0,
            "top_entities": top[["entity_key", col, "risk_level"]].to_dict("records")
                              if "entity_key" in top.columns else [],
        })
        if entity_key and "entity_key" in df.columns:
            row = df[df["entity_key"] == entity_key]
            if not row.empty:
                entity = {c: row.iloc[0][c] for c in ["store_id", "sku_id", "supplier_id"] if c in row.columns}
                expl = risk.explain(code, entity)
                explanations.append({
                    "rupture": code.value,
                    "entity_key": entity_key,
                    "score": expl.score,
                    "level": expl.level.value,
                    "drivers": [
                        {"feature": d.feature, "impact_pct": round(d.impact_pct, 1)}
                        for d in expl.top_drivers
                    ],
                })

    tower = risk.tower_summary(store_id=store_id)
    kpis = risk.operational_kpis(store_id)
    return {
        "scope": {"store_id": store_id or "ALL", "entity_key": entity_key},
        "network_risk_index": tower["network_risk_index"],
        "operational_kpis": kpis,
        "rupture_models": rupture_scores,
        "shap_explanations": explanations,
        "instruction": (
            "Os scores acima foram gerados por modelos XGBoost+LightGBM (ensemble). "
            "NÃO recalcule probabilidades — interprete operacionalmente os drivers SHAP."
        ),
    }
