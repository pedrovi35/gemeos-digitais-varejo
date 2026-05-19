"""Replenishment service — reorder logic, EOQ, supplier OTD."""
from __future__ import annotations

import math
import uuid

import pandas as pd

from config.constants import OrderStatus
from config.settings import settings
from services.base import BaseService
from utils.time_utils import now_tz


class ReplenishmentService(BaseService):

    def open_orders(self) -> pd.DataFrame:
        return self.df("""
            SELECT r.order_id, r.placed_ts, r.expected_ts, r.status,
                   r.quantity, r.store_id, r.sku_id, k.description,
                   s.name AS supplier
            FROM fct_replenishment r
            INNER JOIN dim_sku      k USING (sku_id)
            INNER JOIN dim_supplier s ON s.supplier_id = r.supplier_id
            WHERE r.status IN ('PLACED','IN_TRANSIT','BACKORDERED')
            ORDER BY r.expected_ts NULLS LAST;
        """)

    def supplier_otd(self) -> pd.DataFrame:
        return self.df("""
            SELECT s.supplier_id, s.name, s.tier,
                   COUNT(*)                                                                AS orders,
                   AVG(CASE WHEN r.delivered_ts <= r.expected_ts THEN 1.0 ELSE 0.0 END)    AS otd_rate,
                   AVG(EXTRACT(EPOCH FROM (r.delivered_ts - r.placed_ts))/86400.0)         AS avg_lead_days
            FROM fct_replenishment r
            INNER JOIN dim_supplier s ON s.supplier_id = r.supplier_id
            WHERE r.delivered_ts IS NOT NULL
            GROUP BY s.supplier_id, s.name, s.tier;
        """)

    def reorder_point(self, daily_demand: float, lead_time_days: int,
                      demand_std: float | None = None) -> int:
        std = demand_std if demand_std is not None else max(1.0, daily_demand * 0.25)
        ss = settings.twin.safety_stock_multiplier * std * math.sqrt(lead_time_days)
        return int(math.ceil(daily_demand * lead_time_days + ss))

    def eoq(self, annual_demand: float, order_cost: float, holding_cost: float) -> int:
        if holding_cost <= 0:
            return 0
        return int(math.ceil(math.sqrt(2 * annual_demand * order_cost / holding_cost)))

    def place_order(self, store_id: str, sku_id: str, supplier_id: str, quantity: int) -> str:
        order_id = f"PO-{uuid.uuid4().hex[:10].upper()}"
        placed = now_tz()
        expected = placed.replace(microsecond=0) + pd.Timedelta(days=settings.twin.reorder_lead_time_days)
        self.execute(
            "INSERT INTO fct_replenishment VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?);",
            [order_id, placed, expected, store_id, sku_id, supplier_id, quantity, OrderStatus.PLACED.value],
        )
        return order_id
