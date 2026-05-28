"""
Secrets & environment hydration.

Priority:
  1. Streamlit Cloud `st.secrets` (production)
  2. `.env` file via pydantic-settings (local)
  3. OS environment variables
"""
from __future__ import annotations

import os
from typing import Any

from config.logging import logger


def is_streamlit_cloud() -> bool:
    """Detect Streamlit Community Cloud / Snowflake hosting."""
    flags = (
        os.getenv("STREAMLIT_SHARING_MODE"),
        os.getenv("STREAMLIT_RUNTIME_ENV"),
        os.getenv("IS_STREAMLIT_CLOUD"),
    )
    return any(flags)


def _read_streamlit_secrets() -> dict[str, Any]:
    try:
        import streamlit as st
        if not hasattr(st, "secrets") or not st.secrets:
            return {}
        out: dict[str, Any] = {}
        for section in ("", "groq", "twin", "duckdb"):
            block = st.secrets.get(section, {}) if section else st.secrets
            if isinstance(block, dict):
                out.update({str(k): v for k, v in block.items()})
        return out
    except Exception:
        return {}


def hydrate_settings_from_secrets() -> None:
    """Push secrets into os.environ so pydantic settings pick them up."""
    secrets = _read_streamlit_secrets()
    mapping = {
        "GROQ_API_KEY": secrets.get("GROQ_API_KEY") or secrets.get("groq_api_key"),
        "GROQ_MODEL": secrets.get("GROQ_MODEL"),
        "GROQ_TIMEOUT": secrets.get("GROQ_TIMEOUT"),
        "GROQ_MAX_TOKENS": secrets.get("GROQ_MAX_TOKENS"),
        "TWIN_ENV": secrets.get("TWIN_ENV"),
        "TWIN_LIGHT_SEED": secrets.get("TWIN_LIGHT_SEED"),
        "DUCKDB_PATH": secrets.get("DUCKDB_PATH"),
        "DUCKDB_THREADS": secrets.get("DUCKDB_THREADS"),
        "DUCKDB_MEMORY_LIMIT": secrets.get("DUCKDB_MEMORY_LIMIT"),
        "LOG_LEVEL": secrets.get("LOG_LEVEL"),
    }
    for key, val in mapping.items():
        if val is not None and str(val).strip():
            os.environ[key] = str(val)

    if is_streamlit_cloud() and not os.getenv("TWIN_LIGHT_SEED"):
        os.environ.setdefault("TWIN_LIGHT_SEED", "true")
        os.environ.setdefault("TWIN_ENV", "production")
        logger.info("Streamlit Cloud detected — light seed profile enabled")
