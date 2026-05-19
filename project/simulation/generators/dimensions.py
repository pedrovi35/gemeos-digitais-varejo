"""
Dimensional generator — stores, SKUs, calendar.

Output dataframes live in silver/dim_*.parquet.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker


REGIONS = ("SP-Capital", "SP-Interior", "SP-Litoral", "RJ-Capital", "MG-BH", "PR-Curitiba")
FORMATS = ("Hyper", "Standard", "Premium", "Compact", "Express")
CATEGORIES = ("Bebidas", "Hortifruti", "Açougue", "Higiene Pessoal", "Limpeza", "Mercearia")

SUBCATEGORIES = {
    "Bebidas":         ("Cerveja", "Refrigerante", "Suco", "Água", "Vinho", "Destilado", "Energético"),
    "Hortifruti":      ("Frutas", "Verduras", "Legumes", "Tubérculos", "Ervas"),
    "Açougue":         ("Bovino", "Suíno", "Aves", "Peixes", "Embutidos"),
    "Higiene Pessoal": ("Sabonete", "Shampoo", "Pasta", "Desodorante", "Absorvente", "Fraldas"),
    "Limpeza":         ("Detergente", "Sabão", "Amaciante", "Desinfetante", "Limpa-vidros"),
    "Mercearia":       ("Arroz", "Feijão", "Massa", "Óleo", "Açúcar", "Café", "Enlatados", "Biscoito"),
}

VELOCITY_DIST = (("A", 0.20, 2.5), ("B", 0.50, 1.0), ("C", 0.30, 0.30))


class DimensionGenerator:
    def __init__(self, *, n_stores: int = 20, n_skus: int = 3000, seed: int = 11) -> None:
        self.n_stores = n_stores
        self.n_skus = n_skus
        self.rng = np.random.default_rng(seed)
        self.fake = Faker("pt_BR")
        Faker.seed(seed)

    # ── Stores ──────────────────────────────────────────────
    def build_stores(self) -> pd.DataFrame:
        rows = []
        for i in range(1, self.n_stores + 1):
            region = self.rng.choice(REGIONS, p=[0.30, 0.18, 0.10, 0.18, 0.14, 0.10])
            fmt = self.rng.choice(FORMATS, p=[0.10, 0.50, 0.15, 0.18, 0.07])
            sqm_by_format = {"Hyper": 5800, "Standard": 2200, "Premium": 1800,
                             "Compact": 1100, "Express": 450}
            sqm = int(self.rng.normal(sqm_by_format[fmt], sqm_by_format[fmt] * 0.12))
            rows.append({
                "store_id":   f"ST-{i:03d}",
                "name":       self.fake.city() + " " + self.rng.choice(["Centro", "Shopping",
                                                                        "Norte", "Sul", "Oeste"]),
                "region":     region,
                "state":      region.split("-")[0],
                "format":     fmt,
                "sqm":        max(300, sqm),
                "checkouts":  int(self.rng.integers(4, 28)),
                "headcount":  int(self.rng.integers(18, 180)),
                "opened_at":  self.fake.date_between(start_date="-10y", end_date="-1y"),
                "lat":        float(self.rng.uniform(-25.5, -19.5)),
                "lon":        float(self.rng.uniform(-48.5, -42.5)),
                "is_active":  True,
            })
        return pd.DataFrame(rows)

    # ── SKUs ────────────────────────────────────────────────
    def build_skus(self, suppliers: pd.DataFrame) -> pd.DataFrame:
        rows: list[dict] = []
        # Distribute SKUs across categories with retail-like weights
        cat_weights = np.array([0.18, 0.14, 0.10, 0.14, 0.12, 0.32])
        cat_counts = (cat_weights / cat_weights.sum() * self.n_skus).astype(int)
        cat_counts[-1] += self.n_skus - cat_counts.sum()

        velocity_pool = np.concatenate([
            np.full(int(self.n_skus * share), code, dtype=object)
            for code, share, _ in VELOCITY_DIST
        ])
        # Pad to exact length
        if len(velocity_pool) < self.n_skus:
            velocity_pool = np.concatenate([velocity_pool, np.full(self.n_skus - len(velocity_pool), "B", dtype=object)])
        self.rng.shuffle(velocity_pool)

        sku_idx = 0
        for cat, n_cat in zip(CATEGORIES, cat_counts, strict=True):
            subcats = SUBCATEGORIES[cat]
            cat_suppliers = suppliers[
                suppliers["categories"].str.contains(cat, regex=False)
            ]["supplier_id"].tolist() or suppliers["supplier_id"].tolist()
            for _ in range(int(n_cat)):
                sku_idx += 1
                sub = self.rng.choice(subcats)
                velocity = velocity_pool[sku_idx - 1]
                base_rate_mult = next(m for c, _, m in VELOCITY_DIST if c == velocity)
                cost = round(float(self.rng.uniform(1.20, 95.0)), 2)
                margin = float(self.rng.uniform(0.22, 0.55))
                price = round(cost * (1 + margin), 2)
                shelf_life = int(self.rng.choice([3, 5, 7, 14, 30, 60, 90, 180, 365],
                                                 p=[0.05, 0.08, 0.10, 0.12, 0.15, 0.13, 0.12, 0.13, 0.12]))
                rows.append({
                    "sku_id":          f"SKU-{sku_idx:05d}",
                    "ean":             f"789{self.rng.integers(10**9, 10**10)}",
                    "description":     f"{sub} {self.fake.word().capitalize()} {self.rng.integers(50, 999)}g",
                    "category":        cat,
                    "subcategory":     sub,
                    "brand":           self.rng.choice(
                        ["Premium", "Líder", "Marca Própria", "Econômica", "Importada", "Artesanal"],
                        p=[0.10, 0.30, 0.20, 0.20, 0.10, 0.10],
                    ),
                    "unit":            self.rng.choice(["UN", "KG", "L", "PCT", "CX"],
                                                       p=[0.55, 0.15, 0.10, 0.15, 0.05]),
                    "pack_size":       int(self.rng.choice([1, 6, 12, 24])),
                    "velocity_class":  velocity,
                    "base_daily_rate": round(float(base_rate_mult * self.rng.uniform(2.5, 8.0)), 3),
                    "elasticity":      round(float(-self.rng.uniform(0.8, 2.4)), 3),
                    "unit_cost":       cost,
                    "unit_price":      price,
                    "shelf_life_days": shelf_life,
                    "supplier_id":     self.rng.choice(cat_suppliers),
                    "min_pack_buy":    int(self.rng.choice([1, 6, 12, 24, 48])),
                    "is_active":       bool(self.rng.random() > 0.02),
                })
        return pd.DataFrame(rows)

    # ── Calendar ────────────────────────────────────────────
    @staticmethod
    def build_calendar(start: date, end: date) -> pd.DataFrame:
        from simulation.generators.seasonality import BR_HOLIDAYS
        days = (end - start).days + 1
        rows = []
        for i in range(days):
            d = start + timedelta(days=i)
            rows.append({
                "date":        d,
                "dow":         d.weekday(),
                "is_weekend":  d.weekday() >= 5,
                "is_holiday":  d in BR_HOLIDAYS,
                "month":       d.month,
                "quarter":     (d.month - 1) // 3 + 1,
                "year":        d.year,
                "iso_week":    d.isocalendar().week,
                "is_payday":   d.day in (5, 15, 20, 30),
            })
        return pd.DataFrame(rows)

    # ── Persistence ─────────────────────────────────────────
    @staticmethod
    def write(df: pd.DataFrame, out_dir: Path, name: str) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{name}.parquet"
        df.to_parquet(path, index=False, compression="zstd")
        return path
