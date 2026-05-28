"""Forecast service — short-horizon demand estimation."""
from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

from services.base import BaseService
from utils.time_utils import now_tz


class ForecastService(BaseService):

    def horizon(self, days: int = 14, store_id: str | None = None) -> pd.DataFrame:
        return self.df("""
            SELECT target_date, store_id, sku_id, demand_p50, demand_p90
            FROM fct_forecast
            WHERE target_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL ? DAY
              AND (? IS NULL OR store_id = ?);
        """, [days, store_id, store_id])

    def baseline_from_sales(self, store_id: str, sku_id: str, horizon_days: int = 14) -> pd.DataFrame:
        """Generate a lightweight forecast from historical mean + day-of-week seasonality."""
        hist = self.df("""
            SELECT CAST(sale_ts AS DATE) AS d, SUM(quantity) AS q
            FROM fct_sales
            WHERE store_id = ? AND sku_id = ?
              AND sale_ts >= CURRENT_TIMESTAMP - INTERVAL 28 DAY
            GROUP BY d ORDER BY d;
        """, [store_id, sku_id])
        if hist.empty:
            mu = 1.0
            sigma = 1.0
        else:
            mu = float(hist["q"].mean())
            sigma = float(max(1.0, hist["q"].std(ddof=0) or 1.0))
        out = []
        for i in range(1, horizon_days + 1):
            target = now_tz().date() + timedelta(days=i)
            dow_factor = 1.18 if target.weekday() in (4, 5) else 0.95
            p50 = mu * dow_factor
            p90 = p50 + 1.2816 * sigma
            out.append((target, store_id, sku_id, p50, p90))
        return pd.DataFrame(out, columns=["target_date", "store_id", "sku_id", "demand_p50", "demand_p90"])

    def mape(self, actual: np.ndarray, predicted: np.ndarray) -> float:
        actual = np.asarray(actual, dtype=float)
        predicted = np.asarray(predicted, dtype=float)
        mask = actual > 0
        if not mask.any():
            return float("nan")
        return float(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])))
