"""
Synthetic data seeder com cenários causais R1–R5.

Gera histórico operacional de 60 dias com assinaturas distintas por ruptura
para alimentar feature engineering e modelos preditivos.
"""
from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from config.constants import CATEGORIES, DEFAULT_STORES, StockStatus
from config.logging import logger
from config.settings import settings
from database.connection import get_connection
from simulation.generators.rupture_scenarios import (
    RupturePlan,
    RuptureType,
    assign_cohorts,
    build_registered_promotions,
    r1_inventory_drift,
    r2_demand_multiplier,
    r3_unsignaled_promo,
    r4_lead_time_days,
    r5_order_status,
    RUPTURE_EVENT_TYPES,
)
from utils.time_utils import now_tz


RNG = np.random.default_rng(seed=42)
random.seed(42)


def _seed_profile() -> dict:
    """Light profile for Streamlit Cloud; full profile for local/dev."""
    if settings.twin.light_seed:
        return {
            "history_days": min(settings.twin.seed_history_days, 21),
            "n_skus": min(settings.twin.seed_n_skus, 96),
            "inventory_stride": 3,
        }
    return {
        "history_days": settings.twin.seed_history_days,
        "n_skus": settings.twin.seed_n_skus,
        "inventory_stride": 1,
    }


def _seed_stores(conn) -> None:
    rows = [
        (s["store_id"], s["name"], s["region"], s["format"],
         (now_tz().date() - timedelta(days=random.randint(400, 2000))),
         random.randint(800, 2500), True)
        for s in DEFAULT_STORES
    ]
    conn.executemany("INSERT INTO dim_store VALUES (?, ?, ?, ?, ?, ?, ?);", rows)


def _seed_suppliers(conn) -> list[str]:
    suppliers = [
        ("SUP-001", "Cooperativa Hortifruti SP",     "T1", 1, 0.94, "BR"),
        ("SUP-002", "Frigorífico Sul",               "T1", 2, 0.91, "BR"),
        ("SUP-003", "Distribuidora Mercearia Ltda",  "T2", 3, 0.96, "BR"),
        ("SUP-004", "Bebidas Premium Brasil",        "T2", 4, 0.93, "BR"),
        ("SUP-005", "Higiene & Limpeza Nacional",    "T2", 5, 0.97, "BR"),
        ("SUP-006", "Padaria Industrial Pão & Cia",  "T1", 1, 0.89, "BR"),
        ("SUP-007", "Frios Importados · Restrição",  "T3", 7, 0.72, "BR"),  # R5
    ]
    conn.executemany("INSERT INTO dim_supplier VALUES (?, ?, ?, ?, ?, ?);", suppliers)
    return [s[0] for s in suppliers]


def _seed_skus(conn, plan: RupturePlan, n: int = 240) -> tuple[list[str], dict[str, str]]:
    suppliers = [r[0] for r in conn.execute("SELECT supplier_id FROM dim_supplier;").fetchall()]
    r4_sup = plan.cohorts[RuptureType.R4].supplier_ids[0] if plan.cohorts[RuptureType.R4].supplier_ids else suppliers[0]
    r5_sup = plan.cohorts[RuptureType.R5].supplier_ids[0] if plan.cohorts[RuptureType.R5].supplier_ids else "SUP-007"

    velocities = ["A"] * int(n * 0.2) + ["B"] * int(n * 0.5) + ["C"] * int(n * 0.3)
    rows, ids, sku_supplier = [], [], {}

    for i in range(n):
        sku_id = f"SKU-{i+1:05d}"
        ids.append(sku_id)
        cat = random.choice(CATEGORIES)
        cost = round(RNG.uniform(1.5, 80.0), 2)
        price = round(cost * RNG.uniform(1.25, 2.10), 2)

        if sku_id in plan.skus_for(RuptureType.R4):
            sup = r4_sup
        elif sku_id in plan.skus_for(RuptureType.R5):
            sup = r5_sup
        else:
            sup = random.choice(suppliers[:6])

        sku_supplier[sku_id] = sup
        rows.append((
            sku_id, f"789{RNG.integers(10**9, 10**10)}",
            f"{cat} • Produto {i+1:03d}", cat, None,
            random.choice(["Marca A", "Marca B", "Própria", "Premium"]),
            "UN", random.choice(velocities), cost, price,
            random.choice([3, 7, 14, 30, 90, 180, 365]),
            sup,
        ))
    conn.executemany(
        "INSERT INTO dim_sku VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", rows,
    )
    return ids, sku_supplier


