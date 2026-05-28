"""
Supplier generator — 200 vendors with realistic operational profiles.

Each supplier exposes:
  • tier (T1/T2/T3) — drives base OTD and lead-time
  • base_lead_time_days
  • lead_time_std
  • otd_rate
  • disruption_propensity   (per-month probability of a multi-day delay)
  • categories served       (multi-category for distributors)
  • payment_terms_days
  • capacity_units_per_day
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker


CATEGORIES = ("Bebidas", "Hortifruti", "Açougue", "Higiene Pessoal", "Limpeza", "Mercearia")

# Tier profiles: (share, lead_mean, lead_std, otd, disruption_p_month)
TIER_PROFILES = {
    "T1": (0.18, 1.5, 0.40, 0.96, 0.04),
    "T2": (0.52, 3.2, 0.85, 0.92, 0.09),
    "T3": (0.30, 6.5, 1.80, 0.84, 0.18),
}


class SupplierGenerator:
    """Builds the supplier dimension."""

    def __init__(self, *, n: int = 200, seed: int = 23) -> None:
        self.n = n
        self.rng = np.random.default_rng(seed)
        self.fake = Faker("pt_BR")
        Faker.seed(seed)

    def build(self) -> pd.DataFrame:
        rows = []
        tiers = self.rng.choice(
            list(TIER_PROFILES.keys()),
            size=self.n,
            p=[TIER_PROFILES[t][0] for t in TIER_PROFILES],
        )
        for i, tier in enumerate(tiers, start=1):
            _, lead_mu, lead_sd, otd, disrupt_p = TIER_PROFILES[tier]
            n_cats = int(self.rng.integers(1, 4)) if tier != "T1" else 1
            cats = list(self.rng.choice(CATEGORIES, size=n_cats, replace=False))
            rows.append({
                "supplier_id":          f"SUP-{i:04d}",
                "name":                 self.fake.company(),
                "cnpj":                 self.fake.cnpj() if hasattr(self.fake, "cnpj") else f"{self.rng.integers(10**13, 10**14)}",
                "tier":                 tier,
                "country":              self.rng.choice(["BR", "BR", "BR", "BR", "AR", "UY", "CL"],
                                                        p=[0.78, 0.05, 0.05, 0.04, 0.04, 0.02, 0.02]),
                "base_lead_time_days":  float(max(0.5, self.rng.normal(lead_mu, 0.3))),
                "lead_time_std":        float(lead_sd),
                "otd_rate":             float(np.clip(self.rng.normal(otd, 0.04), 0.50, 0.99)),
                "disruption_p_month":   float(disrupt_p),
                "capacity_units_day":   int(self.rng.integers(800, 12_000)),
                "payment_terms_days":   int(self.rng.choice([14, 21, 28, 30, 45, 60])),
                "categories":           "|".join(cats),
                "primary_category":     cats[0],
                "rating":               float(np.clip(self.rng.normal(4.0 - (0 if tier == "T1" else 0.5), 0.5), 1.0, 5.0)),
                "active":               bool(self.rng.random() > 0.04),
            })
        return pd.DataFrame(rows)

    def write(self, df: pd.DataFrame, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "suppliers.parquet"
        df.to_parquet(path, index=False, compression="zstd")
        return path
