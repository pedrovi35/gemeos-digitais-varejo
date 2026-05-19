"""Internal performance monitoring — query timings, cache hits, boot metrics."""
from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator

import streamlit as st


@dataclass
class MetricEntry:
    name: str
    duration_ms: float
    meta: dict[str, Any] = field(default_factory=dict)


def _store() -> dict:
    if "_twin_metrics" not in st.session_state:
        st.session_state["_twin_metrics"] = {
            "queries": [],
            "boot_ms": None,
            "cache_hits": 0,
            "errors": 0,
        }
    return st.session_state["_twin_metrics"]


def record_timing(name: str, duration_ms: float, **meta: Any) -> None:
    store = _store()
    store["queries"].append(MetricEntry(name=name, duration_ms=duration_ms, meta=meta))
    if len(store["queries"]) > 100:
        store["queries"] = store["queries"][-100:]


def record_boot(duration_ms: float) -> None:
    _store()["boot_ms"] = duration_ms


def record_error() -> None:
    _store()["errors"] = int(_store().get("errors", 0)) + 1


def get_metrics() -> dict:
    store = _store()
    queries: list[MetricEntry] = store.get("queries", [])
    durations = [q.duration_ms for q in queries[-20:]]
    return {
        "boot_ms": store.get("boot_ms"),
        "error_count": store.get("errors", 0),
        "query_count": len(queries),
        "avg_query_ms": sum(durations) / len(durations) if durations else 0.0,
        "p95_query_ms": sorted(durations)[int(len(durations) * 0.95)] if durations else 0.0,
        "recent": queries[-8:],
    }


@contextmanager
def track(name: str, **meta: Any) -> Generator[None, None, None]:
    t0 = time.perf_counter()
    try:
        yield
    finally:
        record_timing(name, (time.perf_counter() - t0) * 1000, **meta)
