"""
Seasonality engine — multiplicative demand modifiers.

Every modifier returns a *multiplier* applied on top of a SKU's base daily rate.
The product of all multipliers gives the effective Poisson lambda for the day.

Effects modeled:
  • day-of-week curve  (Fri/Sat spike, Sun second peak, Mon trough)
  • monthly seasonality (BR retail: Dec spike, Jan trough, Jun/Jul cold cycle)
  • payday effect (5th/15th/20th/30th = +18% for ~3 days)
  • holiday calendar (Brazilian)
  • category × month sensitivity (e.g. bebidas+verão, açougue+inverno-churrasco)
  • weather / heatwave shocks (random hot spells)
  • macro drift (gentle YoY growth)
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from functools import cache

import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# Static curves
# ─────────────────────────────────────────────────────────────────────────────
DOW_MULTIPLIER = np.array([
    0.88,   # Mon
    0.92,   # Tue
    0.95,   # Wed
    1.02,   # Thu
    1.28,   # Fri  ← peak start
    1.42,   # Sat  ← peak
    1.10,   # Sun
])

MONTH_MULTIPLIER = np.array([
    0.85,   # Jan (post-festas, férias caras)
    0.90,   # Feb
    0.95,   # Mar
    1.00,   # Apr
    1.02,   # May (Dia das Mães)
    0.98,   # Jun (festas juninas — algumas categorias sobem)
    0.96,   # Jul (inverno)
    1.00,   # Aug
    1.02,   # Sep
    1.05,   # Oct (Dia das Crianças)
    1.10,   # Nov (Black Friday)
    1.35,   # Dec ← grande pico de Natal
])

# Category × month (12) — relative sensitivity
CATEGORY_SEASONALITY: dict[str, np.ndarray] = {
    "Bebidas":         np.array([1.20, 1.18, 1.05, 0.95, 0.92, 0.90, 0.92, 0.95, 1.02, 1.10, 1.22, 1.45]),
    "Hortifruti":      np.array([1.02, 1.04, 1.06, 1.05, 1.00, 0.96, 0.94, 0.96, 1.00, 1.04, 1.06, 1.10]),
    "Açougue":         np.array([1.05, 0.98, 0.96, 0.98, 1.00, 1.10, 1.18, 1.12, 1.05, 1.02, 1.05, 1.30]),
    "Higiene Pessoal": np.array([1.00, 0.98, 0.98, 1.00, 1.04, 1.00, 0.98, 1.00, 1.00, 1.02, 1.06, 1.12]),
    "Limpeza":         np.array([1.10, 0.98, 0.96, 0.96, 0.98, 0.98, 0.98, 1.00, 1.02, 1.04, 1.08, 1.20]),
    "Mercearia":       np.array([0.95, 0.96, 0.98, 1.00, 1.02, 1.02, 1.04, 1.02, 1.00, 1.02, 1.08, 1.22]),
}


# Brazilian national holidays — feed-in 2024 & 2025 (extend as needed)
BR_HOLIDAYS: set[date] = {
    # 2024
    date(2024, 1, 1),  date(2024, 2, 12), date(2024, 2, 13), date(2024, 3, 29),
    date(2024, 4, 21), date(2024, 5, 1),  date(2024, 5, 30), date(2024, 9, 7),
    date(2024, 10, 12),date(2024, 11, 2), date(2024, 11, 15),date(2024, 11, 20),
    date(2024, 12, 25),
    # 2025
    date(2025, 1, 1),  date(2025, 3, 3),  date(2025, 3, 4),  date(2025, 4, 18),
    date(2025, 4, 21), date(2025, 5, 1),  date(2025, 6, 19), date(2025, 9, 7),
    date(2025, 10, 12),date(2025, 11, 2), date(2025, 11, 15),date(2025, 11, 20),
    date(2025, 12, 25),
    # 2026
    date(2026, 1, 1),  date(2026, 2, 16), date(2026, 2, 17), date(2026, 4, 3),
    date(2026, 4, 21), date(2026, 5, 1),  date(2026, 9, 7),  date(2026, 10, 12),
    date(2026, 11, 2), date(2026, 11, 15),date(2026, 11, 20),date(2026, 12, 25),
}


class SeasonalityEngine:
    """All temporal modifiers — pure, vectorizable, cacheable per-day."""

    def __init__(self, *, seed: int = 17, growth_yoy: float = 0.06) -> None:
        self.rng = np.random.default_rng(seed)
        self.growth_yoy = growth_yoy
        # Pre-roll a year of weather shocks (heatwaves & cold snaps)
        self._weather_cache: dict[date, float] = {}

    # ── Day-of-week ─────────────────────────────────────────
    @staticmethod
    def dow_factor(d: date) -> float:
        return float(DOW_MULTIPLIER[d.weekday()])

    # ── Month ───────────────────────────────────────────────
    @staticmethod
    def month_factor(d: date) -> float:
        return float(MONTH_MULTIPLIER[d.month - 1])

    # ── Category × month ────────────────────────────────────
    @classmethod
    def category_factor(cls, category: str, d: date) -> float:
        curve = CATEGORY_SEASONALITY.get(category)
        if curve is None:
            return 1.0
        return float(curve[d.month - 1])

    # ── Payday effect (5/15/20/30 ± 1 day, +18%) ────────────
    @staticmethod
    def payday_factor(d: date) -> float:
        anchors = (5, 15, 20, 30)
        return 1.18 if d.day in anchors else (1.08 if d.day - 1 in anchors or d.day + 1 in anchors else 1.0)

    # ── Holiday boost (pre-holiday +30%, holiday itself -40%) ─
    @classmethod
    def holiday_factor(cls, d: date) -> float:
        if d in BR_HOLIDAYS:
            return 0.60                                 # loja com fluxo reduzido
        if (d + timedelta(days=1)) in BR_HOLIDAYS:
            return 1.30                                 # véspera — compra antecipada
        if (d + timedelta(days=2)) in BR_HOLIDAYS:
            return 1.18
        return 1.0

    # ── Weather shocks (heatwaves & cold snaps) ─────────────
    def weather_factor(self, d: date, category: str) -> float:
        if d not in self._weather_cache:
            # ~5% chance of a hot shock, ~3% chance of a cold shock per day
            u = self.rng.random()
            if u < 0.05:    self._weather_cache[d] = +1.0     # heat
            elif u < 0.08:  self._weather_cache[d] = -1.0     # cold
            else:           self._weather_cache[d] = 0.0
        shock = self._weather_cache[d]
        if shock == 0.0:
            return 1.0
        # Category sensitivity
        if shock > 0 and category in ("Bebidas", "Hortifruti"):
            return 1.45
        if shock < 0 and category == "Açougue":
            return 1.25                                # carne para churrasco no frio? mais sopa/frios
        return 1.0

    # ── Macro YoY growth ────────────────────────────────────
    def growth_factor(self, d: date, anchor: date) -> float:
        years = (d - anchor).days / 365.25
        return float((1.0 + self.growth_yoy) ** years)

    # ── Combined ────────────────────────────────────────────
    def combined(self, d: date, *, category: str, anchor: date) -> float:
        return (
            self.dow_factor(d)
            * self.month_factor(d)
            * self.category_factor(category, d)
            * self.payday_factor(d)
            * self.holiday_factor(d)
            * self.weather_factor(d, category)
            * self.growth_factor(d, anchor)
        )
