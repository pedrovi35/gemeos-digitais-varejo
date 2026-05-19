"""
Structured analyst response schemas.

Every agent returns an `AnalysisResponse`. The UI renders these in a uniform
executive-report layout: summary → root-cause → evidence → impact →
recommendation → confidence.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from utils.time_utils import now_tz


class Intent(str, Enum):
    RUPTURE_INVESTIGATION = "RUPTURE_INVESTIGATION"
    ROOT_CAUSE            = "ROOT_CAUSE"
    FORECAST_INSIGHT      = "FORECAST_INSIGHT"
    SIMULATION_WHATIF     = "SIMULATION_WHATIF"
    SUPPLIER_ANALYSIS     = "SUPPLIER_ANALYSIS"
    ML_INTERPRETATION     = "ML_INTERPRETATION"
    GENERAL_OPS           = "GENERAL_OPS"
    UNSAFE                = "UNSAFE"


class Confidence(str, Enum):
    LOW    = "LOW"
    MEDIUM = "MEDIUM"
    HIGH   = "HIGH"


class Evidence(BaseModel):
    """One quantitative fact extracted from the warehouse."""
    label:       str
    value:       str
    source:      str = Field(description="table or mart that produced the fact")
    weight:      float = Field(default=1.0, ge=0.0, le=1.0)


class Recommendation(BaseModel):
    title:    str
    detail:   str
    priority: str = Field(default="P2", pattern=r"^P[1-3]$")
    owner:    str = "Operations"
    eta:      str = "24h"


class AnalysisResponse(BaseModel):
    """Unified analyst output rendered identically across every agent."""
    intent:           Intent
    headline:         str        = Field(description="One-line executive summary")
    summary:          str        = Field(description="Executive narrative · 2–5 sentences")
    root_cause:       str | None = None
    evidence:         list[Evidence] = []
    financial_impact: str | None = None
    recommendations:  list[Recommendation] = []
    confidence:       Confidence = Confidence.MEDIUM
    assumptions:      list[str]  = []
    generated_at:     datetime   = Field(default_factory=now_tz)
    agent:            str        = "operational"
    model:            str | None = None
    trace_id:         str | None = None
    extra:            dict[str, Any] = {}
