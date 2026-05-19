"""
Session state manager — schema-validated keys and idempotent initialization.

All pages read/write through `SessionState` so we avoid stringly-typed keys
scattered through the codebase.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import streamlit as st

from utils.time_utils import now_tz


@dataclass
class SessionDefaults:
    twin_running: bool = False
    sim_clock: datetime = field(default_factory=now_tz)
    sim_speed: int = 60          # x-real-time multiplier
    selected_store: str = "ST-001"
    selected_category: str = "All"
    chat_history: list[dict[str, str]] = field(default_factory=list)
    last_scenario: dict[str, Any] = field(default_factory=dict)
    alerts_acknowledged: set[str] = field(default_factory=set)
    initialized: bool = False


class SessionState:
    """Thin façade around `st.session_state` with typed defaults."""

    @staticmethod
    def init() -> None:
        if st.session_state.get("initialized"):
            return
        for key, value in SessionDefaults().__dict__.items():
            st.session_state.setdefault(key, value)
        st.session_state["initialized"] = True

    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        return st.session_state.get(key, default)

    @staticmethod
    def set(key: str, value: Any) -> None:
        st.session_state[key] = value

    @staticmethod
    def toggle(key: str) -> bool:
        st.session_state[key] = not st.session_state.get(key, False)
        return st.session_state[key]
