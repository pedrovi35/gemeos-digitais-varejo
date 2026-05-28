"""Supply model — supplier lead times, OTD, and disruption simulation."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class SupplyParams:
    base_lead_days: int = 3
    lead_std: float = 0.6
    otd_rate: float = 0.95
    disruption_active: bool = False
    disruption_lead_penalty_days: float = 4.0


class SupplyModel:
    def __init__(self, params: SupplyParams | None = None, *, rng: np.random.Generator | None = None):
        self.p = params or SupplyParams()
        self.rng = rng or np.random.default_rng()

    def sample_lead_time(self) -> float:
        base = max(0.5, self.rng.normal(self.p.base_lead_days, self.p.lead_std))
        if self.p.disruption_active:
            base += abs(self.rng.normal(self.p.disruption_lead_penalty_days, 1.0))
        return float(base)

    def on_time(self) -> bool:
        return bool(self.rng.random() < self.p.otd_rate)
