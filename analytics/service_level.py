"""Service level & fill rate analytics."""
from __future__ import annotations

import pandas as pd

from services.base import BaseService


class ServiceLevelAnalytics(BaseService):

    def by_store(self, days: int = 14) -> pd.DataFrame:
        return self.df("""
            SELECT store_id,
                   AVG(service_level) AS service_level,
                   AVG(fill_rate)     AS fill_rate,
                   AVG(stockout_pct)  AS stockout_pct
            FROM mart_kpi_daily
            WHERE snapshot_date >= CURRENT_DATE - INTERVAL ? DAY
            GROUP BY store_id
            ORDER BY service_level DESC;
        """, [days])

    def trend(self, days: int = 30) -> pd.DataFrame:
        return self.df("""
            SELECT snapshot_date,
                   AVG(service_level) AS service_level,
                   AVG(fill_rate)     AS fill_rate
            FROM mart_kpi_daily
            WHERE snapshot_date >= CURRENT_DATE - INTERVAL ? DAY
            GROUP BY snapshot_date
            ORDER BY snapshot_date;
        """, [days])
