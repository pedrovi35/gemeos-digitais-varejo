"""Forecasting analyst — interpretation of forecast quality and drift."""
from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from agents.context_loader import load_general_context, run_template
from agents.prompts import SystemPrompts
from agents.schemas import Intent


class ForecastingAgent(BaseAgent):
    intent     = Intent.FORECAST_INSIGHT
    agent_name = "forecasting"

    @property
    def system_prompt(self) -> str:
        return SystemPrompts.FORECASTING_AGENT

    def load_context(self, query: str, scope: dict[str, Any]) -> dict:
        store_id = scope.get("store_id")
        base = load_general_context(store_id=store_id)
        # Bring in MAPE trend
        try:
            trend = run_template("kpi_trend_14d", [store_id, store_id])
            base["mape_trend"] = [
                {"date": str(r["snapshot_date"]),
                 "service_level": float(r.get("sl", 0)),
                 "fill_rate":     float(r.get("fr", 0)),
                 "stockout_pct":  float(r.get("so", 0))}
                for _, r in trend.iterrows()
            ]
        except Exception:                                   # pragma: no cover
            base["mape_trend"] = []
        return base
