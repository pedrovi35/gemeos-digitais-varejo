"""Stockout analytics — risk surface and lost-sales estimation."""
from __future__ import annotations

import pandas as pd

from services.base import BaseService


class StockoutAnalytics(BaseService):

    def risk_surface(self) -> pd.DataFrame:
        """Per store × category stockout-risk score (0-100)."""
        return self.df("""
            SELECT
                i.store_id,
                k.category,
                COUNT_IF(i.status IN ('STOCKOUT','CRITICAL'))::DOUBLE
                    / NULLIF(COUNT(*),0) * 100  AS risk_score,
                COUNT(*)                        AS skus
            FROM fct_inventory_snapshot i
            INNER JOIN dim_sku k USING (sku_id)
            WHERE i.snapshot_ts >= CURRENT_TIMESTAMP - INTERVAL 1 HOUR
            GROUP BY i.store_id, k.category
            ORDER BY risk_score DESC;
        """)

    def lost_sales_estimate(self, days: int = 7) -> float:
        """Estimated revenue lost to stockouts (forecast vs. actual delta)."""
        row = self.df("""
            WITH expected AS (
                SELECT sku_id, AVG(quantity * unit_price) AS expected_revenue_per_day
                FROM fct_sales
                WHERE sale_ts >= CURRENT_TIMESTAMP - INTERVAL 30 DAY
                GROUP BY sku_id
            ),
            stockout_days AS (
                SELECT sku_id,
                       COUNT(DISTINCT CAST(snapshot_ts AS DATE)) AS days_out
                FROM fct_inventory_snapshot
                WHERE status = 'STOCKOUT'
                  AND snapshot_ts >= CURRENT_TIMESTAMP - INTERVAL ? DAY
                GROUP BY sku_id
            )
            SELECT COALESCE(SUM(expected_revenue_per_day * days_out), 0) AS lost
            FROM expected e
            INNER JOIN stockout_days s USING (sku_id);
        """, [days])
        return float(row.iloc[0]["lost"]) if not row.empty else 0.0

    def time_to_stockout(self) -> pd.DataFrame:
        """Hours-until-stockout based on days_of_cover."""
        return self.df("""
            SELECT i.store_id, i.sku_id, k.description, k.category,
                   i.days_of_cover,
                   i.days_of_cover * 24.0 AS hours_to_stockout
            FROM fct_inventory_snapshot i
            INNER JOIN dim_sku k USING (sku_id)
            WHERE i.days_of_cover < 3
              AND i.snapshot_ts >= CURRENT_TIMESTAMP - INTERVAL 1 HOUR
            ORDER BY hours_to_stockout
            LIMIT 100;
        """)
