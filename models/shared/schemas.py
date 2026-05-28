"""Pydantic schemas for the predictive layer."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from utils.time_utils import now_tz


class RiskLevel(str, Enum):
    LOW      = "LOW"
    MODERATE = "MODERATE"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


def level_from_score(score: float) -> RiskLevel:
    if score >= 0.80: return RiskLevel.CRITICAL
    if score >= 0.60: return RiskLevel.HIGH
    if score >= 0.35: return RiskLevel.MODERATE
    return RiskLevel.LOW


class RiskScore(BaseModel):
    rupture_code: str
    entity_key:   str                            # store_id / sku_id / supplier_id / composite
    score:        float = Field(ge=0.0, le=1.0)
    level:        RiskLevel
    probability:  float = Field(ge=0.0, le=1.0)
    horizon_days: int = 7
    model_version:str | None = None
    generated_at: datetime = Field(default_factory=now_tz)


class FeatureContribution(BaseModel):
    feature: str
    value:   float | str
    shap:    float
    impact_pct: float                            # signed, % of total |shap|


class RiskExplanation(BaseModel):
    rupture_code: str
    entity_key:   str
    score:        float
    level:        RiskLevel
    top_drivers:  list[FeatureContribution]
    counterfactuals: list[str] = []
    narrative:    str | None = None
    confidence:   str = "MEDIUM"
    generated_at: datetime = Field(default_factory=now_tz)


class ModelMetrics(BaseModel):
    roc_auc:    float | None = None
    pr_auc:     float | None = None
    precision:  float | None = None
    recall:     float | None = None
    f1:         float | None = None
    accuracy:   float | None = None
    n_train:    int | None = None
    n_valid:    int | None = None
    positive_rate: float | None = None
    trained_at: datetime = Field(default_factory=now_tz)
