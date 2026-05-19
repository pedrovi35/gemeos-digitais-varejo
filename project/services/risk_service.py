"""
Operational Risk Layer — unifies the five rupture models into a single
enterprise API consumed by Streamlit pages and the Groq interpretation layer.

Pipeline:
    Raw Data → Feature Engineering → Models → Gold risk_scores → Operational Risk Layer
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from config.logging import logger
from config.settings import settings
from models.shared.pipeline import RiskPipeline
from models.shared.registry import MODEL_CATALOG, RuptureCode, get_model
from models.shared.schemas import RiskExplanation, RiskLevel, level_from_score
from utils.time_utils import now_tz


class RiskIntelligenceService:
    """Torre de controle preditiva — scores, rankings, explicações e métricas."""

    def __init__(self) -> None:
        self._pipeline = RiskPipeline()

    # ── Scoring ─────────────────────────────────────────────────────
    def score_rupture(self, code: RuptureCode | str, *, use_cache: bool = True) -> pd.DataFrame:
        code = RuptureCode(code) if isinstance(code, str) else code
        spec = MODEL_CATALOG[code]
        try:
            inf = get_model(code)
            return inf.score_batch(use_cache=use_cache)
        except Exception as e:
            logger.warning(f"[{code.value}] score failed: {e}")
            return pd.DataFrame()

    def score_all(self, *, use_cache: bool = True) -> dict[str, pd.DataFrame]:
        out: dict[str, pd.DataFrame] = {}
        for code in RuptureCode:
            df = self.score_rupture(code, use_cache=use_cache)
            if not df.empty:
                spec = MODEL_CATALOG[code]
                col = spec.output
                if col not in df.columns:
                    alt = [c for c in df.columns if c.endswith("_risk")]
                    if alt:
                        df = df.rename(columns={alt[0]: col})
            out[code.value] = df
        return out

    def load_gold(self, code: RuptureCode | str) -> pd.DataFrame | None:
        code = RuptureCode(code) if isinstance(code, str) else code
        path = Path(settings.lake.gold) / "risk_scores" / code.value / "latest.parquet"
        if path.exists():
            return pd.read_parquet(path)
        return None

    # ── Tower aggregates ────────────────────────────────────────────
    def tower_summary(self, store_id: str | None = None) -> dict:
        scores = self.score_all()
        rupture_stats = []
        composite_entities: list[dict] = []

        for code, df in scores.items():
            if df.empty:
                rupture_stats.append({
                    "code": code, "name": MODEL_CATALOG[RuptureCode(code)].name,
                    "avg_risk": 0.0, "critical_count": 0, "high_count": 0, "entities": 0,
                })
                continue
            spec = MODEL_CATALOG[RuptureCode(code)]
            col = spec.output
            if store_id and "store_id" in df.columns:
                df = df[df["store_id"] == store_id]
            risk = df[col] if col in df.columns else df.iloc[:, -3]
            levels = [level_from_score(float(v)).value for v in risk]
            rupture_stats.append({
                "code": code,
                "name": spec.name,
                "avg_risk": float(risk.mean()),
                "critical_count": sum(1 for l in levels if l == RiskLevel.CRITICAL.value),
                "high_count": sum(1 for l in levels if l in (RiskLevel.HIGH.value, RiskLevel.CRITICAL.value)),
                "entities": len(df),
            })
            key_col = "entity_key" if "entity_key" in df.columns else None
            for _, row in df.nlargest(50, col).iterrows():
                composite_entities.append({
                    "entity_key": row.get(key_col, "—") if key_col else str(row.get("supplier_id", row.get("store_id", "—"))),
                    "rupture": code,
                    "risk": float(row[col]),
                    "level": row.get("risk_level", level_from_score(float(row[col])).value),
                })

        composite_entities.sort(key=lambda x: x["risk"], reverse=True)
        return {
            "ruptures": rupture_stats,
            "top_entities": composite_entities[:30],
            "network_risk_index": self._network_risk_index(rupture_stats),
            "generated_at": now_tz().isoformat(),
        }

    @staticmethod
    def _network_risk_index(stats: list[dict]) -> float:
        if not stats:
            return 0.0
        weights = [0.22, 0.20, 0.18, 0.20, 0.20]
        vals = [s["avg_risk"] for s in stats[:5]]
        while len(vals) < 5:
            vals.append(0.0)
        return float(np.clip(np.average(vals, weights=weights[: len(vals)]) * 100, 0, 100))

    def operational_ranking(self, code: RuptureCode | str, k: int = 25,
                            store_id: str | None = None) -> pd.DataFrame:
        df = self.score_rupture(code)
        if df.empty:
            return df
        spec = MODEL_CATALOG[RuptureCode(code)]
        col = spec.output
        if store_id and "store_id" in df.columns:
            df = df[df["store_id"] == store_id]
        return df.nlargest(k, col)

    def composite_matrix(self, store_id: str | None = None) -> pd.DataFrame:
        """Entity × rupture risk matrix for heatmap."""
        scores = self.score_all()
        rows: list[dict] = []
        for code, df in scores.items():
            if df.empty:
                continue
            spec = MODEL_CATALOG[RuptureCode(code)]
            col = spec.output
            if store_id and "store_id" in df.columns:
                df = df[df["store_id"] == store_id]
            sub = df.nlargest(100, col)
            for _, r in sub.iterrows():
                ek = r.get("entity_key", f"{r.get('store_id','')}·{r.get('sku_id','')}")
                rows.append({"entity_key": ek, "rupture": code, "risk": float(r[col])})
        if not rows:
            return pd.DataFrame(columns=["entity_key", "rupture", "risk"])
        pivot = pd.DataFrame(rows).pivot_table(
            index="entity_key", columns="rupture", values="risk", aggfunc="max"
        ).fillna(0)
        pivot["composite"] = pivot.mean(axis=1)
        return pivot.sort_values("composite", ascending=False)

    # ── Explainability ────────────────────────────────────────────────
    def explain(self, code: RuptureCode | str, entity: dict) -> RiskExplanation:
        inf = get_model(RuptureCode(code) if isinstance(code, str) else code)
        return inf.explain(entity)

    def model_metrics(self, code: RuptureCode | str) -> dict | None:
        path = settings.root / "models" / "artifacts" / (
            code.value if isinstance(code, RuptureCode) else str(code)
        ) / "meta.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8")).get("metrics")

    def operational_kpis(self, store_id: str | None = None) -> dict:
        from database.connection import get_connection
        conn = get_connection()
        params = [store_id, store_id] if store_id else [None, None]
        row = conn.execute("""
            SELECT AVG(service_level) sl, AVG(fill_rate) fr,
                   AVG(stockout_pct) so, AVG(forecast_mape) mape
            FROM mart_kpi_daily
            WHERE snapshot_date >= CURRENT_DATE - INTERVAL 7 DAY
              AND (? IS NULL OR store_id = ?)
        """, params).fetchone()
        sl, fr, so, mape = (row or (0.96, 0.95, 0.02, 0.12))
        return {
            "fill_rate": float(fr or 0),
            "otif": float((sl or 0) + (fr or 0)) / 2,
            "forecast_accuracy": float(1 - (mape or 0.15)),
            "rupture_pct": float(so or 0),
            "service_level": float(sl or 0),
        }

    # ── Training ─────────────────────────────────────────────────────
    def train_all(self):
        return self._pipeline.train_all()

    def train_one(self, code: RuptureCode | str):
        return self._pipeline.train_one(RuptureCode(code) if isinstance(code, str) else code)


@lru_cache(maxsize=1)
def get_risk_service() -> RiskIntelligenceService:
    return RiskIntelligenceService()
