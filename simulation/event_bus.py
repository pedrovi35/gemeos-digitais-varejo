"""
Lightweight pub/sub event bus for the simulation layer.

Subscribers register callables per event-type; the engine and any analytics
consumer can listen without coupling. Thread-safe enough for Streamlit's
single-process model.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from config.constants import EventType
from config.logging import logger


@dataclass
class SimEvent:
    event_type: EventType
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: Any = None


class EventBus:
    _instance: "EventBus | None" = None

    def __new__(cls) -> "EventBus":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._subs = defaultdict(list)
        return cls._instance

    def subscribe(self, event_type: EventType, handler: Callable[[SimEvent], None]) -> None:
        self._subs[event_type].append(handler)

    def publish(self, event: SimEvent) -> None:
        for handler in self._subs.get(event.event_type, []):
            try:
                handler(event)
            except Exception as e:                       # pragma: no cover
                logger.exception(f"event handler failed: {e}")

    def reset(self) -> None:
        self._subs.clear()
