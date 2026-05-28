"""Base class for per-rupture feature engineering."""
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
import pandas as pd

from database.connection import get_connection
from services.base import _render_interval_params


class BaseFeatureEngineering(ABC):
    """Each rupture overrides `build()` returning a DataFrame with:

        - one row per entity (store×sku or supplier)
        - `feature_cols` numeric columns
        - `target_col` binary 0/1
        - `entity_key` string column for joining back
    """
    rupture_code: str = ""
    feature_cols: tuple[str, ...] = ()
    target_col:   str = "target"
    entity_key:   str = "entity_key"

    def __init__(self) -> None:
        self.conn = get_connection()
        # Set by build() when running a backtest: every CURRENT_TIMESTAMP in
        # SQL templates is rewritten to this fixed instant so feature windows
        # contain only data observable on or before the cutoff.
        self._cutoff_ts: pd.Timestamp | None = None

    # ── To override ─────────────────────────────────────────────────
    @abstractmethod
    def build(self, *, horizon_days: int = 7,
              cutoff_ts: pd.Timestamp | None = None) -> pd.DataFrame: ...

    # ── Shared time-series helpers ─────────────────────────────────
    @staticmethod
    def add_rolling_features(df: pd.DataFrame, group_cols: list[str], value_col: str,
                             windows: tuple[int, ...] = (7, 14, 28)) -> pd.DataFrame:
        df = df.sort_values(group_cols + ["d"]).copy()
        g = df.groupby(group_cols, sort=False)[value_col]
        for w in windows:
            df[f"{value_col}_mean_{w}d"] = g.transform(lambda s, _w=w: s.rolling(_w, min_periods=1).mean())
            df[f"{value_col}_std_{w}d"]  = g.transform(lambda s, _w=w: s.rolling(_w, min_periods=1).std().fillna(0))
        return df

    @staticmethod
    def zscore(df: pd.DataFrame, value_col: str, mean_col: str, std_col: str,
               out_col: str) -> pd.DataFrame:
        df[out_col] = (df[value_col] - df[mean_col]) / df[std_col].replace(0, np.nan)
        df[out_col] = df[out_col].fillna(0).clip(-6, 6)
        return df

    def trim_to_cutoff(self, df: pd.DataFrame, ts_col: str = "d") -> pd.DataFrame:
        """Drop rows whose anchoring date is beyond the active backtest cutoff."""
        if self._cutoff_ts is None or df.empty or ts_col not in df.columns:
            return df
        cutoff = pd.Timestamp(self._cutoff_ts).tz_localize(None)
        col = pd.to_datetime(df[ts_col])
        if getattr(col.dt, "tz", None) is not None:
            col = col.dt.tz_localize(None)
        return df[col <= cutoff].copy()

    @staticmethod
    def datetime_features(df: pd.DataFrame, ts_col: str = "d") -> pd.DataFrame:
        ts = pd.to_datetime(df[ts_col])
        df["dow"]        = ts.dt.dayofweek
        df["is_weekend"] = (df["dow"] >= 5).astype(int)
        df["day"]        = ts.dt.day
        df["is_payday"]  = df["day"].isin([5, 15, 20, 30]).astype(int)
        df["month"]      = ts.dt.month
        df["quarter"]    = ts.dt.quarter
        return df

    # ── Convenience SQL ────────────────────────────────────────────
    def df(self, sql: str, params: list | None = None) -> pd.DataFrame:
        if self._cutoff_ts is not None:
            ts = pd.Timestamp(self._cutoff_ts).strftime("%Y-%m-%d %H:%M:%S")
            sql = sql.replace("CURRENT_TIMESTAMP", f"TIMESTAMP '{ts}'")
        rendered, remaining = _render_interval_params(sql, list(params or []))
        return self.conn.execute(rendered, remaining).fetch_df()
