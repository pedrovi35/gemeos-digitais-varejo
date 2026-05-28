"""
Base inference orchestrator.

End-to-end:
    features ← FeatureEngineering.build()
    scores   ← Predictor.predict_proba(features)
    output   ← per-entity RiskScore[] + DataFrame

The class is generic — each rupture composes its FE + Predictor + Explainer
into an `Inference` subclass.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pandas as pd

from config.logging import logger
from models.shared.feature_store import FeatureStore
from models.shared.schemas import (
    FeatureContribution, RiskExplanation, RiskScore, level_from_score,
)

if TYPE_CHECKING:
    from models.shared.base_feature_engineering import BaseFeatureEngineering
    from models.shared.base_predictor import BasePredictor
    from models.shared.base_shap_explainer import BaseShapExplainer


class BaseInference:
    rupture_code: str = ""
    feature_engineer: "BaseFeatureEngineering"
    predictor:        "BasePredictor"
    explainer:        "BaseShapExplainer"
    output_col:       str = "risk_score"
    entity_cols:      tuple[str, ...] = ("store_id", "sku_id")

    def __init__(self) -> None:
        self._store = FeatureStore()

    # ── Public API ──────────────────────────────────────────────────
    def features(self, *, use_cache: bool = True, horizon_days: int = 7) -> pd.DataFrame:
        if use_cache:
            cached = self._store.read(self.rupture_code)
            if cached is not None and not cached.empty:
                logger.debug(f"[{self.rupture_code}] using cached features ({len(cached):,})")
                return cached
        df = self.feature_engineer.build(horizon_days=horizon_days)
        self._store.write(self.rupture_code, df)
        return df

    def score_batch(self, *, horizon_days: int = 7,
                    use_cache: bool = True) -> pd.DataFrame:
        df = self.features(use_cache=use_cache, horizon_days=horizon_days)
        if df.empty:
            return df
        probs = self.predictor.predict_proba(df)
        out = df.copy()
        out[self.output_col]  = probs
        out["risk_level"]     = [level_from_score(p).value for p in probs]
        out["rupture_code"]   = self.rupture_code
        out["generated_at"]   = datetime.utcnow()
        return out

    def top_k(self, k: int = 25, *, ascending: bool = False) -> pd.DataFrame:
        s = self.score_batch()
        if s.empty:
            return s
        return s.sort_values(self.output_col, ascending=ascending).head(k)

    # ── Explanations ────────────────────────────────────────────────
    def explain(self, entity: dict | pd.Series) -> RiskExplanation:
        df = self.features()
        if isinstance(entity, dict):
            mask = pd.Series([True] * len(df))
            for k, v in entity.items():
                if k in df.columns:
                    mask &= (df[k].astype(str) == str(v))
            row = df[mask]
            if row.empty:
                return self._empty_explanation(entity)
            row = row.iloc[0]
        else:
            row = entity
        prob = float(self.predictor.predict_proba(pd.DataFrame([row]))[0])
        sh = self.explainer.explain_row(row)
        entity_key = "·".join(str(row.get(c, "—")) for c in self.entity_cols)
        return RiskExplanation(
            rupture_code=self.rupture_code, entity_key=entity_key,
            score=prob, level=level_from_score(prob),
            top_drivers=sh.contributions,
            counterfactuals=self._counterfactuals(sh.contributions),
            confidence="HIGH" if self.predictor.is_trained else "MEDIUM",
        )

    @staticmethod
    def _counterfactuals(drivers: list[FeatureContribution]) -> list[str]:
        out: list[str] = []
        for d in drivers[:3]:
            if d.shap > 0:
                out.append(f"Se **{d.feature}** reduzir 30%, o risco cai aprox. "
                           f"{abs(d.impact_pct * 0.30):.1f} p.p.")
        return out

    def _empty_explanation(self, entity: dict) -> RiskExplanation:
        return RiskExplanation(
            rupture_code=self.rupture_code,
            entity_key=str(entity), score=0.0,
            level=level_from_score(0.0), top_drivers=[],
            narrative="Entidade não encontrada na malha de features.",
            confidence="LOW",
        )
