"""Classification evaluator — ROC-AUC, PR-AUC, F1, precision, recall."""
from __future__ import annotations

import numpy as np

from models.shared.schemas import ModelMetrics


class BaseEvaluator:
    """Stateless evaluator. Uses scikit-learn metrics."""

    @staticmethod
    def compute(y_true, y_prob, *, threshold: float = 0.5,
                n_train: int | None = None,
                n_valid: int | None = None) -> ModelMetrics:
        from sklearn.metrics import (
            roc_auc_score, average_precision_score, f1_score,
            precision_score, recall_score, accuracy_score,
        )
        y_true = np.asarray(y_true).astype(int)
        y_prob = np.asarray(y_prob).astype(float)
        y_pred = (y_prob >= threshold).astype(int)

        def _safe(fn, **kw):
            try:    return float(fn(**kw))
            except Exception: return None

        return ModelMetrics(
            roc_auc=_safe(roc_auc_score,         y_true=y_true, y_score=y_prob),
            pr_auc =_safe(average_precision_score,y_true=y_true, y_score=y_prob),
            f1     =_safe(f1_score,              y_true=y_true, y_pred=y_pred, zero_division=0),
            precision=_safe(precision_score,     y_true=y_true, y_pred=y_pred, zero_division=0),
            recall =_safe(recall_score,          y_true=y_true, y_pred=y_pred, zero_division=0),
            accuracy=_safe(accuracy_score,       y_true=y_true, y_pred=y_pred),
            n_train=n_train, n_valid=n_valid,
            positive_rate=float(y_true.mean()) if len(y_true) else None,
        )
