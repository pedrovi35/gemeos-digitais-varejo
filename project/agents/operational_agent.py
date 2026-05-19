"""Operational analyst — general-purpose operations question answering."""
from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from agents.context_loader import load_general_context
from agents.prompts import SystemPrompts
from agents.schemas import Intent


class OperationalAgent(BaseAgent):
    intent     = Intent.GENERAL_OPS
    agent_name = "operations"

    @property
    def system_prompt(self) -> str:
        return SystemPrompts.OPERATIONAL_AGENT

    def load_context(self, query: str, scope: dict[str, Any]) -> dict:
        return load_general_context(store_id=scope.get("store_id"))
