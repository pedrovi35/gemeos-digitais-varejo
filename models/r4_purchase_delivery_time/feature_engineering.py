"""
R4 · Tempo de Compra e Entrega — feature engineering.

Predicts operational risk from lead-time / replenishment delays.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from models.shared.base_feature_engineering import BaseFeatureEngineering


FEATURE_COLS: tuple[str, ...] = (
    "supplier_delay_rate", "average_lead_time", "lead_time_variance",
    "delivery_accuracy", "replenishment_frequency", "logistics_delay_score",
    "on_order_ratio", "days_of_cover",
)


class FeatureEngineering(BaseFeatureEngineering):
    rupture_code = "R4"
    feature_cols = FEATURE_COLS
    target_col   = "target"
    entity_key   = "entity_key"

    def build(self, *, horizon_days: int = 7,
              cutoff_ts: pd.Timestamp | None = None) -> pd.DataFrame:
        self._cutoff_ts = cutoff_ts
        inv = self.df("""
            SELECT CAST(i.snapshot_ts AS DATE) d, i.store_id, i.sku_id,
                   AVG(i.on_hand) on_hand, AVG(i.on_order) on_order,
                   AVG(i.days_of_cover) days_of_cover,
                   k.supplier_id
            FROM fct_inventory_snapshot i
            INNER JOIN dim_sku k USING (sku_id)
            WHERE i.snapshot_ts >= CURRENT_TIMESTAMP - INTERVAL 60 DAY
            GROUP BY d, i.store_id, i.sku_id, k.supplier_id
        """)
        sup = self.df("""
            SELECT supplier_id, lead_time_days, otd_rate FROM dim_supplier
        """)
        repl = self.df("""
            SELECT store_id, sku_id,
                   AVG(EXTRACT(EPOCH FROM (delivered_ts - placed_ts))/86400.0) actual_lt,
                   AVG(EXTRACT(EPOCH FROM (expected_ts - placed_ts))/86400.0) planned_lt,
                   COUNT(*) n_orders,
                   AVG(CASE WHEN delivered_ts > expected_ts THEN 1.0 ELSE 0.0 END) delay_rate
            FROM fct_replenishment
            WHERE placed_ts >= CURRENT_TIMESTAMP - INTERVAL 90 DAY
            GROUP BY store_id, sku_id
        """)
        if inv.empty:
            return pd.DataFrame(columns=list(FEATURE_COLS) + [self.target_col, self.entity_key, "d"])

        df = inv.merge(sup, on="supplier_id", how="left")
        df = df.merge(repl, on=["store_id", "sku_id"], how="left")
        df["average_lead_time"]     = df["actual_lt"].fillna(df["lead_time_days"]).fillna(5)
        df["lead_time_variance"]    = (df["actual_lt"] - df["planned_lt"]).abs().fillna(
            df["average_lead_time"] * 0.2
        )
        df["supplier_delay_rate"]   = df["delay_rate"].fillna(1 - df["otd_rate"].fillna(0.9))
        df["delivery_accuracy"]     = 1.0 - df["supplier_delay_rate"].clip(0, 1)
        df["replenishment_frequency"] = df["n_orders"].fillna(0) / 90.0
        df["on_order_ratio"]        = df["on_order"] / df["on_hand"].clip(lower=1)
        df["logistics_delay_score"] = (
            df["supplier_delay_rate"] * 0.5 +
            (df["average_lead_time"] / 14.0).clip(0, 1) * 0.3 +
            (1 - df["days_of_cover"].clip(0, 30) / 30) * 0.2
        )

        df = df.sort_values(["store_id", "sku_id", "d"])
        # Pure-future target: minimum days_of_cover within the next H days drops below 2.
        # The previous rule mixed logistics_delay_score and supplier_delay_rate
        # (both features) into the target, producing perfect in-sample AUC but
        # collapsing to ~0.43 out-of-time.
        fut_cover_min = (
            df.groupby(["store_id", "sku_id"])["days_of_cover"]
              .transform(lambda s: s.shift(-1).rolling(horizon_days, min_periods=1).min())
        )
        df[self.target_col] = (fut_cover_min < 2).fillna(0).astype(int)
        df[self.entity_key] = df["store_id"].astype(str) + "·" + df["sku_id"].astype(str)
        df["d"] = pd.to_datetime(df["d"])
        out = df[list(FEATURE_COLS) + [self.target_col, self.entity_key, "d", "store_id", "sku_id"]]
        return self.trim_to_cutoff(out)
