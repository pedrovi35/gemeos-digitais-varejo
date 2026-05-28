"""ABC analysis — Pareto classification of SKUs by revenue contribution."""
from __future__ import annotations

import pandas as pd

from services.base import BaseService


class ABCAnalysis(BaseService):

    def classify(self, days: int = 30) -> pd.DataFrame:
        df = self.df("""
            SELECT s.sku_id, k.description, k.category,
                   SUM(s.revenue)  AS revenue,
                   SUM(s.quantity) AS units
            FROM fct_sales s
            INNER JOIN dim_sku k USING (sku_id)
            WHERE s.sale_ts >= CURRENT_TIMESTAMP - INTERVAL ? DAY
            GROUP BY s.sku_id, k.description, k.category
            ORDER BY revenue DESC;
        """, [days])
        if df.empty:
            return df
        df["cum_revenue"] = df["revenue"].cumsum()
        df["cum_pct"] = df["cum_revenue"] / df["revenue"].sum()
        df["class"] = df["cum_pct"].apply(lambda p: "A" if p <= 0.80 else "B" if p <= 0.95 else "C")
        return df