def _seed_calendar(conn, days: int = 60) -> None:
    today = now_tz().date()
    rows = []
    for delta in range(-days, days + 1):
        d = today + timedelta(days=delta)
        rows.append((d, d.weekday(), d.weekday() >= 5, False,
                     ("Verão" if d.month in (12, 1, 2) else
                      "Outono" if d.month in (3, 4, 5) else
                      "Inverno" if d.month in (6, 7, 8) else "Primavera")))
    conn.executemany("INSERT INTO dim_calendar VALUES (?, ?, ?, ?, ?);", rows)


def _write_promotions_parquet(promos: list[dict]) -> None:
    if not promos:
        return
    out = settings.lake.bronze / "promotions"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(promos).to_parquet(out / "promotions.parquet", index=False, compression="zstd")
    logger.info(f"bronze promotions written · {len(promos)} rows → {out}")


def _seed_inventory_history(
    conn, sku_ids: list[str], plan: RupturePlan, days: int, *, stride: int = 1,
) -> None:
    """Snapshots diários com padrões R1 (divergência) e R4 (baixa cobertura)."""
    base = now_tz() - timedelta(days=days)
    r1_skus = plan.skus_for(RuptureType.R1)
    r4_skus = plan.skus_for(RuptureType.R4)
    rows = []

    for day_idx in range(0, days, max(1, stride)):
        snap_ts = base + timedelta(days=day_idx, hours=23)
        for store in DEFAULT_STORES:
            for sku in sku_ids:
                on_hand = int(max(0, RNG.normal(80, 35)))
                reorder = int(RNG.integers(20, 50))
                safety = int(reorder * 0.4)
                daily = max(1.0, RNG.normal(8, 3))
                on_order = int(RNG.integers(0, 30))

                if sku in r1_skus and store["store_id"] in plan.stores_for(RuptureType.R1):
                    on_hand, _adj = r1_inventory_drift(on_hand, day_idx, rng=RNG)

                if sku in r4_skus and day_idx >= days - 14:
                    on_hand = int(on_hand * RNG.uniform(0.15, 0.45))
                    on_order = int(RNG.integers(40, 120))

                cover = on_hand / daily if on_hand > 0 else 0.0
                if on_hand <= 0:
                    status = StockStatus.STOCKOUT
                elif on_hand <= safety:
                    status = StockStatus.CRITICAL
                elif on_hand <= reorder:
                    status = StockStatus.WARNING
                elif on_hand > reorder * 4:
                    status = StockStatus.OVERSTOCKED
                else:
                    status = StockStatus.HEALTHY

                rows.append((
                    snap_ts, store["store_id"], sku, int(on_hand),
                    int(on_order), 0, int(reorder), int(safety),
                    float(round(max(0, cover), 2)), status.value,
                ))

    conn.executemany(
        "INSERT INTO fct_inventory_snapshot VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
        rows,
    )
    logger.info(f"inventory snapshots · {len(rows):,} rows ({days}d × stores × skus)")


def _seed_sales_history(
    conn, sku_ids: list[str], plan: RupturePlan, days: int = 60,
) -> None:
    """Vendas com R2 (picos), R3 (promo não sinalizada) e baseline."""
    base = now_tz() - timedelta(days=days)
    sku_prices = dict(conn.execute("SELECT sku_id, unit_price FROM dim_sku;").fetchall())
    r2_skus = plan.skus_for(RuptureType.R2)
    r3_skus = plan.skus_for(RuptureType.R3)
    rows = []

    for day_idx in range(days):
        d = (base + timedelta(days=day_idx)).date()
        for store in DEFAULT_STORES:
            n_events = int(RNG.integers(180, 380))
            for _ in range(n_events):
                sku = random.choice(sku_ids)
                qty = int(max(1, RNG.poisson(2)))
                price = sku_prices.get(sku, 5.0)
                promo = False
                effective = price

                if sku in r2_skus and store["store_id"] in plan.stores_for(RuptureType.R2):
                    mult = r2_demand_multiplier(d, day_idx, rng=RNG)
                    qty = int(max(1, qty * mult))

                if sku in r3_skus:
                    unsignaled, disc = r3_unsignaled_promo(day_idx, rng=RNG)
                    if unsignaled:
                        promo = True
                        effective = price * (1 - disc)
                    elif RNG.random() < 0.05:
                        promo = RNG.random() < 0.08
                        effective = price * (0.85 if promo else 1.0)
                else:
                    promo = RNG.random() < 0.08
                    effective = price * (0.85 if promo else 1.0)

                ts = base + timedelta(days=day_idx, minutes=int(RNG.integers(0, 1440)))
                rows.append((ts, store["store_id"], sku, qty, effective, qty * effective, promo))

    conn.executemany(
        "INSERT INTO fct_sales VALUES (?, ?, ?, ?, ?, ?, ?);", rows,
    )
    logger.info(f"sales seeded · {len(rows):,} rows")


