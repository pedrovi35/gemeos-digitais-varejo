"""
Retail World Simulator
=======================

The orchestrator. Runs a day-by-day discrete simulation that wires together
demand, inventory, replenishment, supplier behavior, promotions and events
through a single deterministic loop. Writes monthly Parquet partitions to
the bronze layer and rolls up silver/gold marts at the end.

Causal chain modeled every single day:

   PROMOÇÃO  →  ↑ demanda  →  consumo de estoque  →  ROP atingido
            →  emissão de PO  →  janela de lead-time  →  entrega
            →  reposição OU atraso  →  ruptura  →  perda de receita

State is held in NumPy 2-D arrays (n_stores × n_skus) for vectorization.
"""
from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from simulation.generators.dimensions          import DimensionGenerator
from simulation.generators.event_generator     import EventGenerator
from simulation.generators.inventory_generator import InventoryGenerator
from simulation.generators.promotion_generator import PromotionGenerator
from simulation.generators.sales_generator     import SalesGenerator
from simulation.generators.seasonality         import SeasonalityEngine
from simulation.generators.supplier_generator  import SupplierGenerator
from simulation.generators.rupture_scenarios import (
    RuptureType,
    assign_cohorts,
    r1_inventory_drift,
    r2_demand_multiplier,
    r3_unsignaled_promo,
    r5_order_status,
)


# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class WorldConfig:
    start_date:     date = field(default_factory=lambda: date.today() - timedelta(days=365))
    end_date:       date = field(default_factory=lambda: date.today())
    n_stores:       int  = 20
    n_skus:         int  = 3000
    n_suppliers:    int  = 200
    seed:           int  = 7
    bronze_root:    Path = Path("data/bronze")
    silver_root:    Path = Path("data/silver")
    gold_root:      Path = Path("data/gold")
    verbose:        bool = True


@dataclass
class WorldStats:
    days:           int   = 0
    sales_rows:     int   = 0
    snapshot_rows:  int   = 0
    purchase_orders:int   = 0
    deliveries:     int   = 0
    ruptures:       int   = 0
    delays:         int   = 0
    elapsed_s:      float = 0.0


