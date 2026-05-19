"""Service base class — wraps the DuckDB connection and exposes helpers."""
from __future__ import annotations

import re
import pandas as pd

from database.connection import get_connection


def _render_interval_params(sql: str, params: list) -> tuple[str, list]:
    """Replace INTERVAL ? DAY/HOUR patterns with literal integers.

    DuckDB does not support parameterized INTERVAL values. This helper
    pre-renders those specific placeholders as safe integer literals
    (always sourced from internal code, never user input) while leaving
    all remaining ``?`` placeholders intact for DuckDB binding.
    """
    pattern = re.compile(r"INTERVAL\s+\?\s+(DAY|HOUR|MINUTE|SECOND|MONTH|YEAR)", re.IGNORECASE)
    remaining: list = []
    param_iter = iter(params)

    def _replace(m: re.Match) -> str:
        val = next(param_iter)
        return f"INTERVAL {int(val)} {m.group(1).upper()}"

    rendered = pattern.sub(_replace, sql)
    # Collect remaining params (those not consumed by interval replacements)
    remaining = list(param_iter)
    return rendered, remaining


class BaseService:
    """Thin base — every concrete service inherits read/write helpers from here."""

    def __init__(self) -> None:
        self.conn = get_connection()

    def df(self, sql: str, params: tuple | list | None = None) -> pd.DataFrame:
        # DuckDB does not support `?` inside INTERVAL literals.
        # We pre-render integer placeholders that appear in INTERVAL contexts.
        rendered, remaining = _render_interval_params(sql, list(params or []))
        try:
            cur = self.conn.execute(rendered, remaining)
            return cur.fetch_df()
        except Exception:
            raise

    def scalar(self, sql: str, params: tuple | list | None = None):
        rendered, remaining = _render_interval_params(sql, list(params or []))
        row = self.conn.execute(rendered, remaining).fetchone()
        return row[0] if row else None

    def execute(self, sql: str, params: tuple | list | None = None) -> None:
        rendered, remaining = _render_interval_params(sql, list(params or []))
        self.conn.execute(rendered, remaining)
