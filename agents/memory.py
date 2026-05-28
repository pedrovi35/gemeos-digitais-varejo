"""
Conversation memory — short-term context across analyst turns.

Sessions are keyed by an opaque session_id (typically a Streamlit session
token). Memory is capped at N turns and persisted only in-process.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime

from utils.time_utils import now_tz


@dataclass
class Turn:
    role: str               # 'user' | 'assistant'
    content: str
    ts: datetime = field(default_factory=now_tz)
    intent: str | None = None
    trace_id: str | None = None


class ConversationMemory:
    """In-process conversation memory with a sliding window."""

    def __init__(self, max_turns: int = 12) -> None:
        self.max_turns = max_turns
        self._store: dict[str, deque[Turn]] = {}

    def append(self, session_id: str, turn: Turn) -> None:
        buf = self._store.setdefault(session_id, deque(maxlen=self.max_turns))
        buf.append(turn)

    def history(self, session_id: str) -> list[Turn]:
        return list(self._store.get(session_id, ()))

    def to_messages(self, session_id: str) -> list[dict]:
        return [{"role": t.role, "content": t.content}
                for t in self.history(session_id)]

    def reset(self, session_id: str | None = None) -> None:
        if session_id is None:
            self._store.clear()
        else:
            self._store.pop(session_id, None)


_GLOBAL = ConversationMemory()


def get_memory() -> ConversationMemory:
    return _GLOBAL