def _seed_replenishment(
    conn, sku_ids: list[str], plan: RupturePlan,
    sku_supplier: dict[str, str], days: int = 60,
) -> None:
    """POs com R4 (atraso) e R5 (bloqueio faturamento)."""
    sup_lt = {
        r[0]: (r[1], r[2])
        for r in conn.execute(
            "SELECT supplier_id, lead_time_days, otd_rate FROM dim_supplier;"
        ).fetchall()
    }
    r4_skus = plan.skus_for(RuptureType.R4)
    r5_sup = plan.cohorts[RuptureType.R5].supplier_ids[0] if plan.cohorts[RuptureType.R5].supplier_ids else "SUP-007"
    base = now_tz() - timedelta(days=days)
    rows = []

    for day_idx in range(0, days, 2):
        for store in DEFAULT_STORES:
            batch = RNG.choice(sku_ids, size=min(50, len(sku_ids)), replace=False)
            for sku in batch:
                sup = sku_supplier.get(sku, "SUP-001")
                lt_base = int(sup_lt.get(sup, (3, 0.9))[0]) if sup in sup_lt else 3

                placed = base + timedelta(days=day_idx, hours=int(RNG.integers(6, 18)))
                lt, on_time = r4_lead_time_days(lt_base, day_idx, rng=RNG) if sku in r4_skus else (lt_base, RNG.random() < 0.9)
                expected = placed + timedelta(days=lt)

                blocked = r5_order_status(day_idx, rng=RNG) if sup == r5_sup else None
                if blocked:
                    status = blocked
                    delivered = None
                elif on_time:
                    status = "DELIVERED"
                    delivered = expected + timedelta(days=int(RNG.integers(0, 1)))
                else:
                    status = "DELIVERED"
                    delivered = expected + timedelta(days=int(RNG.integers(2, 6)))

                rows.append((
                    str(uuid.uuid4())[:12].upper(), placed, expected, delivered,
                    store["store_id"], sku, sup,
                    int(RNG.integers(50, 400)), status,
                ))

    conn.executemany(
        "INSERT INTO fct_replenishment VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);", rows,
    )
    logger.info(f"replenishment seeded · {len(rows):,} rows")


def _seed_rupture_events(conn, plan: RupturePlan, days: int = 60) -> None:
    """Ledger operacional com eventos tipados R1–R5."""
    base = now_tz() - timedelta(days=days)
    rows = []

    for rtype, cohort in plan.cohorts.items():
        evt_type = RUPTURE_EVENT_TYPES[rtype]
        for day_idx in range(0, days, 7):
            for sku in cohort.sku_ids[:3]:
                store = cohort.store_ids[0] if cohort.store_ids else DEFAULT_STORES[0]["store_id"]
                ts = base + timedelta(days=day_idx, hours=10)
                payload = json.dumps({
                    "rupture_code": rtype.value,
                    "sku_id": sku,
                    "store_id": store,
                    "severity": "HIGH" if rtype in (RuptureType.R1, RuptureType.R5) else "MEDIUM",
                })
                rows.append((
                    str(uuid.uuid4()), ts, evt_type, store, sku, payload,
                    "HIGH" if rtype.value in ("R1", "R5") else "MEDIUM",
                ))

    conn.executemany(
        "INSERT INTO log_events VALUES (?, ?, ?, ?, ?, ?, ?);", rows,
    )
    logger.info(f"rupture events · {len(rows)} rows")


def _seed_kpi_mart(conn) -> None:
    conn.execute("""
        INSERT INTO mart_kpi_daily
        SELECT
            CAST(s.sale_ts AS DATE) AS snapshot_date,
            s.store_id,
            SUM(s.revenue)                                                   AS revenue,
            SUM(s.quantity)                                                  AS units_sold,
            LEAST(0.08, GREATEST(0.005,
                COUNT(DISTINCT CASE WHEN i.status = 'STOCKOUT'
                    THEN i.sku_id END)::DOUBLE / NULLIF(COUNT(DISTINCT s.sku_id), 0)
            ))                                                               AS stockout_pct,
            0.93 + random() * 0.05                                           AS fill_rate,
            0.94 + random() * 0.04                                           AS service_level,
            0.08 + random() * 0.14                                           AS forecast_mape
        FROM fct_sales s
        LEFT JOIN (
            SELECT store_id, sku_id, status
            FROM fct_inventory_snapshot
            WHERE snapshot_ts >= CURRENT_TIMESTAMP - INTERVAL 7 DAY
        ) i ON s.store_id = i.store_id AND s.sku_id = i.sku_id
        GROUP BY CAST(s.sale_ts AS DATE), s.store_id;
    """)


