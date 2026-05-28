"""KPI service — operations tower headline metrics."""
from __future__ import annotations

import pandas as pd

from database.queries import QueryRegistry
from services.base import BaseService


class KpiService(BaseService):

    def today(self, store_id: str | None = None) -> dict:
        df = self.df(QueryRegistry.OPS_KPI_TODAY, [store_id, store_id])
        return df.iloc[0].to_dict() if not df.empty else {}

    def trend(self, days: int = 14, store_id: str | None = None) -> pd.DataFrame:
        return self.df(QueryRegistry.OPS_KPI_TREND, [days, store_id, store_id])

    def network_health_score(self) -> float:
        """Composite 0–100 operational health index."""
        row = self.df("""
            SELECT
                AVG(service_level) AS sl,
                AVG(fill_rate)     AS fr,
                AVG(1 - stockout_pct) AS av,
                AVG(1 - forecast_mape) AS fa
            FROM mart_kpi_daily
            WHERE snapshot_date >= CURRENT_DATE - INTERVAL 7 DAY;
        """)
        if row.empty or row.iloc[0].isna().all():
            return 0.0
        r = row.iloc[0]
        score = (0.35 * r["sl"] + 0.30 * r["fr"] + 0.25 * r["av"] + 0.10 * r["fa"]) * 100
        return float(max(0.0, min(100.0, score)))
