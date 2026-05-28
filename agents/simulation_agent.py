"""Scenario analyst — interprets digital-twin simulation outputs."""
from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from agents.context_loader import load_general_context
from agents.prompts import SystemPrompts
from agents.schemas import Intent


class SimulationAgent(BaseAgent):
    intent     = Intent.SIMULATION_WHATIF
    agent_name = "simulation"

    @property
    def system_prompt(self) -> str:
        return SystemPrompts.SIMULATION_AGENT

    def load_context(self, query: str, scope: dict[str, Any]) -> dict:
        ctx = load_general_context(store_id=scope.get("store_id"))
        # Scope is expected to carry projection details from the UI:
        # demand_shock, supplier_otd, lead_time, horizon, scenario_code/name, baselines
        ctx["scenario"] = {k: v for k, v in scope.items()
                           if k in {"scenario_code", "scenario_name", "demand_shock",
                                    "supplier_otd", "lead_time_days", "horizon_days",
                                    "baseline_service_level", "baseline_stockout_pct",
                                    "projected_service_level", "projected_stockout_pct",
                                    "projected_lost_revenue"}}
        return ctx