def _seed_alerts(conn, plan: RupturePlan) -> None:
    ts = now_tz()
    r1 = plan.cohorts[RuptureType.R1]
    r3 = plan.cohorts[RuptureType.R3]
    r5 = plan.cohorts[RuptureType.R5]
    seed_alerts = [
        ("CRITICAL", r1.store_ids[0], r1.sku_ids[0] if r1.sku_ids else None,
         "R1 · Divergência inventário sistêmico vs físico",
         "Estoque negativo detectado em contagem cíclica. Risco de ruptura mascarada."),
        ("HIGH", r3.store_ids[0], r3.sku_ids[0] if r3.sku_ids else None,
         "R3 · Promoção ativa sem sinalização ao abastecimento",
         "Uplift de +180% sem registro no calendário promocional. Revisar forecast."),
        ("HIGH", "ST-002", None,
         "R4 · Atraso logístico fornecedor T2",
         "Lead time médio +5 dias vs planejado. Cobertura < 48h em 23 SKUs."),
        ("CRITICAL", "ST-001", None,
         f"R5 · Restrição faturamento {r5.supplier_ids[0] if r5.supplier_ids else 'SUP-007'}",
         "Pedidos bloqueados por limite de crédito. Impacto em 12 SKUs classe A."),
    ]
    rows = [
        (str(uuid.uuid4()), ts - timedelta(minutes=int(RNG.integers(5, 240))),
         sev, store, sku, title, msg, False, None)
        for sev, store, sku, title, msg in seed_alerts
    ]
    conn.executemany(
        "INSERT INTO log_alerts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);", rows,
    )


def _clear_warehouse(conn) -> None:
    """Remove facts before dimensions (FK-safe order)."""
    for table in (
        "log_events", "log_alerts", "mart_kpi_daily",
        "fct_replenishment", "fct_sales", "fct_inventory_snapshot", "fct_forecast",
        "dim_calendar", "dim_sku", "dim_supplier", "dim_store",
    ):
        conn.execute(f"DELETE FROM {table};")


def seed_warehouse(force: bool = False) -> None:
    """Populate warehouse with R1–R5 causal synthetic history."""
    conn = get_connection()
    existing = conn.execute("SELECT COUNT(*) FROM dim_sku;").fetchone()[0]
    if existing and not force:
        logger.info(f"seed skipped — warehouse already has {existing} SKUs")
        return

    profile = _seed_profile()
    days = profile["history_days"]
    n_skus = profile["n_skus"]
    stride = profile["inventory_stride"]

    logger.info(
        f"seeding warehouse · profile={'light' if settings.twin.light_seed else 'full'} "
        f"· {days}d · {n_skus} SKUs · stride={stride}"
    )
    if force or existing:
        _clear_warehouse(conn)

    store_ids = [s["store_id"] for s in DEFAULT_STORES]

    _seed_stores(conn)
    supplier_ids = _seed_suppliers(conn)

    placeholder_skus = [f"SKU-{i+1:05d}" for i in range(n_skus)]
    plan = assign_cohorts(placeholder_skus, store_ids, supplier_ids, rng=RNG)

    sku_ids, sku_supplier = _seed_skus(conn, plan, n=n_skus)
    plan = assign_cohorts(sku_ids, store_ids, supplier_ids, rng=RNG)

    _seed_calendar(conn, days=days)
    _seed_inventory_history(conn, sku_ids, plan, days=days, stride=stride)
    _seed_sales_history(conn, sku_ids, plan, days=days)

    promos = build_registered_promotions(
        plan, sku_supplier, store_ids,
        now_tz() - timedelta(days=days), days, rng=RNG,
    )
    _write_promotions_parquet(promos)

    _seed_replenishment(conn, sku_ids, plan, sku_supplier, days=days)
    _seed_rupture_events(conn, plan, days=days)
    _seed_kpi_mart(conn)
    _seed_alerts(conn, plan)

    for rtype in RuptureType:
        n = len(plan.cohorts[rtype].sku_ids)
        logger.info(f"  {rtype.value}: {n} SKUs · stores={plan.cohorts[rtype].store_ids[:2]}")

    logger.info("warehouse seed complete · rupture-aware dataset ready")