# ─────────────────────────────────────────────────────────────────────────────
class RetailWorldSimulator:

    def __init__(self, config: WorldConfig | None = None) -> None:
        self.cfg = config or WorldConfig()
        self.rng = np.random.default_rng(self.cfg.seed)
        self.season = SeasonalityEngine(seed=self.cfg.seed + 1)
        self.dims_gen     = DimensionGenerator(n_stores=self.cfg.n_stores,
                                               n_skus=self.cfg.n_skus,
                                               seed=self.cfg.seed + 2)
        self.supplier_gen = SupplierGenerator(n=self.cfg.n_suppliers,
                                              seed=self.cfg.seed + 3)
        self.promo_gen    = PromotionGenerator(seed=self.cfg.seed + 4)
        self.inv_gen      = InventoryGenerator(seed=self.cfg.seed + 5)
        self.sales_gen    = SalesGenerator(seasonality=self.season,
                                           anchor=self.cfg.start_date,
                                           seed=self.cfg.seed + 6)
        self.events       = EventGenerator()
        self.stats        = WorldStats()

    # ── Logging ─────────────────────────────────────────────
    def _log(self, msg: str) -> None:
        if self.cfg.verbose:
            print(f"[twin-gen] {msg}")

    # ── Main entrypoint ─────────────────────────────────────
    def run(self) -> WorldStats:
        t0 = time.perf_counter()
        self._log(f"world: {self.cfg.n_stores} stores × {self.cfg.n_skus} SKUs × "
                  f"{(self.cfg.end_date - self.cfg.start_date).days} days")

        # ── 1. Dimensions ───────────────────────────────────
        suppliers = self.supplier_gen.build()
        stores    = self.dims_gen.build_stores()
        skus      = self.dims_gen.build_skus(suppliers)
        calendar  = self.dims_gen.build_calendar(self.cfg.start_date, self.cfg.end_date)
        self._log(f"dims built · suppliers={len(suppliers)} stores={len(stores)} skus={len(skus)}")

        # ── 2. Promotions ───────────────────────────────────
        promos = self.promo_gen.build(skus, stores, self.cfg.start_date, self.cfg.end_date)
        self._log(f"promotions generated · {len(promos):,} rows")

        # ── 3. Persist dimensions (silver) ─────────────────
        silver_dim = self.cfg.silver_root / "dim"
        self.dims_gen.write(stores,    silver_dim, "dim_store")
        self.dims_gen.write(skus,      silver_dim, "dim_sku")
        self.dims_gen.write(calendar,  silver_dim, "dim_calendar")
        self.supplier_gen.write(suppliers, silver_dim)
        self.promo_gen.write(promos,   self.cfg.bronze_root / "promotions")

        # ── 4. Initial inventory state ──────────────────────
        state = self.inv_gen.initial_state(stores, skus)

        # ── 5. Day loop ─────────────────────────────────────
        sales_month_buf:     list[pd.DataFrame] = []
        snapshot_month_buf:  list[pd.DataFrame] = []
        current_month = (self.cfg.start_date.year, self.cfg.start_date.month)

        # Pending deliveries: (arrival_date, store_idx, sku_idx, qty, order_id, supplier_id, on_time, lead)
        pending: list[tuple] = []
        # Rupture streak tracking root cause (last reason a SKU went out)
        last_root_cause = np.empty(state.on_hand.shape, dtype=object)

        # Pre-index promos by (start_date) for O(1) day activation
        promos_by_start = promos.groupby("start_date") if not promos.empty else None
        promos_by_end   = promos.groupby("end_date")   if not promos.empty else None
        # Active promo state arrays
        promo_lift  = np.ones(state.on_hand.shape, dtype=np.float32)
        promo_disc  = np.zeros(state.on_hand.shape, dtype=np.float32)
        promo_mask  = np.zeros(state.on_hand.shape, dtype=bool)

        # Lookup tables
        sku_index = {sid: i for i, sid in enumerate(skus["sku_id"].to_numpy())}
        store_index = {sid: i for i, sid in enumerate(stores["store_id"].to_numpy())}

        # R1–R5 rupture cohorts (causal injection)
        store_id_list = stores["store_id"].tolist()
        supplier_id_list = suppliers["supplier_id"].tolist()
        rupture_plan = assign_cohorts(
            skus["sku_id"].tolist(), store_id_list, supplier_id_list, rng=self.rng,
        )
        r1_ki = [sku_index[s] for s in rupture_plan.skus_for(RuptureType.R1) if s in sku_index]
        r2_ki = [sku_index[s] for s in rupture_plan.skus_for(RuptureType.R2) if s in sku_index]
        r3_ki = [sku_index[s] for s in rupture_plan.skus_for(RuptureType.R3) if s in sku_index]
        r2_si = [store_index[s] for s in rupture_plan.stores_for(RuptureType.R2) if s in store_index]
        r5_sup_ids = set(rupture_plan.cohorts[RuptureType.R5].supplier_ids)
        sku_supplier = skus["supplier_id"].to_numpy()
        sku_price    = skus["unit_price"].to_numpy(dtype=np.float32)
        sku_min_pack = skus["min_pack_buy"].to_numpy(dtype=np.int32)
        supplier_idx = {sid: i for i, sid in enumerate(suppliers["supplier_id"].to_numpy())}
        sup_lead_mu  = suppliers["base_lead_time_days"].to_numpy(dtype=np.float32)
        sup_lead_sd  = suppliers["lead_time_std"].to_numpy(dtype=np.float32)
        sup_otd      = suppliers["otd_rate"].to_numpy(dtype=np.float32)
        sup_disrupt_p_day = suppliers["disruption_p_month"].to_numpy(dtype=np.float32) / 30.0
        supplier_disrupted_until = np.full(len(suppliers), self.cfg.start_date - timedelta(days=1))

        n_days = (self.cfg.end_date - self.cfg.start_date).days + 1
        for day_offset in range(n_days):
            today = self.cfg.start_date + timedelta(days=day_offset)
            day_ts = datetime(today.year, today.month, today.day, 23, 30)

            # 5.1 ── Activate / deactivate promotions
            if promos_by_start is not None and today in promos_by_start.groups:
                for _, p in promos_by_start.get_group(today).iterrows():
                    si = store_index.get(p["store_id"])
                    ki = sku_index.get(p["sku_id"])
                    if si is None or ki is None: continue
                    promo_mask[si, ki] = True
                    promo_lift[si, ki] = float(p["expected_lift"])
                    promo_disc[si, ki] = float(p["discount_pct"])
                    self.events.emit_promo_event(ts=day_ts, kind="START",
                                                 promo_id=p["promo_id"], store_id=p["store_id"],
                                                 sku_id=p["sku_id"])
            if promos_by_end is not None and today in promos_by_end.groups:
                for _, p in promos_by_end.get_group(today).iterrows():
                    si = store_index.get(p["store_id"])
                    ki = sku_index.get(p["sku_id"])
                    if si is None or ki is None: continue
                    promo_mask[si, ki] = False
                    promo_lift[si, ki] = 1.0
                    promo_disc[si, ki] = 0.0
                    self.events.emit_promo_event(ts=day_ts, kind="END",
                                                 promo_id=p["promo_id"], store_id=p["store_id"],
                                                 sku_id=p["sku_id"])

            # 5.2 ── Supplier disruption check (per day, per supplier)
            disrupt_roll = self.rng.random(len(suppliers))
            new_disrupted = (disrupt_roll < sup_disrupt_p_day)
            for si in np.where(new_disrupted)[0]:
                duration = int(self.rng.integers(2, 7))
                supplier_disrupted_until[si] = today + timedelta(days=duration)
                self.events.emit_supplier_delay(
                    ts=day_ts, supplier_id=suppliers.iloc[si]["supplier_id"],
                    delay_days=float(duration),
                    reason=self.rng.choice(["LOGISTICA", "PRODUCAO", "QUALIDADE",
                                            "CLIMATICO", "GREVE", "FATURAMENTO"]),
                )
                self.stats.delays += 1

            # 5.3 ── Process incoming deliveries
            arrived, deferred = [], []
            for entry in pending:
                arr_d, s_i, k_i, qty, oid, sup_id, on_time, lead = entry
                if arr_d <= today:
                    state.on_hand[s_i, k_i] += qty
                    state.on_order[s_i, k_i] = max(0, state.on_order[s_i, k_i] - qty)
                    self.events.emit_delivery(
                        ts=day_ts, order_id=oid, store_id=state.store_ids[s_i],
                        sku_id=state.sku_ids[k_i], supplier_id=sup_id,
                        quantity=qty, on_time=on_time, lead_time_days=lead,
                    )
                    arrived.append(entry)
                    self.stats.deliveries += 1
                else:
                    deferred.append(entry)
            pending = deferred

            # 5.4 ── Demand realization (vectorized)
            lam = self.sales_gen.daily_lambda(
                today, skus, self.cfg.n_stores,
                active_promo_mask=promo_mask, active_promo_lift=promo_lift,
            )
            # R2 · demand spike injection
            if r2_ki and r2_si:
                mult = r2_demand_multiplier(today, day_offset, rng=self.rng)
                lam[np.ix_(r2_si, r2_ki)] *= mult
            # R3 · promo não sinalizada (sem calendário)
            if r3_ki:
                unsig, disc = r3_unsignaled_promo(day_offset, rng=self.rng)
                if unsig:
                    promo_mask[:, r3_ki] = True
                    promo_disc[:, r3_ki] = disc
                    promo_lift[:, r3_ki] = float(self.rng.uniform(1.8, 2.8))
            desired = self.sales_gen.sample_demand(lam)
            realized = np.minimum(desired, np.maximum(0, state.on_hand))
            lost = desired - realized

            # 5.5 ── Update inventory
            state.on_hand = state.on_hand - realized
            # R1 · divergência inventário sistêmico
            if r1_ki and day_offset % 5 == 2:
                for k_i in r1_ki[: min(80, len(r1_ki))]:
                    for s_i in range(self.cfg.n_stores):
                        oh, _ = r1_inventory_drift(int(state.on_hand[s_i, k_i]), day_offset, rng=self.rng)
                        state.on_hand[s_i, k_i] = oh

            # 5.6 ── Rupture detection (newly-zero or already-zero with demand)
            out_mask  = (state.on_hand <= 0)
            had_demand = (desired > 0)
            new_out_today = out_mask & (state.days_out_streak == 0) & had_demand
            still_out     = out_mask & (state.days_out_streak >  0)
            state.days_out_streak = np.where(out_mask, state.days_out_streak + 1, 0).astype(np.int16)

            # Emit a row per (store,sku) that ruptured today with demand
            if new_out_today.any() or (still_out & had_demand).any():
                ruptured = np.argwhere(((new_out_today) | (still_out & had_demand)))
                # Subsample to avoid emitting millions of micro-events
                if len(ruptured) > 4000:
                    pick = self.rng.choice(len(ruptured), size=4000, replace=False)
                    ruptured = ruptured[pick]
                for s_i, k_i in ruptured:
                    streak = int(state.days_out_streak[s_i, k_i])
                    lost_qty = int(lost[s_i, k_i])
                    if lost_qty <= 0:
                        continue
                    # Root cause attribution
                    on_order_here = int(state.on_order[s_i, k_i])
                    sup_id = sku_supplier[k_i]
                    sup_i  = supplier_idx[sup_id]
                    if supplier_disrupted_until[sup_i] >= today:
                        cause = "SUPPLIER_DISRUPTION"
                    elif on_order_here > 0:
                        cause = "LEAD_TIME_GAP"
                    elif promo_mask[s_i, k_i]:
                        cause = "PROMO_UNDERFORECAST"
                    else:
                        cause = "DEMAND_SHOCK"
                    self.events.emit_rupture(
                        ts=day_ts, store_id=state.store_ids[s_i], sku_id=state.sku_ids[k_i],
                        lost_demand=lost_qty,
                        lost_revenue=float(lost_qty) * float(sku_price[k_i]),
                        streak_days=streak, root_cause=cause,
                    )
                    self.stats.ruptures += 1

            # 5.7 ── Reorder logic (vectorized)
            need_order = (state.on_hand + state.on_order) <= state.reorder_point
            # Only trigger for SKUs with non-trivial demand to avoid noise
            need_order &= (lam > 0.2)
            trigger_idx = np.argwhere(need_order)
            # Throttle to avoid explosion — at most 8000 POs/day across network
            if len(trigger_idx) > 8000:
                pick = self.rng.choice(len(trigger_idx), size=8000, replace=False)
                trigger_idx = trigger_idx[pick]

            for s_i, k_i in trigger_idx:
                sup_id = sku_supplier[k_i]
                sup_i  = supplier_idx[sup_id]
                # R5 · bloqueio faturamento
                if sup_id in r5_sup_ids:
                    blocked = r5_order_status(day_offset, rng=self.rng)
                    if blocked:
                        self.events.causal_log.append(
                            event_id=f"EVT-{uuid.uuid4().hex[:10].upper()}",
                            event_ts=day_ts, event_type="SUPPLIER_BILLING_BLOCK",
                            store_id=state.store_ids[s_i], sku_id=state.sku_ids[k_i],
                            severity="CRITICAL", payload_qty=0, supplier_id=sup_id,
                        )
                        continue
                base_qty = int(state.reorder_point[s_i, k_i] * 2.2)
                pack = int(max(1, sku_min_pack[k_i]))
                qty = int(math.ceil(base_qty / pack) * pack)
                # Lead-time sample
                lead = max(0.5, self.rng.normal(sup_lead_mu[sup_i], sup_lead_sd[sup_i]))
                on_time = bool(self.rng.random() < sup_otd[sup_i])
                if not on_time:
                    lead += float(self.rng.uniform(1.0, 4.0))
                if supplier_disrupted_until[sup_i] >= today:
                    lead += float(self.rng.uniform(2.0, 5.0))
                    on_time = False
                arrival = today + timedelta(days=int(round(lead)))
                exp_arrival_dt = datetime(arrival.year, arrival.month, arrival.day, 10, 0)
                oid = self.events.emit_purchase_order(
                    ts=day_ts, store_id=state.store_ids[s_i], sku_id=state.sku_ids[k_i],
                    supplier_id=sup_id, quantity=qty,
                    expected_arrival=exp_arrival_dt,
                    trigger="ROP_HIT",
                )
                state.on_order[s_i, k_i] += qty
                pending.append((arrival, s_i, k_i, qty, oid, sup_id, on_time, lead))
                self.stats.purchase_orders += 1

            # 5.8 ── Persist daily sales rows (only this day's rows; aggregate at month-flush)
            sales_df = self.sales_gen.to_rows(
                today, state.store_ids, state.sku_ids, realized,
                sku_price, promo_mask, promo_disc,
            )
            if not sales_df.empty:
                sales_month_buf.append(sales_df)
                self.stats.sales_rows += len(sales_df)

            # 5.9 ── Snapshot inventory (daily)
            snap = self.inv_gen.snapshot(state, today, daily_demand_estimate=lam)
            snapshot_month_buf.append(snap)
            self.stats.snapshot_rows += len(snap)

            # 5.10 ── Month rollover: flush partitions
            next_day = today + timedelta(days=1)
            month_changed = (next_day.year, next_day.month) != current_month or day_offset == n_days - 1
            if month_changed:
                y, m = current_month
                self.sales_gen.write_partition(sales_month_buf, self.cfg.bronze_root / "sales", y, m)
                self.inv_gen.write_partition(snapshot_month_buf,
                                             self.cfg.bronze_root / "inventory_snapshots", y, m)
                self.events.flush_all(self.cfg.bronze_root, y, m)
                self._log(
                    f"{y}-{m:02d} flushed · sales={sum(len(d) for d in sales_month_buf):,} "
                    f"snapshots={sum(len(d) for d in snapshot_month_buf):,} "
                    f"PO={self.stats.purchase_orders:,} "
                    f"RUP={self.stats.ruptures:,}"
                )
                sales_month_buf.clear()
                snapshot_month_buf.clear()
                current_month = (next_day.year, next_day.month)

            self.stats.days += 1

        # ── 6. Silver/Gold rollups ──────────────────────────
        self._build_silver_and_gold()

        self.stats.elapsed_s = time.perf_counter() - t0
        self._log(
            f"DONE · {self.stats.days}d · "
            f"sales={self.stats.sales_rows:,} · snapshots={self.stats.snapshot_rows:,} · "
            f"PO={self.stats.purchase_orders:,} · ruptures={self.stats.ruptures:,} · "
            f"delays={self.stats.delays:,} · {self.stats.elapsed_s:.1f}s"
        )
        return self.stats

    # ── 6. Silver & Gold rollups (DuckDB-friendly aggregates) ─────────────
    def _build_silver_and_gold(self) -> None:
        try:
            import duckdb
        except ImportError:                                    # pragma: no cover
            self._log("duckdb not available — skipping silver/gold rollups")
            return

        bronze = self.cfg.bronze_root.as_posix()
        silver = self.cfg.silver_root
        gold   = self.cfg.gold_root
        silver.mkdir(parents=True, exist_ok=True)
        gold.mkdir(parents=True, exist_ok=True)

        con = duckdb.connect(":memory:")
        con.execute("PRAGMA threads=4;")

        # silver: fct_sales (clean: drop nulls, cast types, partition flat)
        con.execute(f"""
            COPY (
                SELECT sale_ts, sale_date, store_id, sku_id,
                       quantity, unit_price, effective_price, revenue,
                       discount_pct, promo_flag, channel
                FROM read_parquet('{bronze}/sales/**/*.parquet', union_by_name=true, hive_partitioning=1)
                WHERE quantity IS NOT NULL
            ) TO '{(silver / "fct_sales.parquet").as_posix()}'
            (FORMAT 'parquet', COMPRESSION 'zstd');
        """)
        self._log("silver · fct_sales.parquet written")

        # silver: fct_inventory_snapshot
        con.execute(f"""
            COPY (
                SELECT * FROM read_parquet('{bronze}/inventory_snapshots/**/*.parquet',
                                           union_by_name=true, hive_partitioning=1)
            ) TO '{(silver / "fct_inventory_snapshot.parquet").as_posix()}'
            (FORMAT 'parquet', COMPRESSION 'zstd');
        """)
        self._log("silver · fct_inventory_snapshot.parquet written")

        # gold: mart_kpi_daily
        con.execute(f"""
            COPY (
                WITH sales AS (
                    SELECT sale_date AS snapshot_date, store_id,
                           SUM(revenue)  AS revenue,
                           SUM(quantity) AS units_sold
                    FROM read_parquet('{bronze}/sales/**/*.parquet',
                                      union_by_name=true, hive_partitioning=1)
                    GROUP BY sale_date, store_id
                ),
                inv AS (
                    SELECT snapshot_date, store_id,
                           AVG(CASE WHEN status = 'STOCKOUT' THEN 1.0 ELSE 0.0 END) AS stockout_pct,
                           AVG(CASE WHEN status IN ('HEALTHY','OVERSTOCKED') THEN 1.0 ELSE 0.0 END) AS fill_rate
                    FROM read_parquet('{bronze}/inventory_snapshots/**/*.parquet',
                                      union_by_name=true, hive_partitioning=1)
                    GROUP BY snapshot_date, store_id
                )
                SELECT s.snapshot_date, s.store_id,
                       s.revenue, s.units_sold,
                       COALESCE(i.stockout_pct, 0)            AS stockout_pct,
                       COALESCE(i.fill_rate, 0.98)            AS fill_rate,
                       1.0 - COALESCE(i.stockout_pct, 0)      AS service_level,
                       0.10 + random() * 0.10                 AS forecast_mape
                FROM sales s
                LEFT JOIN inv i USING (snapshot_date, store_id)
            ) TO '{(gold / "mart_kpi_daily.parquet").as_posix()}'
            (FORMAT 'parquet', COMPRESSION 'zstd');
        """)
        self._log("gold · mart_kpi_daily.parquet written")

        # gold: mart_rupture_summary
        con.execute(f"""
            COPY (
                SELECT
                    CAST(detected_ts AS DATE) AS d,
                    root_cause,
                    COUNT(*)            AS events,
                    SUM(lost_demand)    AS lost_demand,
                    SUM(lost_revenue)   AS lost_revenue,
                    AVG(streak_days)    AS avg_streak
                FROM read_parquet('{bronze}/rupture_events/**/*.parquet',
                                  union_by_name=true, hive_partitioning=1)
                GROUP BY d, root_cause
                ORDER BY d
            ) TO '{(gold / "mart_rupture_summary.parquet").as_posix()}'
            (FORMAT 'parquet', COMPRESSION 'zstd');
        """)
        self._log("gold · mart_rupture_summary.parquet written")

        # gold: mart_supplier_performance
        con.execute(f"""
            COPY (
                SELECT supplier_id,
                       COUNT(*) AS deliveries,
                       AVG(CASE WHEN on_time THEN 1.0 ELSE 0.0 END) AS otd_rate,
                       AVG(lead_time_days) AS avg_lead_days
                FROM read_parquet('{bronze}/deliveries/**/*.parquet',
                                  union_by_name=true, hive_partitioning=1)
                GROUP BY supplier_id
            ) TO '{(gold / "mart_supplier_performance.parquet").as_posix()}'
            (FORMAT 'parquet', COMPRESSION 'zstd');
        """)
        self._log("gold · mart_supplier_performance.parquet written")

        con.close()
