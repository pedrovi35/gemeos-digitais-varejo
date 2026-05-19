"""What-if analytics — counterfactual KPI projections under scenarios."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WhatIfResult:
    baseline_service_level: float
    projected_service_level: float
    baseline_stockout_pct: float
    projected_stockout_pct: float
    projected_lost_revenue: float
    confidence: float


class WhatIfAnalytics:
    """Closed-form projector — fast enough for interactive sliders."""

    def project(
        self, *,
        baseline_service_level: float,
        baseline_stockout_pct: float,
        baseline_daily_revenue: float,
        demand_shock: float = 1.0,
        supply_otd: float = 0.95,
        lead_time_days: int = 3,
        horizon_days: int = 7,
    ) -> WhatIfResult:
        # Service level erodes with demand shock and OTD drop
        sl_penalty = (demand_shock - 1.0) * 0.04 + (0.95 - supply_otd) * 0.30
        projected_sl = max(0.0, min(1.0, baseline_service_level - sl_penalty))

        # Stockout grows roughly proportional to penalty and lead time
        so_growth = sl_penalty * 1.2 + max(0, lead_time_days - 3) * 0.005
        projected_so = max(0.0, min(0.5, baseline_stockout_pct + so_growth))

        lost = baseline_daily_revenue * projected_so * horizon_days

        return WhatIfResult(
            baseline_service_level=baseline_service_level,
            projected_service_level=projected_sl,
            baseline_stockout_pct=baseline_stockout_pct,
            projected_stockout_pct=projected_so,
            projected_lost_revenue=lost,
            confidence=0.82,
        )
