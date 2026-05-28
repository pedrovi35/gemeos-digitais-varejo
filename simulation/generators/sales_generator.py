"""
Sales generator — vectorized daily demand realization.

For each simulated day we:
  1. Compute λ(store, sku, day) = base × seasonality × payday × holiday
     × weather × growth × promo_lift
  2. Sample demand ~ Poisson(λ)  → desired units
  3. Clip to on_hand              → realized units (the gap is lost-sales)
  4. Build the sales row chunk (only rows with realized > 0)
  5. Return realized matrix to update inventory

The output schema mimics a POS transaction stream but aggregated to
(date, store, sku) tickets — millions of rows over a year.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from simulation.generators.seasonality import SeasonalityEngine


class SalesGenerator:

    def __init__(self, *, seasonality: SeasonalityEngine, anchor: date,
                 seed: int = 53) -> None:
        self.seasonality = seasonality
        self.anchor = anchor
        self.rng = np.random.default_rng(seed)

    # ── Day step ────────────────────────────────────────────
    def daily_lambda(self, day: date, skus: pd.DataFrame, n_stores: int,
                     active_promo_mask: np.ndarray | None = None,
                     active_promo_lift: np.ndarray | None = None) -> np.ndarray:
        """Return λ matrix of shape (n_stores, n_skus)."""
        base = skus["base_daily_rate"].to_numpy(dtype=np.float32)             # (n_skus,)
        cats = skus["category"].to_numpy()

        # Per-category multiplier
        cat_mult = np.array([
            self.seasonality.category_factor(c, day) for c in cats
        ], dtype=np.float32)
        weather = np.array([
            self.seasonality.weather_factor(day, c) for c in cats
        ], dtype=np.float32)

        global_mult = (
            self.seasonality.dow_factor(day)
            * self.seasonality.month_factor(day)
            * self.seasonality.payday_factor(day)
            * self.seasonality.holiday_factor(day)
            * self.seasonality.growth_factor(day, self.anchor)
        )

        per_sku = base * cat_mult * weather * global_mult                     # (n_skus,)

        # Per-store random multiplier (size, region, format)
        store_mult = self.rng.uniform(0.75, 1.30, size=n_stores).astype(np.float32)
        lam = np.outer(store_mult, per_sku)                                   # (n_stores, n_skus)

        # Promo lift
        if active_promo_mask is not None and active_promo_lift is not None:
            lam = np.where(active_promo_mask, lam * active_promo_lift, lam)

        # Slight noise (daily jitter) and clip
        lam *= self.rng.uniform(0.92, 1.08, size=lam.shape).astype(np.float32)
        return np.maximum(0.0, lam)

    def sample_demand(self, lam: np.ndarray) -> np.ndarray:
        return self.rng.poisson(lam).astype(np.int32)

    # ── Build sales rows for the day ────────────────────────
    def to_rows(self, day: date, store_ids: np.ndarray, sku_ids: np.ndarray,
                realized: np.ndarray, unit_price: np.ndarray,
                promo_mask: np.ndarray, discount: np.ndarray) -> pd.DataFrame:
        nz = np.argwhere(realized > 0)
        if nz.size == 0:
            return pd.DataFrame()
        s_idx = nz[:, 0]; k_idx = nz[:, 1]
        qty   = realized[s_idx, k_idx]
        price = unit_price[k_idx]
        promo = promo_mask[s_idx, k_idx]
        disc  = discount[s_idx, k_idx]
        effective_price = np.where(promo, price * (1 - disc), price)
        revenue = qty * effective_price

        # Realistic transaction timestamps within the day, weighted by hour curve
        from simulation.generators.seasonality import DOW_MULTIPLIER  # noqa
        hour_curve = np.array([
            0.005,0.003,0.002,0.002,0.003,0.008,0.022,0.041,0.060,0.072,
            0.078,0.078,0.072,0.062,0.054,0.058,0.068,0.080,0.082,0.068,
            0.046,0.025,0.011,0.005,
        ])
        hours = self.rng.choice(24, size=qty.size, p=hour_curve)
        minutes = self.rng.integers(0, 60, size=qty.size)
        seconds = self.rng.integers(0, 60, size=qty.size)
        ts = np.array([
            datetime(day.year, day.month, day.day, int(h), int(m), int(s))
            for h, m, s in zip(hours, minutes, seconds, strict=True)
        ])

        df = pd.DataFrame({
            "sale_ts":        ts,
            "sale_date":      day,
            "store_id":       store_ids[s_idx],
            "sku_id":         sku_ids[k_idx],
            "quantity":       qty,
            "unit_price":     np.round(price.astype(np.float32), 2),
            "effective_price":np.round(effective_price.astype(np.float32), 2),
            "revenue":        np.round(revenue.astype(np.float32), 2),
            "discount_pct":   np.round(np.where(promo, disc, 0.0).astype(np.float32), 3),
            "promo_flag":     promo,
            "channel":        np.where(self.rng.random(qty.size) < 0.06, "APP", "LOJA"),
        })
        # Inject ~0.05% suspicious negatives (returns) — operational realism
        n_returns = max(0, int(len(df) * 0.0005))
        if n_returns:
            idx = self.rng.choice(len(df), size=n_returns, replace=False)
            df.loc[idx, "quantity"] = -df.loc[idx, "quantity"]
            df.loc[idx, "revenue"]  = -df.loc[idx, "revenue"]
        return df

    # ── Writer (month partition) ────────────────────────────
    @staticmethod
    def write_partition(frames: list[pd.DataFrame], out_dir: Path,
                        year: int, month: int) -> Path | None:
        if not frames:
            return None
        partition = out_dir / f"year={year}" / f"month={month:02d}"
        partition.mkdir(parents=True, exist_ok=True)
        out = partition / "sales.parquet"
        pd.concat(frames, ignore_index=True).to_parquet(out, index=False, compression="zstd")
        return out
