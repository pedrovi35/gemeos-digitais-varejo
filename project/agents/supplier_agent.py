"""Supplier analyst — OTD, lead-time and concentration-risk insights."""
from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from agents.context_loader import load_general_context, run_template
from agents.prompts import SystemPrompts
from agents.schemas import Intent


class SupplierAgent(BaseAgent):
    intent     = Intent.SUPPLIER_ANALYSIS
    agent_name = "supplier"

    @property
    def system_prompt(self) -> str:
        # Reuse operational prompt — it already mandates the executive structure
        return SystemPrompts.OPERATIONAL_AGENT

    def load_context(self, query: str, scope: dict[str, Any]) -> dict:
        ctx = load_general_context(store_id=scope.get("store_id"))
        try:
            ctx["suppliers_below_sla"] = run_template("supplier_otd_recent").to_dict(orient="records")
        except Exception:                                   # pragma: no cover
            ctx["suppliers_below_sla"] = []
        return ctx
