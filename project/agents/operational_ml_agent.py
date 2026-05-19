"""Operational ML interpreter — Groq explains model outputs, never predicts."""
from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from agents.ml_context_loader import load_ml_rupture_context
from agents.prompts import SystemPrompts
from agents.schemas import Intent


class OperationalMLAgent(BaseAgent):
    intent     = Intent.ML_INTERPRETATION
    agent_name = "operational_ml"

    @property
    def system_prompt(self) -> str:
        return SystemPrompts.ML_INTERPRETER

    def load_context(self, query: str, scope: dict[str, Any]) -> dict:
        return load_ml_rupture_context(
            rupture_code=scope.get("rupture_code"),
            store_id=scope.get("store_id"),
            entity_key=scope.get("entity_key"),
        )
