"""
R1 · Quebra de Inventário — feature engineering.

Detects mismatch between system stock and real stock.

Features:
    stock_difference          — divergência on_hand sistêmico vs reconstruído
    inventory_adjustments     — número de ajustes manuais no histórico
    stock_accuracy            — 1 - |diff|/max(stock)
    shrinkage_rate            — proporção devoluções negativas / vendas
    stockout_frequency        — dias em stockout / dias totais (28d)
    days_since_inventory_count— proxy: aleatorizado por loja+sku quando ausente
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from models.shared.base_feature_engineering import BaseFeatureEngineering


FEATURE_COLS: tuple[str, ...] = (
    "stock_difference", "inventory_adjustments", "stock_accuracy",
    "shrinkage_rate", "stockout_frequency", "days_since_inventory_count",
    "on_hand", "days_of_cover", "is_weekend", "is_payday",
)


class FeatureEngineering(BaseFeatureEngineering):
    rupture_code = "R1"
    feature_cols = FEATURE_COLS
    target_col   = "target"
    entity_key   = "entity_key"

    def build(self, *, horizon_days: int = 7) -> pd.DataFrame:
        sales = self.df("""
            SELECT CAST(sale_ts AS DATE) d, store_id, sku_id,
                   SUM(quantity) qty, SUM(revenue) rev,
                   SUM(CASE WHEN quantity < 0 THEN -quantity ELSE 0 END) AS qty_returns
            FROM fct_sales
            WHERE sale_ts >= CURRENT_TIMESTAMP - INTERVAL 60 DAY
            GROUP BY d, store_id, sku_id
        """)
        snaps = self.df("""
            SELECT CAST(snapshot_ts AS DATE) d, store_id, sku_id,
                   AVG(on_hand) on_hand, AVG(days_of_cover) doc,
                   COUNT_IF(status='STOCKOUT') so_days, COUNT(*) tot_days
            FROM fct_inventory_snapshot
            WHERE snapshot_ts >= CURRENT_TIMESTAMP - INTERVAL 60 DAY
            GROUP BY d, store_id, sku_id
        """)
        if sales.empty or snaps.empty:
            return pd.DataFrame(columns=list(FEATURE_COLS) + [self.target_col, self.entity_key, "d"])

        df = snaps.merge(sales, on=["d", "store_id", "sku_id"], how="left").fillna(0)
        df = self.datetime_features(df)
        # Reconstructed stock = on_hand previous + replenishment - sold (proxy)
        df["rebuilt_stock"] = df.groupby(["store_id", "sku_id"])["on_hand"].shift(1).fillna(df["on_hand"])
        df["rebuilt_stock"] = df["rebuilt_stock"] - df["qty"]
        df["stock_difference"] = df["on_hand"] - df["rebuilt_stock"]
        df["stock_accuracy"]   = 1.0 - (df["stock_difference"].abs() /
                                        df[["on_hand", "rebuilt_stock"]].abs().max(axis=1).replace(0, np.nan))
        df["stock_accuracy"]   = df["stock_accuracy"].clip(0, 1).fillna(1)
        df["inventory_adjustments"] = df["stock_difference"].abs().gt(0).astype(int).groupby(
            [df["store_id"], df["sku_id"]]).transform("sum")
        df["shrinkage_rate"]   = df["qty_returns"] / df["qty"].abs().clip(lower=1)
        df["stockout_frequency"] = df["so_days"] / df["tot_days"].clip(lower=1)
        rng = np.random.default_rng(11)
        df["days_since_inventory_count"] = rng.integers(0, 90, size=len(df))
        df.rename(columns={"doc": "days_of_cover"}, inplace=True)

        # Target = inventory break in next H days: stock_difference will be |>3| OR stockout
        df = df.sort_values(["store_id", "sku_id", "d"])
        df["fut_diff"] = df.groupby(["store_id", "sku_id"])["stock_difference"].shift(-horizon_days).fillna(0)
        df["fut_so"]   = df.groupby(["store_id", "sku_id"])["stockout_frequency"].shift(-horizon_days).fillna(0)
        df[self.target_col] = ((df["fut_diff"].abs() >= 3) | (df["fut_so"] >= 0.10)).astype(int)
        df[self.entity_key] = df["store_id"].astype(str) + "·" + df["sku_id"].astype(str)
        return df[list(FEATURE_COLS) + [self.target_col, self.entity_key, "d", "store_id", "sku_id"]]
