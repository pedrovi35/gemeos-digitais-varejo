"""
Demand model — stochastic generation of sales events.

Compound Poisson with day-of-week and hour-of-day seasonality, plus promotion
and shock multipliers controlled by the scenario layer.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class DemandParams:
    base_rate: float = 8.0          # mean units/day for an average SKU
    dow_factor: tuple = (0.9, 0.92, 0.95, 1.00, 1.18, 1.30, 1.10)
    hour_curve: tuple = (
        0.10, 0.05, 0.04, 0.04, 0.05, 0.10, 0.30, 0.55,
        0.80, 0.95, 1.00, 0.95, 0.85, 0.75, 0.70, 0.78,
        0.92, 1.05, 1.20, 1.10, 0.85, 0.60, 0.35, 0.20,
    )
    promo_lift: float = 1.45
    shock_multiplier: float = 1.0


class DemandModel:
    def __init__(self, params: DemandParams | None = None, *, rng: np.random.Generator | None = None):
        self.p = params or DemandParams()
        self.rng = rng or np.random.default_rng()

    def expected_units(self, *, dow: int, hour: int, velocity: str = "B", promo: bool = False) -> float:
        velocity_mult = {"A": 2.4, "B": 1.0, "C": 0.35}.get(velocity, 1.0)
        rate = (self.p.base_rate / 24.0) * self.p.dow_factor[dow] * self.p.hour_curve[hour]
        rate *= velocity_mult * self.p.shock_multiplier
        if promo:
            rate *= self.p.promo_lift
        return float(rate)

    def sample(self, *, dow: int, hour: int, velocity: str = "B", promo: bool = False) -> int:
        return int(self.rng.poisson(self.expected_units(dow=dow, hour=hour, velocity=velocity, promo=promo)))
