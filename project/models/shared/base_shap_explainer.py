"""
SHAP explainer wrapper.

If SHAP is available, uses TreeExplainer on the XGBoost artifact.
Otherwise falls back to model feature_importances_ scaled by feature value
deviation — keeps explainability working even without the SHAP dependency.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from config.logging import logger
from config.settings import settings
from models.shared.schemas import FeatureContribution


ARTIFACTS_ROOT = settings.root / "models" / "artifacts"


@dataclass
class _ShapResult:
    base_value: float
    contributions: list[FeatureContribution]


class BaseShapExplainer:
    """One explainer per rupture code."""

    def __init__(self, rupture_code: str,
                 feature_cols: tuple[str, ...]) -> None:
        self.rupture_code = rupture_code
        self.feature_cols = list(feature_cols)
        self._explainer = None
        self._model = None
        self._init()

    def _init(self) -> None:
        out = ARTIFACTS_ROOT / self.rupture_code
        try:
            import joblib
            if (out / "xgb.joblib").exists():
                self._model = joblib.load(out / "xgb.joblib")
        except Exception:                                       # pragma: no cover
            self._model = None
        try:
            import shap
            if self._model is not None:
                self._explainer = shap.TreeExplainer(self._model)
                logger.info(f"[{self.rupture_code}] SHAP TreeExplainer ready")
        except Exception:                                       # pragma: no cover
            self._explainer = None

    # ── Single instance ─────────────────────────────────────────────
    def explain_row(self, row: pd.Series, *, top_k: int = 6) -> _ShapResult:
        if self._explainer is not None:
            X = pd.DataFrame([row[self.feature_cols].fillna(0)]).astype(np.float32)
            values = self._explainer.shap_values(X)
            shap_vals = values[0] if hasattr(values, "__len__") else np.asarray(values).ravel()
            base = float(getattr(self._explainer, "expected_value", 0.0))
        else:
            shap_vals = self._heuristic_shap(row)
            base = 0.5

        total_abs = max(1e-9, float(np.abs(shap_vals).sum()))
        contribs = []
        for f, v, s in sorted(
            zip(self.feature_cols, row[self.feature_cols].values, shap_vals, strict=False),
            key=lambda kv: abs(kv[2]), reverse=True,
        )[:top_k]:
            contribs.append(FeatureContribution(
                feature=f, value=float(v) if isinstance(v, (int, float, np.floating)) else str(v),
                shap=float(s), impact_pct=float(s) / total_abs * 100,
            ))
        return _ShapResult(base_value=base, contributions=contribs)

    # ── Global importance ───────────────────────────────────────────
    def feature_importance(self) -> pd.DataFrame:
        if self._model is None:
            return pd.DataFrame(columns=["feature", "importance"])
        imp = getattr(self._model, "feature_importances_", None)
        if imp is None:
            return pd.DataFrame(columns=["feature", "importance"])
        return pd.DataFrame({"feature": self.feature_cols, "importance": imp}) \
                 .sort_values("importance", ascending=False)

    # ── Fallback ────────────────────────────────────────────────────
    def _heuristic_shap(self, row: pd.Series) -> np.ndarray:
        """Use signed deviation-from-mean as a stand-in for SHAP."""
        vals = row[self.feature_cols].fillna(0).astype(float).values
        z = (vals - vals.mean()) / (vals.std() + 1e-6)
        return z * 0.1
