"""
Backtest service — produces row-level scored frames for calibration analysis,
counterfactual simulation, and the Streamlit proof-of-value page.

Public API:
    score_window(code, cutoff, horizon) -> pd.DataFrame
    daily_revenue_by_entity(code, cutoff) -> pd.DataFrame

Everything goes through the cutoff-aware feature engineering so no future
information leaks into the training set; realized events are pulled from
the warehouse for the strict (cutoff, cutoff+H] window.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from functools import lru_cache

import numpy as np
import pandas as pd

from config.logging import logger
from database.connection import get_connection
from models.shared.registry import MODEL_CATALOG, RuptureCode


def _fe(code: RuptureCode):
    pkg = MODEL_CATALOG[code].package
    mod = __import__(f"{pkg}.feature_engineering", fromlist=["FeatureEngineering"])
    return mod.FeatureEngineering()


def _trainer(code: RuptureCode):
    pkg = MODEL_CATALOG[code].package
    mod = __import__(f"{pkg}.trainer", fromlist=["Trainer"])
    return mod.Trainer()


def _realized_events(code: RuptureCode, cutoff: pd.Timestamp, horizon: int) -> pd.DataFrame:
    """Realized events with their first-occurrence date inside (cutoff, cutoff+H]."""
    conn = get_connection()
    end = cutoff + timedelta(days=horizon)
    cutoff_s = cutoff.strftime("%Y-%m-%d %H:%M:%S")
    end_s    = end.strftime("%Y-%m-%d %H:%M:%S")

    if code == RuptureCode.R5:
        sql = f"""
            SELECT supplier_id AS entity_key,
                   MIN(CAST(placed_ts AS DATE)) AS realized_date
            FROM fct_replenishment
            WHERE placed_ts > TIMESTAMP '{cutoff_s}'
              AND placed_ts <= TIMESTAMP '{end_s}'
              AND status IN ('REJECTED','BLOCKED','CANCELLED')
            GROUP BY supplier_id
        """
    else:
        sql = f"""
            SELECT (store_id || '·' || sku_id) AS entity_key,
                   MIN(CAST(snapshot_ts AS DATE)) AS realized_date
            FROM fct_inventory_snapshot
            WHERE snapshot_ts > TIMESTAMP '{cutoff_s}'
              AND snapshot_ts <= TIMESTAMP '{end_s}'
              AND status IN ('STOCKOUT','CRITICAL')
            GROUP BY store_id, sku_id
        """
    df = conn.execute(sql).fetch_df()
    df["realized"] = 1
    return df


def daily_revenue_by_entity(code: RuptureCode, cutoff: pd.Timestamp) -> pd.DataFrame:
    """Average daily revenue per entity in the 28 days BEFORE the cutoff.

    Used to monetize counterfactual ruptures: a rupture costs roughly
    `daily_revenue × horizon` in lost sales.
    """
    conn = get_connection()
    cutoff_s = cutoff.strftime("%Y-%m-%d %H:%M:%S")
    start_s  = (cutoff - timedelta(days=28)).strftime("%Y-%m-%d %H:%M:%S")

    if code == RuptureCode.R5:
        sql = f"""
            SELECT k.supplier_id AS entity_key,
                   COALESCE(SUM(s.revenue) / 28.0, 0) AS daily_revenue
            FROM fct_sales s
            INNER JOIN dim_sku k USING (sku_id)
            WHERE s.sale_ts > TIMESTAMP '{start_s}'
              AND s.sale_ts <= TIMESTAMP '{cutoff_s}'
            GROUP BY k.supplier_id
        """
    else:
        sql = f"""
            SELECT (store_id || '·' || sku_id) AS entity_key,
                   COALESCE(SUM(revenue) / 28.0, 0) AS daily_revenue
            FROM fct_sales
            WHERE sale_ts > TIMESTAMP '{start_s}'
              AND sale_ts <= TIMESTAMP '{cutoff_s}'
            GROUP BY store_id, sku_id
        """
    return conn.execute(sql).fetch_df()


@dataclass
class ScoreWindow:
    code: RuptureCode
    cutoff: pd.Timestamp
    horizon: int
    scored: pd.DataFrame             # entity_key, risk, realized, realized_date, daily_revenue, lead_days
    in_sample_auc: float
    n_train: int


def score_window(code: RuptureCode, cutoff: pd.Timestamp, horizon: int) -> ScoreWindow | None:
    """Train at cutoff, score entities as of cutoff, join with realized events.

    Returns None if there is not enough data to train at this cutoff.
    The model is trained in-memory (persist=False) — production artifacts
    are untouched.
    """
    fe = _fe(code)
    df = fe.build(cutoff_ts=cutoff)
    if df.empty or df["target"].sum() < 2:
        logger.warning(f"[{code.value}@{cutoff.date()}] insufficient data — skipping")
        return None

    trainer = _trainer(code)
    metrics = trainer.fit(df, persist=False)

    last_d = df["d"].max()
    score_df = df[df["d"] == last_d].copy()
    if score_df.empty:
        return None
    X = score_df[trainer.feature_cols].fillna(0).astype(np.float32)
    score_df["risk"] = trainer.predict(X)

    realized = _realized_events(code, cutoff, horizon)
    score_df = score_df.merge(realized, on="entity_key", how="left")
    score_df["realized"] = score_df["realized"].fillna(0).astype(int)
    score_df["realized_date"] = pd.to_datetime(score_df.get("realized_date"))

    score_df["lead_days"] = (
        (score_df["realized_date"] - pd.Timestamp(cutoff).normalize()).dt.days
    )

    rev = daily_revenue_by_entity(code, cutoff)
    score_df = score_df.merge(rev, on="entity_key", how="left")
    score_df["daily_revenue"] = score_df["daily_revenue"].fillna(0.0)

    keep = ["entity_key", "risk", "realized", "realized_date",
            "lead_days", "daily_revenue"]
    return ScoreWindow(
        code=code, cutoff=cutoff, horizon=horizon,
        scored=score_df[keep].sort_values("risk", ascending=False).reset_index(drop=True),
        in_sample_auc=float(metrics.roc_auc) if metrics.roc_auc is not None else float("nan"),
        n_train=int(len(df)),
    )


@lru_cache(maxsize=32)
def score_window_cached(code_value: str, cutoff_iso: str, horizon: int) -> ScoreWindow | None:
    """LRU-cached version for the Streamlit page (hashable args only)."""
    return score_window(RuptureCode(code_value), pd.Timestamp(cutoff_iso), horizon)
