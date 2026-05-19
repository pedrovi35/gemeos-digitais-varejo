"""Rupture investigator — root-cause analysis of stockout events."""
from __future__ import annotations

import re
from typing import Any

from agents.base_agent import BaseAgent
from agents.context_loader import load_rupture_context, load_sku_context
from agents.prompts import SystemPrompts
from agents.schemas import Intent


_SKU_RE   = re.compile(r"\bSKU[-_]?(\d{4,6})\b", re.IGNORECASE)
_STORE_RE = re.compile(r"\bST[-_]?(\d{3})\b",   re.IGNORECASE)


class RuptureAgent(BaseAgent):
    intent     = Intent.RUPTURE_INVESTIGATION
    agent_name = "rupture"

    @property
    def system_prompt(self) -> str:
        return SystemPrompts.RUPTURE_AGENT

    def load_context(self, query: str, scope: dict[str, Any]) -> dict:
        # If the query mentions a specific SKU+store, load deep dossier
        sku_match  = _SKU_RE.search(query)
        store_match= _STORE_RE.search(query)
        store_id = scope.get("store_id")
        category = scope.get("category")

        ctx = load_rupture_context(store_id=store_id, category=category)

        if sku_match:
            sku_id = f"SKU-{int(sku_match.group(1)):05d}"
            st_id = f"ST-{int(store_match.group(1)):03d}" if store_match else (store_id or "ST-001")
            ctx["sku_deep_dive"] = load_sku_context(sku_id, st_id)
            ctx["scope"]["focus_sku"] = sku_id
            ctx["scope"]["focus_store"] = st_id
        return ctx
