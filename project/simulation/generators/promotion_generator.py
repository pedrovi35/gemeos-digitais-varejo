"""
Promotion generator — promo calendar with realistic cadence.

Promos are SKU × store × date-range entries with:
  • discount_pct (0.05 → 0.40)
  • mechanism (LINEAR, TAB_VIP, COMBO, LEVE3_PAGUE2)
  • expected_lift (computed from elasticity)

A SKU's promo footprint follows:
  • A-class SKUs run more & deeper promos
  • category-anchored seasonal pushes (e.g. cerveja em Nov/Dec)
  • Black-Friday & natal blocks across many SKUs simultaneously
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


MECHANISMS = ("LINEAR", "TAB_VIP", "COMBO", "LEVE3_PAGUE2", "EXTRA_FIDELIDADE")
MECH_WEIGHTS = (0.45, 0.20, 0.12, 0.13, 0.10)


class PromotionGenerator:

    def __init__(self, *, seed: int = 31) -> None:
        self.rng = np.random.default_rng(seed)

    def build(self, skus: pd.DataFrame, stores: pd.DataFrame,
              start: date, end: date) -> pd.DataFrame:
        store_ids = stores["store_id"].to_numpy()
        rows: list[dict] = []
        promo_counter = 0

        # ── Per-SKU regular promo cadence ───────────────────
        for _, sku in skus.iterrows():
            velocity = sku["velocity_class"]
            n_promos_per_year = {"A": 14, "B": 7, "C": 3}[velocity]
            horizon_days = (end - start).days
            n_promos = int(n_promos_per_year * horizon_days / 365)
            if n_promos == 0:
                continue
            offsets = sorted(self.rng.choice(horizon_days - 14, size=n_promos, replace=False))
            for off in offsets:
                p_start = start + timedelta(days=int(off))
                p_dur = int(self.rng.choice([3, 4, 5, 7, 10, 14],
                                            p=[0.15, 0.20, 0.20, 0.20, 0.15, 0.10]))
                p_end = p_start + timedelta(days=p_dur)
                discount = float(np.clip(self.rng.normal(0.18 if velocity == "A" else 0.12, 0.06),
                                         0.05, 0.45))
                mech = self.rng.choice(MECHANISMS, p=MECH_WEIGHTS)
                lift = float(np.clip((discount * abs(sku["elasticity"]) * self.rng.uniform(0.8, 1.2)) + 1, 1.05, 3.5))
                # Some promos national, some regional
                target_stores = (store_ids if self.rng.random() < 0.6
                                 else self.rng.choice(store_ids, size=int(len(store_ids) * 0.5), replace=False))
                for st in target_stores:
                    promo_counter += 1
                    rows.append({
                        "promo_id":     f"PR-{promo_counter:07d}",
                        "sku_id":       sku["sku_id"],
                        "store_id":     st,
                        "start_date":   p_start,
                        "end_date":     p_end,
                        "discount_pct": round(discount, 3),
                        "mechanism":    mech,
                        "expected_lift": round(lift, 3),
                        "category":     sku["category"],
                        "channel":      self.rng.choice(["TAB", "ENCARTE", "DIGITAL", "GONDOLA"]),
                        "scope":        "NATIONAL" if len(target_stores) == len(store_ids) else "REGIONAL",
                    })

        # ── Black-Friday block (last Friday of November) ────
        rows += self._block_event(skus, stores, "BLACK_FRIDAY",
                                  anchor=lambda y: date(y, 11, 24),
                                  duration=7, discount=(0.20, 0.40),
                                  start=start, end=end, share_skus=0.40)
        # ── Natal block ─────────────────────────────────────
        rows += self._block_event(skus, stores, "NATAL",
                                  anchor=lambda y: date(y, 12, 10),
                                  duration=15, discount=(0.10, 0.25),
                                  start=start, end=end, share_skus=0.55)

        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values(["start_date", "sku_id"]).reset_index(drop=True)
            df["promo_id"] = [f"PR-{i+1:07d}" for i in range(len(df))]
        return df

    def _block_event(self, skus, stores, code, *, anchor, duration,
                     discount, start, end, share_skus) -> list[dict]:
        store_ids = stores["store_id"].to_numpy()
        rows = []
        years = range(start.year, end.year + 1)
        for y in years:
            try:
                a = anchor(y)
            except ValueError:
                continue
            if not (start <= a <= end):
                continue
            chosen = skus.sample(frac=share_skus, random_state=int(self.rng.integers(0, 10**6)))
            for _, sku in chosen.iterrows():
                d = float(self.rng.uniform(*discount))
                lift = float(np.clip(d * abs(sku["elasticity"]) * 1.3 + 1.2, 1.3, 4.0))
                for st in store_ids:
                    rows.append({
                        "promo_id":     None,
                        "sku_id":       sku["sku_id"],
                        "store_id":     st,
                        "start_date":   a,
                        "end_date":     a + timedelta(days=duration),
                        "discount_pct": round(d, 3),
                        "mechanism":    "LINEAR" if code == "NATAL" else "TAB_VIP",
                        "expected_lift": round(lift, 3),
                        "category":     sku["category"],
                        "channel":      "ENCARTE",
                        "scope":        f"EVENT::{code}",
                    })
        return rows

    @staticmethod
    def write(df: pd.DataFrame, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "promotions.parquet"
        df.to_parquet(path, index=False, compression="zstd")
        return path
