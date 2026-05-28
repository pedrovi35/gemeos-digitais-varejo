"""
AIService — single façade the UI talks to.

Pipeline:
   query → guardrails → intent routing (LLM + heuristics) →
   specialist agent → AnalysisResponse → memory append

Use this from any page:

    >>> from agents.ai_service import AIService
    >>> svc = AIService()
    >>> resp = svc.analyze("Por que houve ruptura no leite na ST-001?",
    ...                    scope={"store_id": "ST-001"}, session_id="ui:42")
"""
from __future__ import annotations

import re
from typing import Any

from agents.forecasting_agent import ForecastingAgent
from agents.groq_client import GroqClient
from agents.memory import Turn, get_memory
from agents.operational_agent import OperationalAgent
from agents.operational_ml_agent import OperationalMLAgent
from agents.prompts import SystemPrompts
from agents.rupture_agent import RuptureAgent
from agents.schemas import AnalysisResponse, Confidence, Intent
from agents.simulation_agent import SimulationAgent
from agents.supplier_agent import SupplierAgent
from config.logging import logger
from config.settings import settings


_HEURISTICS: list[tuple[re.Pattern, Intent]] = [
    # Specific domain keywords first — more precise signals take priority
    (re.compile(r"\b(?:rupt|stockout|sem estoque|faltando?)\b", re.I), Intent.RUPTURE_INVESTIGATION),
    (re.compile(r"\b(?:forecast|previs[aã]o|mape|drift|vi[eé]s)\b", re.I), Intent.FORECAST_INSIGHT),
    (re.compile(r"\b(?:e se|what[- ]?if|cen[aá]rio|simul\w*)\b", re.I), Intent.SIMULATION_WHATIF),
    (re.compile(r"\b(?:fornecedor|otd|lead[- ]?time|supplier)\b", re.I), Intent.SUPPLIER_ANALYSIS),
    (re.compile(r"\b(?:shap|modelo|predi[cç][aã]o|risco r[1-5]|ruptura r[1-5]|ml)\b", re.I),
     Intent.ML_INTERPRETATION),
    # ROOT_CAUSE is generic ("por que", "porque") — only fires if no domain matched above
    (re.compile(r"\b(?:causa[- ]?raiz|root[- ]?cause)\b", re.I), Intent.ROOT_CAUSE),
    (re.compile(r"\b(?:por que|porque)\b", re.I), Intent.ROOT_CAUSE),
]


class AIService:
    """Top-level orchestration: route + execute + remember."""

    def __init__(self) -> None:
        self.llm = GroqClient()
        self.memory = get_memory()
        self._agents = {
            Intent.RUPTURE_INVESTIGATION: RuptureAgent(self.llm),
            Intent.ROOT_CAUSE:            RuptureAgent(self.llm),
            Intent.FORECAST_INSIGHT:      ForecastingAgent(self.llm),
            Intent.SIMULATION_WHATIF:     SimulationAgent(self.llm),
            Intent.SUPPLIER_ANALYSIS:     SupplierAgent(self.llm),
            Intent.GENERAL_OPS:           OperationalAgent(self.llm),
            Intent.ML_INTERPRETATION:     OperationalMLAgent(self.llm),
        }

    # ── Intent routing ──────────────────────────────────────────────
    def route(self, query: str) -> Intent:
        # 1. Cheap heuristics
        for pat, intent in _HEURISTICS:
            if pat.search(query):
                return intent
        # 2. LLM classifier fallback
        label = self.llm.classify(
            system=SystemPrompts.INTENT_ROUTER,
            query=query,
            allowed=[i.value for i in Intent if i is not Intent.UNSAFE],
            fallback=Intent.GENERAL_OPS.value,
        )
        try:
            return Intent(label)
        except ValueError:
            return Intent.GENERAL_OPS

    # ── Main entrypoint ─────────────────────────────────────────────
    def analyze(
        self, query: str, *,
        scope: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> AnalysisResponse:
        scope = scope or {}
        intent = self.route(query)
        logger.info(f"AIService · route → {intent.value}")
        agent = self._agents[intent]

        history = self.memory.to_messages(session_id) if session_id else []
        response = agent.analyze(query, scope=scope, history=history)

        # Memory write
        if session_id:
            self.memory.append(session_id, Turn(role="user", content=query, intent=intent.value))
            self.memory.append(session_id,
                               Turn(role="assistant", content=response.summary,
                                    intent=intent.value, trace_id=response.trace_id))
        return response

    # ── Specialized convenience entrypoints ─────────────────────────
    def explain_rupture(self, sku_id: str, store_id: str) -> AnalysisResponse:
        return self._agents[Intent.RUPTURE_INVESTIGATION].analyze(
            f"Explique a causa-raiz da ruptura do SKU {sku_id} na loja {store_id}.",
            scope={"store_id": store_id, "sku_id": sku_id},
        )

    def interpret_simulation(self, scenario_payload: dict) -> AnalysisResponse:
        query = (
            f"Interprete o cenário {scenario_payload.get('scenario_name','?')} e gere "
            f"um briefing executivo da projeção."
        )
        return self._agents[Intent.SIMULATION_WHATIF].analyze(
            query, scope=scenario_payload,
        )

    def interpret_ml_risk(self, *, store_id: str | None = None,
                          rupture_code: str | None = None,
                          entity_key: str | None = None) -> AnalysisResponse:
        query = (
            "Interprete operacionalmente os scores preditivos das 5 rupturas críticas "
            "e os principais drivers SHAP. Produza briefing executivo."
        )
        return self._agents[Intent.ML_INTERPRETATION].analyze(
            query,
            scope={"store_id": store_id, "rupture_code": rupture_code, "entity_key": entity_key},
        )

    def healthcheck(self) -> dict:
        return {
            "online": self.llm.online,
            "model": getattr(settings.groq, "model", None),
            "agents": list(set(a.agent_name for a in self._agents.values())),
        }
