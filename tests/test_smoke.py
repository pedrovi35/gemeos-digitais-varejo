"""Smoke tests — verify the runtime bootstraps without crashing."""
from __future__ import annotations


def test_settings_loads() -> None:
    from config.settings import settings
    assert settings.name
    assert settings.twin.horizon_days > 0


def test_constants_enum() -> None:
    from config.constants import AlertSeverity, StockStatus
    assert StockStatus.STOCKOUT.value == "STOCKOUT"
    assert AlertSeverity.CRITICAL.value == "CRITICAL"


def test_what_if_projection() -> None:
    from analytics.what_if import WhatIfAnalytics
    r = WhatIfAnalytics().project(
        baseline_service_level=0.98, baseline_stockout_pct=0.015,
        baseline_daily_revenue=200_000, demand_shock=1.5, supply_otd=0.80,
        lead_time_days=5, horizon_days=7,
    )
    assert r.projected_service_level < r.baseline_service_level
    assert r.projected_stockout_pct > r.baseline_stockout_pct
