"""
Toolbox — structured operational facts the copilot can cite.

The copilot doesn't yet do automatic tool calls; instead we build a compact
JSON context dossier from these helpers and inject it into the prompt.
"""
from __future__ import annotations

import json

from analytics.stockout_analytics import StockoutAnalytics
from services.alert_service import AlertService
from services.inventory_service import InventoryService
from services.kpi_service import KpiService


class AgentToolbox:
    def __init__(self) -> None:
        self.kpi = KpiService()
        self.inv = InventoryService()
        self.alerts = AlertService()
        self.stockout = StockoutAnalytics()

    def build_context(self, store_id: str | None = None) -> str:
        kpi = self.kpi.today(store_id)
        at_risk = self.inv.at_risk_count(store_id)
        ranking = self.inv.stockout_ranking().head(5).to_dict(orient="records")
        open_alerts = self.alerts.open().head(5).to_dict(orient="records")
        lost = self.stockout.lost_sales_estimate(days=7)

        dossier = {
            "scope": {"store_id": store_id or "ALL"},
            "kpi_today": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in kpi.items()},
            "stockouts_at_risk_skus": at_risk,
            "top_risk_categories": ranking,
            "open_alerts": [
                {k: str(v) for k, v in a.items() if k in ("severity", "title", "store_id", "sku_id")}
                for a in open_alerts
            ],
            "lost_sales_7d_estimate": round(lost, 2),
        }
        return json.dumps(dossier, ensure_ascii=False, indent=2, default=str)
