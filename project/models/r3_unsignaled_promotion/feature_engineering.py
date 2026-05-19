"""
R3 · Produto Ofertado Sem Sinalização — feature engineering.

Detects uplift without proper supply-chain signaling.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from config.settings import settings
from models.shared.base_feature_engineering import BaseFeatureEngineering


FEATURE_COLS: tuple[str, ...] = (
    "promotion_flag", "promotion_registered", "uplift_variation",
    "price_drop_pct", "campaign_sync_delay", "unexpected_demand_ratio",
    "discount_depth", "sales_velocity_lift",
)


class FeatureEngineering(BaseFeatureEngineering):
    rupture_code = "R3"
    feature_cols = FEATURE_COLS
    target_col   = "target"
    entity_key   = "entity_key"

    def _load_promo_calendar(self) -> pd.DataFrame | None:
        path = settings.lake.bronze / "promotions" / "promotions.parquet"
        if not path.exists():
            alt = settings.root / "data" / "bronze" / "promotions" / "promotions.parquet"
            path = alt if alt.exists() else path
        if not path.exists():
            return None
        promos = pd.read_parquet(path)
        promos["start_date"] = pd.to_datetime(promos["start_date"]).dt.date
        promos["end_date"]   = pd.to_datetime(promos["end_date"]).dt.date
        return promos

    def build(self, *, horizon_days: int = 7) -> pd.DataFrame:
        sales = self.df("""
            SELECT CAST(s.sale_ts AS DATE) d, s.store_id, s.sku_id,
                   SUM(s.quantity) qty, AVG(s.unit_price) avg_price,
                   BOOL_OR(s.promotion_flag) promotion_flag,
                   k.unit_price list_price
            FROM fct_sales s
            INNER JOIN dim_sku k USING (sku_id)
            WHERE s.sale_ts >= CURRENT_TIMESTAMP - INTERVAL 60 DAY
            GROUP BY d, s.store_id, s.sku_id, k.unit_price
        """)
        if sales.empty:
            return pd.DataFrame(columns=list(FEATURE_COLS) + [self.target_col, self.entity_key, "d"])

        sales["d"] = pd.to_datetime(sales["d"]).dt.date
        promos = self._load_promo_calendar()
        if promos is not None and not promos.empty:
            reg_rows = []
            for _, p in promos.iterrows():
                dates = pd.date_range(p["start_date"], p["end_date"], freq="D")
                for d in dates:
                    reg_rows.append({
                        "d": d.date(), "store_id": p["store_id"], "sku_id": p["sku_id"],
                        "promotion_registered": 1,
                        "registered_discount": p.get("discount_pct", 0.15),
                    })
            reg = pd.DataFrame(reg_rows).drop_duplicates(["d", "store_id", "sku_id"])
            sales = sales.merge(reg, on=["d", "store_id", "sku_id"], how="left")
        else:
            sales["promotion_registered"] = sales["promotion_flag"].astype(int)
            sales["registered_discount"]  = 0.15

        sales["promotion_registered"] = sales["promotion_registered"].fillna(0).astype(int)
        sales["price_drop_pct"] = (
            (sales["list_price"] - sales["avg_price"]) / sales["list_price"].clip(lower=0.01)
        ).clip(0, 1)
        sales["discount_depth"] = sales["price_drop_pct"]

        sales = sales.sort_values(["store_id", "sku_id", "d"])
        sales = self.add_rolling_features(sales, ["store_id", "sku_id"], "qty", windows=(7, 14))
        sales["baseline_qty"] = sales["qty_mean_14d"].clip(lower=1)
        sales["uplift_variation"] = (sales["qty"] - sales["baseline_qty"]) / sales["baseline_qty"]
        sales["unexpected_demand_ratio"] = np.where(
            (sales["promotion_flag"]) & (sales["promotion_registered"] == 0),
            sales["uplift_variation"], 0,
        )
        # Sync delay proxy: days since last registered promo
        sales["campaign_sync_delay"] = (
            sales.groupby(["store_id", "sku_id"], group_keys=False)["promotion_registered"]
            .transform(lambda s: (~s.astype(bool)).astype(int).cumsum())
        )
        sales["sales_velocity_lift"] = sales["uplift_variation"].clip(0, 5)

        fut_uplift = sales.groupby(["store_id", "sku_id"])["uplift_variation"].shift(-horizon_days)
        sales[self.target_col] = (
            ((sales["promotion_flag"]) & (sales["promotion_registered"] == 0) & (sales["uplift_variation"] > 0.35)) |
            (fut_uplift > 0.5)
        ).astype(int)
        sales[self.entity_key] = sales["store_id"].astype(str) + "·" + sales["sku_id"].astype(str)
        sales["d"] = pd.to_datetime(sales["d"])
        return sales[list(FEATURE_COLS) + [self.target_col, self.entity_key, "d", "store_id", "sku_id"]]
