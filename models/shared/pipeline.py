"""
Risk pipeline — orchestrates feature_eng → train → eval → SHAP → batch-score
for ALL five rupture models. Used by the training CLI and the ML Ops Center.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from config.logging import logger
from config.settings import settings
from models.shared.registry import MODEL_CATALOG, RuptureCode
from models.shared.schemas import ModelMetrics
from utils.time_utils import now_tz


@dataclass
class PipelineResult:
    code: str
    metrics: ModelMetrics
    n_rows: int
    elapsed_s: float


class RiskPipeline:
    """End-to-end orchestrator across rupture models."""

    @staticmethod
    def _inference(code: RuptureCode):
        spec = MODEL_CATALOG[code]
        mod = __import__(f"{spec.package}.inference", fromlist=["Inference"])
        return mod.Inference()

    @staticmethod
    def _trainer(code: RuptureCode):
        spec = MODEL_CATALOG[code]
        mod = __import__(f"{spec.package}.trainer", fromlist=["Trainer"])
        return mod.Trainer()

    def train_one(self, code: RuptureCode) -> PipelineResult:
        import time
        t0 = time.perf_counter()
        infer = self._inference(code)
        df = infer.feature_engineer.build()
        infer._store.write(code.value, df)              # cache features
        trainer = self._trainer(code)
        metrics = trainer.fit(df)
        # Batch-score and persist to gold
        scored = infer.score_batch(use_cache=False)
        gold = Path(settings.lake.gold) / "risk_scores" / code.value
        gold.mkdir(parents=True, exist_ok=True)
        scored.to_parquet(gold / "latest.parquet", index=False, compression="zstd")
        elapsed = time.perf_counter() - t0
        logger.info(f"[{code.value}] pipeline done · {len(df):,} rows · {elapsed:.1f}s")
        return PipelineResult(code=code.value, metrics=metrics, n_rows=len(df), elapsed_s=elapsed)

    def train_all(self) -> list[PipelineResult]:
        results: list[PipelineResult] = []
        for code in (RuptureCode.R1, RuptureCode.R2, RuptureCode.R3,
                     RuptureCode.R4, RuptureCode.R5):
            try:
                results.append(self.train_one(code))
            except Exception as e:                       # pragma: no cover
                logger.exception(f"[{code.value}] pipeline FAILED: {e}")
        return results

    # ── Batch scoring without retraining ────────────────────────────
    def score_all(self) -> dict[str, pd.DataFrame]:
        out: dict[str, pd.DataFrame] = {}
        for code in MODEL_CATALOG:
            try:
                inf = self._inference(code)
                out[code.value] = inf.score_batch()
            except Exception as e:                       # pragma: no cover
                logger.warning(f"[{code.value}] score failed: {e}")
                out[code.value] = pd.DataFrame()
        return out
