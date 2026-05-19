"""Sales service — revenue, velocity, basket dynamics."""
from __future__ import annotations

import pandas as pd

from services.base import BaseService


class SalesService(BaseService):

    def revenue_by_day(self, days: int = 14, store_id: str | None = None) -> pd.DataFrame:
        return self.df("""
            SELECT
                CAST(sale_ts AS DATE) AS d,
                SUM(revenue)          AS revenue,
                SUM(quantity)         AS units
            FROM fct_sales
            WHERE sale_ts >= CURRENT_TIMESTAMP - INTERVAL ? DAY
              AND (? IS NULL OR store_id = ?)
            GROUP BY d
            ORDER BY d;
        """, [days, store_id, store_id])

    def revenue_by_category(self, days: int = 7) -> pd.DataFrame:
        return self.df("""
            SELECT k.category,
                   SUM(s.revenue) AS revenue,
                   SUM(s.quantity) AS units
            FROM fct_sales s
            INNER JOIN dim_sku k USING (sku_id)
            WHERE s.sale_ts >= CURRENT_TIMESTAMP - INTERVAL ? DAY
            GROUP BY k.category
            ORDER BY revenue DESC;
        """, [days])

    def top_sku(self, n: int = 20, days: int = 7) -> pd.DataFrame:
        return self.df("""
            SELECT s.sku_id, k.description, k.category, k.velocity_class,
                   SUM(s.revenue)  AS revenue,
                   SUM(s.quantity) AS units
            FROM fct_sales s
            INNER JOIN dim_sku k USING (sku_id)
            WHERE s.sale_ts >= CURRENT_TIMESTAMP - INTERVAL ? DAY
            GROUP BY s.sku_id, k.description, k.category, k.velocity_class
            ORDER BY revenue DESC
            LIMIT ?;
        """, [days, n])

    def hourly_heatmap(self, days: int = 7) -> pd.DataFrame:
        return self.df("""
            SELECT
                EXTRACT(DOW FROM sale_ts)::INTEGER  AS dow,
                EXTRACT(HOUR FROM sale_ts)::INTEGER AS hour,
                SUM(revenue)                         AS revenue
            FROM fct_sales
            WHERE sale_ts >= CURRENT_TIMESTAMP - INTERVAL ? DAY
            GROUP BY dow, hour
            ORDER BY dow, hour;
        """, [days])
