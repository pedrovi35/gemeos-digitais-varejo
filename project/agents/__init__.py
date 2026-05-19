"""
Operational Intelligence Layer.

Public surface:
    AIService             — top-level façade (use this from the UI)
    AnalysisResponse      — structured analyst response (rendered uniformly)
    Intent / Confidence   — enums
    GroqClient            — hardened LLM client
    BaseAgent             — extension point for new specialists
    OperationalAgent, RuptureAgent, ForecastingAgent,
    SimulationAgent, SupplierAgent — concrete specialists

Legacy `OperationsCopilot` is still exported for back-compat with older pages.
"""
from agents.ai_service        import AIService
from agents.base_agent        import BaseAgent
from agents.copilot           import OperationsCopilot
from agents.forecasting_agent import ForecastingAgent
from agents.groq_client       import GroqClient
from agents.memory            import ConversationMemory, Turn, get_memory
from agents.operational_agent import OperationalAgent
from agents.prompts           import SystemPrompts
from agents.rupture_agent     import RuptureAgent
from agents.schemas           import (
    AnalysisResponse, Confidence, Evidence, Intent, Recommendation,
)
from agents.simulation_agent  import SimulationAgent
from agents.supplier_agent    import SupplierAgent
from agents.tools             import AgentToolbox
from agents.tracer            import AITracer

__all__ = [
    # Service façade
    "AIService",
    # Schemas
    "AnalysisResponse", "Confidence", "Evidence", "Intent", "Recommendation",
    # Agents
    "BaseAgent", "OperationalAgent", "RuptureAgent", "ForecastingAgent",
    "SimulationAgent", "SupplierAgent",
    # Infra
    "GroqClient", "ConversationMemory", "Turn", "get_memory",
    "AITracer", "SystemPrompts",
    # Legacy
    "OperationsCopilot", "AgentToolbox",
]
