"""
Application bootstrap — schema, seed, directories, health.

Called once per Streamlit session via `@st.cache_resource`.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import streamlit as st

from config.logging import configure_logging, logger
from config.settings import settings
from core.monitoring import record_boot
from core.secrets import hydrate_settings_from_secrets, is_streamlit_cloud


@dataclass(frozen=True)
class RuntimeStatus:
    ok: bool
    boot_ms: float
    light_seed: bool
    cloud: bool
    message: str


def _ensure_directories() -> None:
    for path in (
        settings.duckdb.path.parent,
        settings.lake.bronze,
        settings.lake.silver,
        settings.lake.gold,
        settings.root / "data" / "features",
        settings.root / "models" / "artifacts",
        settings.log_path.parent,
    ):
        Path(path).mkdir(parents=True, exist_ok=True)


@st.cache_resource(show_spinner=False)
def ensure_runtime(*, force_seed: bool = False) -> RuntimeStatus:
    """
    Idempotent runtime initialization.
    Spinner is controlled by the caller (`after_page_config`).
    """
    t0 = time.perf_counter()
    configure_logging()
    _ensure_directories()

    from database.schema import bootstrap_warehouse
    from database.seed import seed_warehouse

    bootstrap_warehouse()
    seed_warehouse(force=force_seed)

    boot_ms = (time.perf_counter() - t0) * 1000
    record_boot(boot_ms)

    from config.settings import settings as live_settings
    light = live_settings.twin.light_seed
    cloud = is_streamlit_cloud()
    msg = f"ready · {'light' if light else 'full'} seed · {boot_ms:.0f}ms"
    logger.info(f"Runtime bootstrap complete — {msg}")

    return RuntimeStatus(
        ok=True,
        boot_ms=boot_ms,
        light_seed=light,
        cloud=cloud,
        message=msg,
    )
