"""
Rupture scenario injector — dados sintéticos com padrões causais R1–R5.

Cada cohort recebe assinatura operacional distinta para treinar e demonstrar
os modelos preditivos de ruptura.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum

import numpy as np


class RuptureType(str, Enum):
    R1 = "R1"  # Quebra de inventário
    R2 = "R2"  # Venda acima da média
    R3 = "R3"  # Promoção não sinalizada
    R4 = "R4"  # Lead time / entrega
    R5 = "R5"  # Restrição faturamento fornecedor


@dataclass
class RuptureCohort:
    rupture: RuptureType
    sku_ids: list[str] = field(default_factory=list)
    store_ids: list[str] = field(default_factory=list)
    supplier_ids: list[str] = field(default_factory=list)


@dataclass
class RupturePlan:
    """Mapa de cohorts por tipo de ruptura."""
    cohorts: dict[RuptureType, RuptureCohort]
    baseline_sku_ids: list[str] = field(default_factory=list)

    def skus_for(self, r: RuptureType) -> set[str]:
        return set(self.cohorts[r].sku_ids)

    def stores_for(self, r: RuptureType) -> set[str]:
        return set(self.cohorts[r].store_ids)


def assign_cohorts(
    sku_ids: list[str],
    store_ids: list[str],
    supplier_ids: list[str],
    *,
    rng: np.random.Generator,
    pct_per_rupture: float = 0.08,
) -> RupturePlan:
    """Divide SKUs em cohorts não sobrepostas (~8% cada ruptura)."""
    n = len(sku_ids)
    chunk = max(3, int(n * pct_per_rupture))
    shuffled = list(sku_ids)
    rng.shuffle(shuffled)

    slices = {
        RuptureType.R1: shuffled[0:chunk],
        RuptureType.R2: shuffled[chunk: chunk * 2],
        RuptureType.R3: shuffled[chunk * 2: chunk * 3],
        RuptureType.R4: shuffled[chunk * 3: chunk * 4],
        RuptureType.R5: shuffled[chunk * 4: chunk * 5],
    }
    baseline = shuffled[chunk * 5:]

    # R4/R5 ligados a fornecedores com perfil de risco
    r4_sup = supplier_ids[-2] if len(supplier_ids) >= 2 else supplier_ids[0]
    r5_sup = supplier_ids[-1] if supplier_ids else "SUP-001"
    primary_store = store_ids[0] if store_ids else "ST-001"
    spike_stores = store_ids[: min(3, len(store_ids))]

    cohorts: dict[RuptureType, RuptureCohort] = {}
    for rtype, skus in slices.items():
        stores = spike_stores if rtype == RuptureType.R2 else [primary_store]
        if rtype in (RuptureType.R4, RuptureType.R5):
            stores = store_ids
        sups = []
        if rtype == RuptureType.R4:
            sups = [r4_sup]
        elif rtype == RuptureType.R5:
            sups = [r5_sup]
        cohorts[rtype] = RuptureCohort(
            rupture=rtype, sku_ids=skus, store_ids=stores, supplier_ids=sups,
        )

    return RupturePlan(cohorts=cohorts, baseline_sku_ids=baseline)


# ── R1 · Quebra de inventário ─────────────────────────────────────────────
def r1_inventory_drift(
    on_hand: int,
    day_idx: int,
    *,
    rng: np.random.Generator,
) -> tuple[int, int]:
    """Retorna (on_hand_sistêmico, ajuste_divergência)."""
    # A cada ~10 dias: grande divergência inventário físico vs sistêmico
    if day_idx % 10 == 7:
        drift = int(rng.integers(8, 25)) * rng.choice([-1, 1])
        return max(-5, on_hand + drift), abs(drift)
    if day_idx % 14 == 3:
        return -int(rng.integers(1, 4)), int(rng.integers(5, 15))  # estoque negativo
    # drift gradual mascarando ruptura
    micro = int(rng.integers(-3, 4))
    return max(0, on_hand + micro), abs(micro)


# ── R2 · Venda acima da média ─────────────────────────────────────────────
def r2_demand_multiplier(day: date, day_idx: int, *, rng: np.random.Generator) -> float:
    """Picos em payday e explosões aleatórias."""
    if day.day in (5, 15, 20, 30):
        return float(rng.uniform(2.2, 3.8))
    if day_idx in (40, 41, 42, 52, 53):
        return float(rng.uniform(2.5, 4.5))  # explosão de vendas
    if day.weekday() >= 5:
        return float(rng.uniform(1.3, 1.8))
    return 1.0


# ── R3 · Promoção não sinalizada ──────────────────────────────────────────
def r3_unsignaled_promo(day_idx: int, *, rng: np.random.Generator) -> tuple[bool, float]:
    """Venda com desconto/promo SEM registro no calendário."""
    if day_idx % 9 in (2, 3, 4):
        return True, float(rng.uniform(0.18, 0.35))
    return False, 0.0


# ── R4 · Lead time ────────────────────────────────────────────────────────
def r4_lead_time_days(base_lt: int, day_idx: int, *, rng: np.random.Generator) -> tuple[int, bool]:
    """Atraso logístico e entrega fora do prazo."""
    if day_idx % 7 in (4, 5, 6):
        delay = int(rng.integers(3, 8))
        return base_lt + delay, False
    if rng.random() < 0.12:
        return base_lt + int(rng.integers(2, 5)), False
    return base_lt, True


# ── R5 · Restrição faturamento ────────────────────────────────────────────
def r5_order_status(day_idx: int, *, rng: np.random.Generator) -> str | None:
    """Pedidos bloqueados / recusados por restrição comercial."""
    if day_idx % 5 == 0:
        return rng.choice(["BLOCKED", "REJECTED"], p=[0.6, 0.4])
    if day_idx % 8 == 1:
        return "BLOCKED"
    if rng.random() < 0.08:
        return rng.choice(["REJECTED", "BLOCKED", "CANCELLED"])
    return None


def build_registered_promotions(
    plan: RupturePlan,
    sku_supplier: dict[str, str],
    store_ids: list[str],
    base: datetime,
    days: int,
    *,
    rng: np.random.Generator,
) -> list[dict]:
    """Promoções REGISTRADAS (R3 cohort excluído — gera uplift não sinalizado)."""
    rows: list[dict] = []
    r3_skus = plan.skus_for(RuptureType.R3)
    pid = 0
    for d in range(0, days, 12):
        for sku in plan.baseline_sku_ids[:20]:
            if sku in r3_skus:
                continue
            for store in store_ids[:2]:
                pid += 1
                start = (base + timedelta(days=d)).date()
                rows.append({
                    "promo_id": f"PR-{pid:06d}",
                    "sku_id": sku,
                    "store_id": store,
                    "start_date": start,
                    "end_date": start + timedelta(days=5),
                    "discount_pct": round(float(rng.uniform(0.10, 0.25)), 3),
                    "expected_lift": round(float(rng.uniform(1.2, 1.8)), 3),
                    "promotion_registered": 1,
                })
    return rows


RUPTURE_EVENT_TYPES = {
    RuptureType.R1: "INVENTORY_BREAK",
    RuptureType.R2: "DEMAND_SPIKE",
    RuptureType.R3: "UNSIGNALED_PROMOTION",
    RuptureType.R4: "LEAD_TIME_DELAY",
    RuptureType.R5: "SUPPLIER_BILLING_BLOCK",
}
