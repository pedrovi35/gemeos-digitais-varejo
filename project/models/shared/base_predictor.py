"""
Base predictor — loads ensemble artifacts and scores feature frames.

If artifacts are missing, falls back to a transparent heuristic score
computed from the engineered features (z-score average), so the platform
remains usable before the first training run.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from config.logging import logger
from config.settings import settings


ARTIFACTS_ROOT = settings.root / "models" / "artifacts"


class BasePredictor:

    def __init__(self, rupture_code: str,
                 feature_cols: tuple[str, ...]) -> None:
        self.rupture_code = rupture_code
        self.feature_cols = list(feature_cols)
        self._xgb = None
        self._lgbm = None
        self._meta: dict = {}
        self._load()

    # ── Loading ─────────────────────────────────────────────────────
    def _load(self) -> None:
        out = ARTIFACTS_ROOT / self.rupture_code
        if not out.exists():
            logger.info(f"[{self.rupture_code}] no artifacts — running in heuristic mode")
            return
        try:
            import joblib
            if (out / "xgb.joblib").exists():
                self._xgb = joblib.load(out / "xgb.joblib")
            if (out / "lgbm.joblib").exists():
                self._lgbm = joblib.load(out / "lgbm.joblib")
            if (out / "meta.json").exists():
                self._meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
            logger.info(f"[{self.rupture_code}] artifacts loaded")
        except Exception as e:                                # pragma: no cover
            logger.warning(f"[{self.rupture_code}] failed to load artifacts: {e}")

    @property
    def is_trained(self) -> bool:
        return self._xgb is not None

    # ── Scoring ─────────────────────────────────────────────────────
    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        X = self._frame(df)
        if not self.is_trained:
            return self._heuristic_score(X)
        p1 = self._xgb.predict_proba(X)[:, 1]
        if self._lgbm is None:
            return p1
        p2 = self._lgbm.predict_proba(X)[:, 1]
        return 0.5 * p1 + 0.5 * p2

    def _frame(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in self.feature_cols:
            if col not in df.columns:
                df[col] = 0.0
        return df[self.feature_cols].fillna(0).astype(np.float32)

    # ── Fallback ────────────────────────────────────────────────────
    def _heuristic_score(self, X: pd.DataFrame) -> np.ndarray:
        """Squash standardized feature mean through a logistic."""
        if X.empty:
            return np.array([])
        z = (X - X.mean()) / X.std(ddof=0).replace(0, np.nan).fillna(1)
        sig = 1 / (1 + np.exp(-z.fillna(0).mean(axis=1).values))
        return sig.astype(np.float32)
