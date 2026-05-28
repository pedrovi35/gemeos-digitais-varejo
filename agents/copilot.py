"""Operations Copilot — orchestrates Groq + operational toolbox."""
from __future__ import annotations

from collections.abc import Iterator

from agents.groq_client import GroqClient
from agents.prompts import SystemPrompts
from agents.tools import AgentToolbox


class OperationsCopilot:
    def __init__(self) -> None:
        self.llm = GroqClient()
        self.toolbox = AgentToolbox()

    def _messages(self, user_query: str, store_id: str | None,
                  history: list[dict] | None) -> list[dict]:
        context = self.toolbox.build_context(store_id)
        messages: list[dict] = [
            {"role": "system", "content": SystemPrompts.OPERATIONAL_AGENT},
            {"role": "system", "content": f"## Contexto operacional ao vivo\n```json\n{context}\n```"},
        ]
        for h in (history or []):
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": user_query})
        return messages

    def ask(self, user_query: str, *, store_id: str | None = None,
            history: list[dict] | None = None) -> str:
        return self.llm.complete(self._messages(user_query, store_id, history))

    def stream(self, user_query: str, *, store_id: str | None = None,
               history: list[dict] | None = None) -> Iterator[str]:
        yield from self.llm.stream(self._messages(user_query, store_id, history))

    def scenario_brief(self, scenario_name: str, projection_json: str) -> str:
        return self.llm.complete([
            {"role": "system", "content": SystemPrompts.SIMULATION_AGENT},
            {"role": "user", "content": f"Cenário: {scenario_name}\nProjeção:\n{projection_json}"},
        ])
