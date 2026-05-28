"""
R5 · Fornecedores com Restrição de Faturamento — feature engineering.

Detects commercial/financial blocks impacting supply continuity.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from models.shared.base_feature_engineering import BaseFeatureEngineering


FEATURE_COLS: tuple[str, ...] = (
    "supplier_restriction_flag", "blocked_orders", "invoice_rejection_rate",
    "supplier_financial_score", "payment_delay", "credit_limit_usage",
    "otd_rate", "skus_at_risk", "avg_days_of_cover",
)


class FeatureEngineering(BaseFeatureEngineering):
    rupture_code = "R5"
    feature_cols = FEATURE_COLS
    target_col   = "target"
    entity_key   = "entity_key"

    def build(self, *, horizon_days: int = 7,
              cutoff_ts: pd.Timestamp | None = None) -> pd.DataFrame:
        self._cutoff_ts = cutoff_ts
        sup = self.df("""
            SELECT s.supplier_id, s.name, s.tier, s.lead_time_days, s.otd_rate
            FROM dim_supplier s
        """)
        # Expand to (supplier × day) grain so the model has enough rows to train.
        # Without the time axis we'd have one row per supplier (~7) — insufficient.
        inv = self.df("""
            SELECT k.supplier_id, CAST(i.snapshot_ts AS DATE) d,
                   COUNT_IF(i.status IN ('STOCKOUT','CRITICAL')) skus_at_risk,
                   COUNT(*) total_skus,
                   AVG(i.days_of_cover) avg_days_of_cover
            FROM fct_inventory_snapshot i
            INNER JOIN dim_sku k USING (sku_id)
            WHERE i.snapshot_ts >= CURRENT_TIMESTAMP - INTERVAL 60 DAY
            GROUP BY k.supplier_id, d
        """)
        orders = self.df("""
            SELECT supplier_id, CAST(placed_ts AS DATE) d,
                   COUNT(*) total_orders,
                   COUNT_IF(status IN ('REJECTED','BLOCKED','CANCELLED')) blocked_orders,
                   AVG(CASE WHEN status IN ('REJECTED','BLOCKED') THEN 1.0 ELSE 0.0 END) rejection_rate
            FROM fct_replenishment
            WHERE placed_ts >= CURRENT_TIMESTAMP - INTERVAL 60 DAY
            GROUP BY supplier_id, d
        """)
        if sup.empty or inv.empty:
            return pd.DataFrame(columns=list(FEATURE_COLS) + [self.target_col, self.entity_key, "d"])

        df = inv.merge(sup, on="supplier_id", how="left").merge(
            orders, on=["supplier_id", "d"], how="left",
        )
        rng = np.random.default_rng(55)
        tier_penalty = df["tier"].map({"T1": 0.05, "T2": 0.12, "T3": 0.22}).fillna(0.15)
        df["invoice_rejection_rate"] = df["rejection_rate"].fillna(tier_penalty + rng.uniform(0, 0.08, len(df)))
        df["blocked_orders"]         = df["blocked_orders"].fillna(
            (df["invoice_rejection_rate"] * df["total_orders"].fillna(20)).astype(int)
        )
        df["supplier_restriction_flag"] = (
            (df["invoice_rejection_rate"] >= 0.15) | (df["blocked_orders"] >= 3)
        ).astype(int)
        df["supplier_financial_score"] = (
            df["otd_rate"].fillna(0.9) * 0.5 +
            (1 - df["invoice_rejection_rate"].clip(0, 1)) * 0.5
        )
        df["payment_delay"]       = (1 - df["otd_rate"].fillna(0.9)) * rng.integers(0, 21, len(df))
        df["credit_limit_usage"]  = np.clip(
            df["invoice_rejection_rate"] * 1.4 + tier_penalty, 0, 1
        )
        df["skus_at_risk"]        = df["skus_at_risk"].fillna(0)
        df["avg_days_of_cover"]   = df["avg_days_of_cover"].fillna(7)

        df[self.target_col] = (
            (df["supplier_restriction_flag"] == 1) |
            (df["invoice_rejection_rate"] >= 0.20) |
            (df["skus_at_risk"] / df["total_skus"].clip(lower=1) >= 0.15)
        ).astype(int)
        df[self.entity_key] = df["supplier_id"]
        df["d"] = pd.to_datetime(df["d"])
        out = df[list(FEATURE_COLS) + [self.target_col, self.entity_key, "d", "supplier_id"]]
        return self.trim_to_cutoff(out)
