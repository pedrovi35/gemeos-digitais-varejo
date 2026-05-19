"""
Inventory generator — holds the live (store × SKU) state during simulation
and persists daily snapshots to parquet in monthly chunks.

State columns kept in memory as numpy arrays of shape (n_stores, n_skus):
  on_hand          int32
  on_order         int32
  reorder_point    int32
  safety_stock     int32
  days_out_streak  int16
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class InventoryState:
    store_ids: np.ndarray
    sku_ids: np.ndarray
    on_hand: np.ndarray
    on_order: np.ndarray
    reorder_point: np.ndarray
    safety_stock: np.ndarray
    days_out_streak: np.ndarray = field(default=None)

    def __post_init__(self) -> None:
        if self.days_out_streak is None:
            self.days_out_streak = np.zeros_like(self.on_hand, dtype=np.int16)


class InventoryGenerator:
    """Initial state builder + daily snapshot writer (monthly partition)."""

    def __init__(self, *, seed: int = 41) -> None:
        self.rng = np.random.default_rng(seed)

    # ── Initial state ───────────────────────────────────────
    def initial_state(self, stores: pd.DataFrame, skus: pd.DataFrame) -> InventoryState:
        n_s, n_k = len(stores), len(skus)
        base = skus["base_daily_rate"].to_numpy(dtype=np.float32)
        # Reorder point ≈ 7 days of demand, safety stock ≈ 3 days
        rop = np.maximum(8, (base * 7).astype(np.int32))
        ss  = np.maximum(3, (base * 3).astype(np.int32))
        # Tile across stores and add per-store variability
        store_mult = self.rng.uniform(0.7, 1.4, size=(n_s, 1)).astype(np.float32)
        rop_2d = np.tile(rop, (n_s, 1)) * store_mult
        ss_2d  = np.tile(ss,  (n_s, 1)) * store_mult
        on_hand = (rop_2d * self.rng.uniform(1.2, 2.8, size=(n_s, n_k))).astype(np.int32)
        return InventoryState(
            store_ids=stores["store_id"].to_numpy(),
            sku_ids=skus["sku_id"].to_numpy(),
            on_hand=on_hand,
            on_order=np.zeros((n_s, n_k), dtype=np.int32),
            reorder_point=rop_2d.astype(np.int32),
            safety_stock=ss_2d.astype(np.int32),
        )

    # ── Snapshot row generation ─────────────────────────────
    @staticmethod
    def snapshot(state: InventoryState, day: date,
                 daily_demand_estimate: np.ndarray) -> pd.DataFrame:
        n_s, n_k = state.on_hand.shape
        store_grid = np.repeat(state.store_ids, n_k)
        sku_grid   = np.tile(state.sku_ids, n_s)

        on_hand = state.on_hand.ravel()
        on_order = state.on_order.ravel()
        rop = state.reorder_point.ravel()
        ss  = state.safety_stock.ravel()
        demand = np.maximum(0.1, daily_demand_estimate.ravel())
        cover = on_hand / demand

        status = np.full(on_hand.shape, "HEALTHY", dtype=object)
        status[on_hand <= 0]            = "STOCKOUT"
        status[(on_hand > 0) & (on_hand <= ss)]                  = "CRITICAL"
        status[(on_hand > ss) & (on_hand <= rop)]                = "WARNING"
        status[on_hand > rop * 4]                                = "OVERSTOCKED"

        df = pd.DataFrame({
            "snapshot_date": day,
            "store_id":      store_grid,
            "sku_id":        sku_grid,
            "on_hand":       on_hand,
            "on_order":      on_order,
            "reorder_point": rop,
            "safety_stock":  ss,
            "days_of_cover": np.round(cover, 2).astype(np.float32),
            "status":        status,
        })
        # Inject ~0.3% missing on_order values to mimic ERP drift
        n_missing = int(len(df) * 0.003)
        if n_missing:
            idx = np.random.default_rng().choice(len(df), size=n_missing, replace=False)
            df.loc[idx, "on_order"] = np.nan
        return df

    # ── Writer (month partition) ────────────────────────────
    @staticmethod
    def write_partition(frames: list[pd.DataFrame], out_dir: Path,
                        year: int, month: int) -> Path:
        partition = out_dir / f"year={year}" / f"month={month:02d}"
        partition.mkdir(parents=True, exist_ok=True)
        out = partition / "inventory_snapshots.parquet"
        pd.concat(frames, ignore_index=True).to_parquet(out, index=False, compression="zstd")
        return out
