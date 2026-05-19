"""
Simulation Engine — orchestrates the digital twin clock.

Responsibilities:
  • advance the simulation clock
  • drive demand & supply models
  • emit operational events into the bus and warehouse
  • apply scenario overrides
  • compute live inventory deltas
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

import numpy as np

from config.constants import AlertSeverity, EventType, StockStatus
from config.logging import logger
from services.event_service import EventService
from services.alert_service import AlertService
from services.inventory_service import InventoryService
from simulation.clock import SimulationClock
from simulation.demand_model import DemandModel, DemandParams
from simulation.event_bus import EventBus, SimEvent
from simulation.scenarios import Scenario, ScenarioCatalog
from simulation.supply_model import SupplyModel, SupplyParams


@dataclass
class EngineStats:
    ticks: int = 0
    events: int = 0
    sales_units: int = 0
    stockouts: int = 0
    reorders: int = 0
    by_type: dict[str, int] = field(default_factory=dict)


class SimulationEngine:
    """Discrete-event simulation engine for the retail twin."""

    def __init__(self, *, seed: int = 7) -> None:
        self.rng = np.random.default_rng(seed)
        self.clock = SimulationClock.start()
        self.bus = EventBus()
        self.demand = DemandModel(DemandParams(), rng=self.rng)
        self.supply = SupplyModel(SupplyParams(), rng=self.rng)
        self.scenario: Scenario = ScenarioCatalog.BASELINE
        self.stats = EngineStats()

        self._inventory = InventoryService()
        self._events    = EventService()
        self._alerts    = AlertService()

    # ── Scenario control ────────────────────────────────────
    def apply_scenario(self, scenario: Scenario) -> None:
        self.scenario = scenario
        for k, v in scenario.demand_overrides.items():
            setattr(self.demand.p, k, v)
        for k, v in scenario.supply_overrides.items():
            setattr(self.supply.p, k, v)
        logger.info(f"scenario applied → {scenario.code}")
        self._events.emit(
            EventType.DEMAND_SPIKE if "DEMAND" in scenario.code else EventType.SUPPLIER_DELAY,
            payload={"scenario": scenario.code, "name": scenario.name},
            severity=AlertSeverity(scenario.severity) if scenario.severity in AlertSeverity._value2member_map_ else AlertSeverity.MEDIUM,
        )

    # ── Tick loop ───────────────────────────────────────────
    def tick(self) -> None:
        now = self.clock.tick()
        self.stats.ticks += 1

        snap = self._inventory.live_snapshot()
        if snap.empty:
            return

        dow, hour = now.weekday(), now.hour
        sampled = snap.sample(n=min(40, len(snap)), random_state=int(self.rng.integers(0, 1_000_000)))

        for _, row in sampled.iterrows():
            qty = self.demand.sample(dow=dow, hour=hour, velocity=row.get("velocity_class", "B"))
            if qty <= 0:
                continue
            new_on_hand = max(0, int(row["on_hand"]) - qty)
            self.stats.sales_units += min(qty, int(row["on_hand"]))

            status = self._inventory.classify(new_on_hand, int(row["reorder_point"] or 0),
                                              int(row["safety_stock"] or 0))
            self._inventory.execute(
                """
                UPDATE fct_inventory_snapshot
                SET on_hand = ?, status = ?, snapshot_ts = ?
                WHERE store_id = ? AND sku_id = ? AND snapshot_ts = ?;
                """,
                [new_on_hand, status.value, now, row["store_id"], row["sku_id"], row["snapshot_ts"]],
            )

            self._publish(EventType.SALE, store_id=row["store_id"], sku_id=row["sku_id"],
                          payload={"qty": int(qty), "on_hand": new_on_hand})

            if status == StockStatus.STOCKOUT:
                self.stats.stockouts += 1
                self._alerts.raise_alert(
                    AlertSeverity.CRITICAL,
                    title=f"Stockout: {row['sku_id']} @ {row['store_id']}",
                    message=f"On-hand zerou após venda de {qty} unidades.",
                    store_id=row["store_id"], sku_id=row["sku_id"],
                )
                self._publish(EventType.STOCKOUT_DETECTED, row["store_id"], row["sku_id"])
            elif status == StockStatus.CRITICAL and self.rng.random() < 0.4:
                self.stats.reorders += 1
                self._publish(EventType.REORDER_TRIGGER, row["store_id"], row["sku_id"],
                              payload={"qty": int(row["reorder_point"] * 2)})

    def run(self, ticks: int = 24) -> EngineStats:
        for _ in range(ticks):
            self.tick()
        return self.stats

    # ── Helpers ─────────────────────────────────────────────
    def _publish(self, etype: EventType, store_id: str | None = None,
                 sku_id: str | None = None, payload: dict | None = None) -> None:
        self.bus.publish(SimEvent(event_type=etype, payload=payload or {}, timestamp=self.clock.current))
        self._events.emit(etype, store_id=store_id, sku_id=sku_id, payload=payload)
        self.stats.events += 1
        self.stats.by_type[etype.value] = self.stats.by_type.get(etype.value, 0) + 1

    def reset(self) -> None:
        self.stats = EngineStats()
        self.clock = SimulationClock.start()
        self.bus.reset()
        self.scenario = ScenarioCatalog.BASELINE
