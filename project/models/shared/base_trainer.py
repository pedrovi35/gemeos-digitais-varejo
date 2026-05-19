"""
Base trainer — XGBoost + LightGBM soft-vote ensemble with temporal split,
artifact persistence to `models/artifacts/<rupture>/`.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from config.logging import logger
from config.settings import settings
from models.shared.base_evaluator import BaseEvaluator
from models.shared.schemas import ModelMetrics


ARTIFACTS_ROOT = settings.root / "models" / "artifacts"


@dataclass
class TrainingConfig:
    test_size:      float = 0.20
    random_state:   int = 7
    xgb_params:     dict = None
    lgbm_params:    dict = None
    use_ensemble:   bool = True

    def __post_init__(self) -> None:
        if self.xgb_params is None:
            self.xgb_params = dict(
                n_estimators=400, max_depth=6, learning_rate=0.06,
                subsample=0.85, colsample_bytree=0.85,
                reg_lambda=1.0, eval_metric="auc",
                tree_method="hist", random_state=self.random_state,
            )
        if self.lgbm_params is None:
            self.lgbm_params = dict(
                n_estimators=500, max_depth=-1, num_leaves=63,
                learning_rate=0.05, feature_fraction=0.85,
                bagging_fraction=0.85, random_state=self.random_state,
                verbose=-1,
            )


class BaseTrainer:
    """Universal trainer used by every rupture model."""

    def __init__(self, rupture_code: str,
                 feature_cols: tuple[str, ...],
                 target_col: str,
                 config: TrainingConfig | None = None) -> None:
        self.rupture_code = rupture_code
        self.feature_cols = list(feature_cols)
        self.target_col   = target_col
        self.cfg = config or TrainingConfig()

    # ── Public ──────────────────────────────────────────────────────
    def fit(self, df: pd.DataFrame, *, time_col: str | None = "d") -> ModelMetrics:
        X, y = self._prepare(df)
        X_tr, X_va, y_tr, y_va = self._temporal_split(df, X, y, time_col)
        logger.info(f"[{self.rupture_code}] training · n_train={len(X_tr)} n_valid={len(X_va)} "
                    f"positive_rate={y.mean():.3f}")

        xgb_model  = self._fit_xgb(X_tr, y_tr, X_va, y_va)
        lgbm_model = self._fit_lgbm(X_tr, y_tr, X_va, y_va) if self.cfg.use_ensemble else None

        pred_va = self._ensemble_predict(xgb_model, lgbm_model, X_va)
        metrics = BaseEvaluator.compute(y_va, pred_va,
                                        n_train=len(X_tr), n_valid=len(X_va))

        self._persist(xgb_model, lgbm_model, metrics)
        logger.info(f"[{self.rupture_code}] trained · AUC={metrics.roc_auc:.3f} F1={metrics.f1:.3f}")
        return metrics

    # ── Internals ───────────────────────────────────────────────────
    def _prepare(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
        df = df.dropna(subset=[self.target_col])
        for col in self.feature_cols:
            if col not in df.columns:
                df[col] = 0.0
        X = df[self.feature_cols].fillna(0).astype(np.float32)
        y = df[self.target_col].astype(int).values
        return X, y

    def _temporal_split(self, df: pd.DataFrame, X: pd.DataFrame, y: np.ndarray,
                        time_col: str | None) -> tuple:
        if time_col and time_col in df.columns:
            order = pd.to_datetime(df[time_col]).argsort().values
            cut   = int(len(order) * (1 - self.cfg.test_size))
            tr, va = order[:cut], order[cut:]
            return X.iloc[tr], X.iloc[va], y[tr], y[va]
        # Random fallback
        from sklearn.model_selection import train_test_split
        return train_test_split(X, y, test_size=self.cfg.test_size,
                                random_state=self.cfg.random_state, stratify=y if y.sum() > 5 else None)

    def _fit_xgb(self, X_tr, y_tr, X_va, y_va):
        from xgboost import XGBClassifier
        m = XGBClassifier(**self.cfg.xgb_params)
        m.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], verbose=False)
        return m

    def _fit_lgbm(self, X_tr, y_tr, X_va, y_va):
        from lightgbm import LGBMClassifier, early_stopping, log_evaluation
        m = LGBMClassifier(**self.cfg.lgbm_params)
        m.fit(X_tr, y_tr, eval_set=[(X_va, y_va)],
              callbacks=[early_stopping(30, verbose=False), log_evaluation(0)])
        return m

    @staticmethod
    def _ensemble_predict(xgb_m, lgbm_m, X) -> np.ndarray:
        p1 = xgb_m.predict_proba(X)[:, 1]
        if lgbm_m is None:
            return p1
        p2 = lgbm_m.predict_proba(X)[:, 1]
        return 0.5 * p1 + 0.5 * p2

    def _persist(self, xgb_model, lgbm_model, metrics: ModelMetrics) -> None:
        out = ARTIFACTS_ROOT / self.rupture_code
        out.mkdir(parents=True, exist_ok=True)
        joblib.dump(xgb_model,  out / "xgb.joblib")
        if lgbm_model is not None:
            joblib.dump(lgbm_model, out / "lgbm.joblib")
        meta = {
            "rupture_code": self.rupture_code,
            "feature_cols": self.feature_cols,
            "target_col":   self.target_col,
            "metrics":      metrics.model_dump(mode="json"),
            "config":       {k: v for k, v in asdict(self.cfg).items() if k != "xgb_params"},
        }
        (out / "meta.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
