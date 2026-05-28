"""Inventory service — live snapshot, stockout detection, days-of-cover math."""
from __future__ import annotations

import pandas as pd

from config.constants import StockStatus
from database.queries import QueryRegistry
from services.base import BaseService


class InventoryService(BaseService):

    def live_snapshot(self, store_id: str | None = None, category: str | None = None) -> pd.DataFrame:
        return self.df(
            QueryRegistry.INVENTORY_LIVE,
            [store_id, store_id, category, category],
        )

    def stockout_ranking(self) -> pd.DataFrame:
        return self.df(QueryRegistry.STOCKOUT_RANKING)

    def at_risk_count(self, store_id: str | None = None) -> int:
        sql = """
            SELECT COUNT(*)
            FROM fct_inventory_snapshot
            WHERE status IN ('CRITICAL','STOCKOUT')
              AND snapshot_ts >= CURRENT_TIMESTAMP - INTERVAL 1 HOUR
              AND (? IS NULL OR store_id = ?);
        """
        return int(self.scalar(sql, [store_id, store_id]) or 0)

    def coverage_distribution(self) -> pd.DataFrame:
        return self.df("""
            SELECT
                CASE
                    WHEN days_of_cover < 1   THEN '< 1d'
                    WHEN days_of_cover < 3   THEN '1-3d'
                    WHEN days_of_cover < 7   THEN '3-7d'
                    WHEN days_of_cover < 14  THEN '7-14d'
                    WHEN days_of_cover < 30  THEN '14-30d'
                    ELSE '30d+'
                END AS bucket,
                COUNT(*) AS n
            FROM fct_inventory_snapshot
            WHERE snapshot_ts >= CURRENT_TIMESTAMP - INTERVAL 24 HOUR
            GROUP BY bucket
            ORDER BY MIN(days_of_cover);
        """)

    def classify(self, on_hand: int, reorder_point: int, safety_stock: int) -> StockStatus:
        if on_hand <= 0:
            return StockStatus.STOCKOUT
        if on_hand <= safety_stock:
            return StockStatus.CRITICAL
        if on_hand <= reorder_point:
            return StockStatus.WARNING
        if on_hand > reorder_point * 4:
            return StockStatus.OVERSTOCKED
        return StockStatus.HEALTHY
