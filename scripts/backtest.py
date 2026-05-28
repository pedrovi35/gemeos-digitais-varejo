#!/usr/bin/env python3
"""
Walk-forward backtest for the five rupture models.

For each cutoff T in a sliding window, the pipeline:
  1. rebuilds features using only data observable at or before T
     (FE.build(cutoff_ts=T))
  2. trains a fresh in-memory model (persist=False, no artifact pollution)
  3. scores entities as of day T
  4. joins scores with the events that actually happened in (T, T+H]
  5. reports out-of-time AUC, precision@k, recall, and lead time

The score for "did the entity rupture?" is computed from the warehouse
post-cutoff window — so the labels used here were never visible during
training, making the AUC an honest predictive metric.

Usage:
    python scripts/backtest.py
    python scripts/backtest.py --rupture R1
    python scripts/backtest.py --horizon 7 --cutoffs 35 28 21
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score, precision_score, recall_score, roc_auc_score,
)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config.logging import configure_logging, logger  # noqa: E402
from database.connection import get_connection  # noqa: E402
from models.shared.registry import MODEL_CATALOG, RuptureCode  # noqa: E402
from utils.time_utils import now_tz  # noqa: E402


def _fe(code: RuptureCode):
    pkg = MODEL_CATALOG[code].package
    mod = __import__(f"{pkg}.feature_engineering", fromlist=["FeatureEngineering"])
    return mod.FeatureEngineering()


def _trainer(code: RuptureCode):
    pkg = MODEL_CATALOG[code].package
    mod = __import__(f"{pkg}.trainer", fromlist=["Trainer"])
    return mod.Trainer()


def _realized_events(code: RuptureCode, cutoff: pd.Timestamp, horizon: int) -> pd.DataFrame:
    """Return entities that actually experienced the rupture in (cutoff, cutoff+H]."""
    conn = get_connection()
    end = cutoff + timedelta(days=horizon)
    cutoff_s = cutoff.strftime("%Y-%m-%d %H:%M:%S")
    end_s    = end.strftime("%Y-%m-%d %H:%M:%S")

    if code == RuptureCode.R5:
        # Realized blocked supplier: any rejected/blocked PO in the window.
        sql = f"""
            SELECT supplier_id AS entity_key, 1 AS realized
            FROM fct_replenishment
            WHERE placed_ts > TIMESTAMP '{cutoff_s}'
              AND placed_ts <= TIMESTAMP '{end_s}'
              AND status IN ('REJECTED','BLOCKED','CANCELLED')
            GROUP BY supplier_id
        """
    else:
        # store_id+sku_id became STOCKOUT or CRITICAL in the future window.
        sql = f"""
            SELECT (store_id || '·' || sku_id) AS entity_key, 1 AS realized
            FROM fct_inventory_snapshot
            WHERE snapshot_ts > TIMESTAMP '{cutoff_s}'
              AND snapshot_ts <= TIMESTAMP '{end_s}'
              AND status IN ('STOCKOUT','CRITICAL')
            GROUP BY store_id, sku_id
        """
    return conn.execute(sql).fetch_df()


def _score_at_cutoff(code: RuptureCode, cutoff: pd.Timestamp, horizon: int) -> dict | None:
    fe = _fe(code)
    df = fe.build(cutoff_ts=cutoff)
    if df.empty or df["target"].sum() < 2:
        logger.warning(f"[{code.value} @ {cutoff.date()}] skipping: insufficient training data")
        return None

    trainer = _trainer(code)
    metrics_in_sample = trainer.fit(df, persist=False)

    # Score set = most recent feature row per entity at the cutoff.
    last_d = df["d"].max()
    score_df = df[df["d"] == last_d].copy()
    if score_df.empty:
        return None
    X = score_df[trainer.feature_cols].fillna(0).astype(np.float32)
    score_df["risk"] = trainer.predict(X)

    realized = _realized_events(code, cutoff, horizon)
    score_df = score_df.merge(realized, on="entity_key", how="left")
    score_df["realized"] = score_df["realized"].fillna(0).astype(int)

    y_true = score_df["realized"].values
    y_pred = score_df["risk"].values

    pos = int(y_true.sum())
    if pos == 0 or pos == len(y_true):
        auc = float("nan")
        ap = float("nan")
    else:
        auc = float(roc_auc_score(y_true, y_pred))
        ap = float(average_precision_score(y_true, y_pred))

    # Precision@k for operational ranking
    top_k = score_df.nlargest(min(10, len(score_df)), "risk")
    precision_at_10 = float(top_k["realized"].mean()) if len(top_k) else float("nan")

    # Threshold-based confusion at risk >= 0.5
    y_bin = (y_pred >= 0.5).astype(int)
    if y_bin.sum() and y_true.sum():
        prec = float(precision_score(y_true, y_bin, zero_division=0))
        rec  = float(recall_score(y_true, y_bin, zero_division=0))
    else:
        prec = rec = float("nan")

    return {
        "rupture":          code.value,
        "cutoff":           str(cutoff.date()),
        "horizon_days":     horizon,
        "n_entities_at_cutoff": int(len(score_df)),
        "n_realized":       pos,
        "positive_rate":    float(y_true.mean()),
        "auc_out_of_time":  auc,
        "avg_precision":    ap,
        "precision_at_10":  precision_at_10,
        "precision@0.5":    prec,
        "recall@0.5":       rec,
        "in_sample_auc":    metrics_in_sample.roc_auc,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Walk-forward backtest")
    parser.add_argument("--rupture", choices=[c.value for c in RuptureCode], default=None)
    parser.add_argument("--horizon", type=int, default=7)
    parser.add_argument("--cutoffs", type=int, nargs="+", default=[35, 28, 21],
                        help="days before now() to use as cutoffs")
    parser.add_argument("--output", type=str, default="data/backtest_results.json")
    args = parser.parse_args()

    configure_logging()
    now = pd.Timestamp(now_tz()).tz_localize(None)
    cutoffs = [now - timedelta(days=d) for d in args.cutoffs]
    codes = [RuptureCode(args.rupture)] if args.rupture else list(RuptureCode)

    results: list[dict] = []
    for code in codes:
        for ct in cutoffs:
            logger.info(f"═══ {code.value} @ cutoff={ct.date()} (H={args.horizon}d) ═══")
            try:
                r = _score_at_cutoff(code, ct, args.horizon)
                if r:
                    results.append(r)
            except Exception as e:
                logger.exception(f"[{code.value} @ {ct.date()}] failed: {e}")

    if not results:
        logger.warning("no results produced")
        return

    df = pd.DataFrame(results)
    print()
    print("=" * 100)
    print("Walk-forward backtest summary (out-of-time)")
    print("=" * 100)
    cols = ["rupture", "cutoff", "n_entities_at_cutoff", "n_realized",
            "positive_rate", "auc_out_of_time", "avg_precision",
            "precision_at_10", "in_sample_auc"]
    print(df[cols].to_string(index=False, float_format="%.3f"))

    summary = (
        df.groupby("rupture")
          .agg(auc_oot=("auc_out_of_time", "mean"),
               ap=("avg_precision", "mean"),
               p_at_10=("precision_at_10", "mean"),
               auc_in_sample=("in_sample_auc", "mean"),
               n_windows=("cutoff", "count"))
          .reset_index()
    )
    print()
    print("Per-rupture average across cutoffs:")
    print(summary.to_string(index=False, float_format="%.3f"))

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    logger.info(f"results → {out}")


if __name__ == "__main__":
    main()
