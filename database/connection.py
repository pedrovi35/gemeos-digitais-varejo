"""
DuckDB connection manager.

DuckDB is process-local; we keep a single connection per Streamlit session
through `st.cache_resource`, so reruns reuse the same handle and prepared
statements stay warm.
"""
from __future__ import annotations

from pathlib import Path

import duckdb

from config.logging import logger
from config.settings import settings
from utils.cache import cached_resource


@cached_resource()
def get_connection() -> duckdb.DuckDBPyConnection:
    """Return a configured DuckDB connection (singleton per session)."""
    path: Path = settings.duckdb.path
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(database=str(path), read_only=settings.duckdb.read_only)
    conn.execute(f"PRAGMA threads={settings.duckdb.threads};")
    conn.execute(f"PRAGMA memory_limit='{settings.duckdb.memory_limit}';")
    conn.execute("PRAGMA enable_progress_bar=false;")

    # Useful extensions
    for ext in ("httpfs", "json"):
        try:
            conn.execute(f"INSTALL {ext}; LOAD {ext};")
        except Exception as e:        # pragma: no cover
            logger.debug(f"extension {ext} unavailable: {e}")

    logger.info(f"DuckDB connected → {path}")
    return conn


def close_connection() -> None:
    try:
        conn = get_connection()
        conn.close()
        logger.info("DuckDB connection closed")
    except Exception as e:           # pragma: no cover
        logger.warning(f"failed to close DuckDB cleanly: {e}")
