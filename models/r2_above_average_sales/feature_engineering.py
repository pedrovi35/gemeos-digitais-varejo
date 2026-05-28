"""
R2 · Venda Acima da Média — feature engineering.

Detects abnormal demand spikes vs rolling baseline.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from models.shared.base_feature_engineering import BaseFeatureEngineering


FEATURE_COLS: tuple[str, ...] = (
    "rolling_mean_7d", "rolling_std", "demand_acceleration",
    "demand_spike_score", "payday_flag", "weekend_flag", "seasonal_index",
    "qty_zscore_14d", "velocity_class_a",
)


class FeatureEngineering(BaseFeatureEngineering):
    rupture_code = "R2"
    feature_cols = FEATURE_COLS
    target_col   = "target"
    entity_key   = "entity_key"

    def build(self, *, horizon_days: int = 7,
              cutoff_ts: pd.Timestamp | None = None) -> pd.DataFrame:
        self._cutoff_ts = cutoff_ts
        df = self.df("""
            SELECT CAST(s.sale_ts AS DATE) d, s.store_id, s.sku_id,
                   SUM(s.quantity) qty, SUM(s.revenue) rev,
                   k.velocity_class, k.category
            FROM fct_sales s
            INNER JOIN dim_sku k USING (sku_id)
            WHERE s.sale_ts >= CURRENT_TIMESTAMP - INTERVAL 60 DAY
            GROUP BY d, s.store_id, s.sku_id, k.velocity_class, k.category
        """)
        if df.empty:
            return pd.DataFrame(columns=list(FEATURE_COLS) + [self.target_col, self.entity_key, "d"])

        df = self.datetime_features(df)
        df["payday_flag"]   = df["is_payday"]
        df["weekend_flag"]  = df["is_weekend"]
        df = self.add_rolling_features(df, ["store_id", "sku_id"], "qty", windows=(7, 14, 28))
        df["rolling_mean_7d"] = df["qty_mean_7d"]
        df["rolling_std"]     = df["qty_std_7d"]
        df = self.zscore(df, "qty", "qty_mean_14d", "qty_std_14d", "qty_zscore_14d")
        df["demand_acceleration"] = (
            df.groupby(["store_id", "sku_id"])["qty"].diff().fillna(0) /
            df["rolling_mean_7d"].clip(lower=1)
        )
        df["demand_spike_score"] = (df["qty"] - df["rolling_mean_7d"]) / df["rolling_std"].replace(0, np.nan)
        df["demand_spike_score"] = df["demand_spike_score"].fillna(0).clip(-6, 6)
        # Seasonal index: qty / category-store monthly mean
        df["month"] = pd.to_datetime(df["d"]).dt.month
        cat_mean = df.groupby(["store_id", "category", "month"])["qty"].transform("mean").clip(lower=1)
        df["seasonal_index"] = df["qty"] / cat_mean
        df["velocity_class_a"] = (df["velocity_class"] == "A").astype(int)

        df = df.sort_values(["store_id", "sku_id", "d"])
        # Target is a strictly-future event: max demand in the next H days exceeds
        # the current rolling baseline by ≥80%. Using only future quantities
        # (no current-period feature) avoids the target-leak that inflated AUC.
        fut_qty_max = (
            df.groupby(["store_id", "sku_id"])["qty"]
              .transform(lambda s: s.shift(-1).rolling(horizon_days, min_periods=1).max())
        )
        df[self.target_col] = (fut_qty_max > df["rolling_mean_7d"] * 1.8).fillna(0).astype(int)
        df[self.entity_key] = df["store_id"].astype(str) + "·" + df["sku_id"].astype(str)
        out = df[list(FEATURE_COLS) + [self.target_col, self.entity_key, "d", "store_id", "sku_id"]]
        return self.trim_to_cutoff(out)
