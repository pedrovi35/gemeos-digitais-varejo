"""
Structured tracer for AI calls.

Every analyst invocation produces a trace_id and a series of spans
(context_load, llm_call, parse, persist). Traces land in `log_events`
so they're queryable from the System Console.
"""
from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field

from config.constants import AlertSeverity, EventType
from config.logging import logger


@dataclass
class Span:
    name: str
    started_at: float = field(default_factory=time.perf_counter)
    elapsed_ms: float | None = None
    meta: dict = field(default_factory=dict)
    error: str | None = None


@dataclass
class Trace:
    trace_id: str
    agent: str
    spans: list[Span] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "agent": self.agent,
            "spans": [
                {"name": s.name, "elapsed_ms": s.elapsed_ms,
                 "meta": s.meta, "error": s.error}
                for s in self.spans
            ],
        }


class AITracer:
    """Lightweight per-invocation tracer."""

    def __init__(self, agent: str) -> None:
        self.trace = Trace(trace_id=f"TRC-{uuid.uuid4().hex[:10].upper()}", agent=agent)

    @contextmanager
    def span(self, name: str, **meta):
        sp = Span(name=name, meta=dict(meta))
        try:
            yield sp
        except Exception as e:                                # pragma: no cover
            sp.error = str(e)
            raise
        finally:
            sp.elapsed_ms = (time.perf_counter() - sp.started_at) * 1000
            self.trace.spans.append(sp)

    def persist(self) -> None:
        """Persist trace summary to log_events (best-effort)."""
        try:
            from services.event_service import EventService
            EventService().emit(
                EventType.SALE if False else EventType.DEMAND_SPIKE,  # placeholder type
                payload={"trace": self.trace.to_dict(), "marker": "AI_TRACE"},
                severity=AlertSeverity.INFO,
            )
        except Exception as e:                                # pragma: no cover
            logger.debug(f"trace persist skipped: {e}")
        logger.info(f"[trace {self.trace.trace_id}] {self.trace.agent} · "
                    f"spans={len(self.trace.spans)} · "
                    f"total={sum((s.elapsed_ms or 0) for s in self.trace.spans):.0f}ms")
