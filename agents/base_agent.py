"""
Abstract base for analyst agents.

Every concrete agent inherits this scaffolding:
  • intent → matches its specialty
  • load_context(query, scope) → dossier dict
  • system_prompt → role-specific
  • analyze(query, scope) → AnalysisResponse

The base orchestrates: guardrails → tracer → context → LLM → parse → persist.
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any

from agents.context_loader import evidence_from_context
from agents.groq_client import GroqClient
from agents.guardrails import classify_safety, redact_pii, truncate
from agents.schemas import AnalysisResponse, Confidence, Evidence, Intent, Recommendation
from agents.tracer import AITracer
from config.settings import settings


class BaseAgent(ABC):
    """Common pipeline for every specialist analyst."""

    intent: Intent = Intent.GENERAL_OPS
    agent_name: str = "operational"

    def __init__(self, llm: GroqClient | None = None) -> None:
        self.llm = llm or GroqClient()

    # ── Public API ──────────────────────────────────────────────────
    def analyze(self, query: str, *, scope: dict[str, Any] | None = None,
                history: list[dict] | None = None) -> AnalysisResponse:
        scope = scope or {}
        tracer = AITracer(agent=self.agent_name)

        with tracer.span("guardrails"):
            blocked = classify_safety(query)
            if blocked is Intent.UNSAFE:
                tracer.persist()
                return AnalysisResponse(
                    intent=Intent.UNSAFE,
                    headline="Pergunta bloqueada pelo guardrail",
                    summary="A consulta foi bloqueada por conter padrões inseguros "
                            "(prompt-injection, SQL destrutivo ou tamanho excessivo).",
                    confidence=Confidence.HIGH, agent=self.agent_name,
                    trace_id=tracer.trace.trace_id,
                )
            safe_query = redact_pii(truncate(query, 1600))

        with tracer.span("context_load") as sp:
            context = self.load_context(safe_query, scope)
            sp.meta["context_keys"] = list(context.keys())

        with tracer.span("llm_call") as sp:
            messages = self._build_messages(safe_query, context, history or [])
            answer_md = self.llm.complete(messages, temperature=0.15)
            sp.meta["chars"] = len(answer_md)

        with tracer.span("parse"):
            response = self._compose_response(answer_md, context, tracer.trace.trace_id)

        tracer.persist()
        return response

    # ── To override ─────────────────────────────────────────────────
    @abstractmethod
    def load_context(self, query: str, scope: dict[str, Any]) -> dict: ...

    @property
    @abstractmethod
    def system_prompt(self) -> str: ...

    # ── Internals ───────────────────────────────────────────────────
    def _build_messages(self, query: str, context: dict, history: list[dict]) -> list[dict]:
        dossier = json.dumps(context, ensure_ascii=False, indent=2, default=str)
        msgs: list[dict] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "system", "content": "## DOSSIÊ OPERACIONAL\n```json\n" + dossier + "\n```"},
        ]
        for h in history[-6:]:
            msgs.append({"role": h["role"], "content": h["content"]})
        msgs.append({"role": "user", "content": query})
        return msgs

    def _compose_response(self, answer_md: str, context: dict, trace_id: str) -> AnalysisResponse:
        # Heuristic headline = first non-empty line under "### Resumo executivo"
        headline = self._extract_section(answer_md, "Resumo executivo") or answer_md[:140]
        root_cause = self._extract_section(answer_md, "Causa raiz")
        impact = self._extract_section(answer_md, "Impacto financeiro")
        confidence = self._extract_confidence(answer_md)

        return AnalysisResponse(
            intent=self.intent,
            headline=headline.strip().split("\n")[0][:180],
            summary=answer_md,
            root_cause=root_cause,
            evidence=evidence_from_context(context),
            financial_impact=impact,
            recommendations=self._extract_recommendations(answer_md),
            confidence=confidence,
            agent=self.agent_name,
            model=settings.groq.model,
            trace_id=trace_id,
        )

    # ── Section extractors (simple markdown parser) ────────────────
    _NEXT_HEADING = re.compile(r"\n#{2,}\s", re.MULTILINE)

    @staticmethod
    def _extract_section(md: str, header: str) -> str | None:
        lo = md.lower()
        h = header.lower()
        idx = lo.find(h)
        if idx < 0:
            return None
        rest = md[idx + len(header):]
        # Next heading of any level (##, ###, ####, ...) terminates the section
        m = BaseAgent._NEXT_HEADING.search(rest)
        return (rest[:m.start()] if m else rest).strip(" :\n")

    @staticmethod
    def _extract_confidence(md: str) -> Confidence:
        # Restrict search to a "confiança" / "confidence" section when present;
        # fall back to last occurrence in full text only if no section is found.
        section = BaseAgent._extract_section(md, "Confiança") \
               or BaseAgent._extract_section(md, "Confidence") \
               or md
        found = Confidence.MEDIUM
        for m in re.finditer(r"\b(HIGH|MEDIUM|LOW)\b", section.upper()):
            found = Confidence(m.group(1))
        return found

    @staticmethod
    def _extract_recommendations(md: str) -> list[Recommendation]:
        section = BaseAgent._extract_section(md, "Recomendação") or ""
        out: list[Recommendation] = []
        for line in section.splitlines():
            line = line.strip("- *0123456789. ").strip()
            if not line:
                continue
            prio = "P1" if line.startswith("**P1") or "P1" in line[:6] else \
                   "P3" if "P3" in line[:6] else "P2"
            out.append(Recommendation(title=line[:80], detail=line, priority=prio))
            if len(out) >= 6:
                break
        return out
