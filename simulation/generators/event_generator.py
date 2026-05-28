"""
Event generator — operational event ledger producer.

Emits and persists rupture events, supplier delays, demand spikes,
promotional starts/ends, replenishment placements and deliveries.

All event collectors expose `.append(...)` semantics during the simulation
day-loop, and a `.flush(...)` to write the month partition.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd


class EventCollector:
    """Generic monthly buffer for any event dataset."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._buffer: list[dict] = []

    def append(self, **row) -> None:
        self._buffer.append(row)

    def extend(self, rows: list[dict]) -> None:
        self._buffer.extend(rows)

    def __len__(self) -> int:
        return len(self._buffer)

    def flush(self, out_dir: Path, year: int, month: int) -> Path | None:
        if not self._buffer:
            return None
        df = pd.DataFrame(self._buffer)
        partition = out_dir / f"year={year}" / f"month={month:02d}"
        partition.mkdir(parents=True, exist_ok=True)
        out = partition / f"{self.name}.parquet"
        df.to_parquet(out, index=False, compression="zstd")
        self._buffer.clear()
        return out


class EventGenerator:
    """Bundles all operational event collectors used by the world simulator."""

    def __init__(self) -> None:
        self.purchase_orders = EventCollector("purchase_orders")
        self.deliveries      = EventCollector("deliveries")
        self.supplier_delays = EventCollector("supplier_delays")
        self.ruptures        = EventCollector("rupture_events")
        self.causal_log      = EventCollector("operational_events")  # generic ledger

    # ── Atomic emitters ─────────────────────────────────────
    def emit_purchase_order(self, *, ts: datetime, store_id: str, sku_id: str,
                            supplier_id: str, quantity: int,
                            expected_arrival: datetime, trigger: str) -> str:
        order_id = f"PO-{uuid.uuid4().hex[:10].upper()}"
        self.purchase_orders.append(
            order_id=order_id, placed_ts=ts, store_id=store_id, sku_id=sku_id,
            supplier_id=supplier_id, quantity=int(quantity),
            expected_arrival=expected_arrival, status="PLACED", trigger=trigger,
        )
        self.causal_log.append(
            event_id=f"EVT-{uuid.uuid4().hex[:10].upper()}", event_ts=ts,
            event_type="REORDER_TRIGGER", store_id=store_id, sku_id=sku_id,
            severity="INFO", payload_qty=int(quantity), supplier_id=supplier_id,
        )
        return order_id

    def emit_delivery(self, *, ts: datetime, order_id: str, store_id: str,
                      sku_id: str, supplier_id: str, quantity: int,
                      on_time: bool, lead_time_days: float) -> None:
        self.deliveries.append(
            order_id=order_id, delivered_ts=ts, store_id=store_id, sku_id=sku_id,
            supplier_id=supplier_id, quantity=int(quantity), on_time=bool(on_time),
            lead_time_days=float(lead_time_days),
        )
        self.causal_log.append(
            event_id=f"EVT-{uuid.uuid4().hex[:10].upper()}", event_ts=ts,
            event_type="DELIVERY", store_id=store_id, sku_id=sku_id,
            severity="INFO" if on_time else "MEDIUM",
            payload_qty=int(quantity), supplier_id=supplier_id,
        )

    def emit_supplier_delay(self, *, ts: datetime, supplier_id: str,
                            delay_days: float, reason: str) -> None:
        self.supplier_delays.append(
            delay_id=f"DLY-{uuid.uuid4().hex[:8].upper()}", detected_ts=ts,
            supplier_id=supplier_id, delay_days=float(delay_days), reason=reason,
        )
        self.causal_log.append(
            event_id=f"EVT-{uuid.uuid4().hex[:10].upper()}", event_ts=ts,
            event_type="SUPPLIER_DELAY", store_id=None, sku_id=None,
            severity="HIGH", supplier_id=supplier_id, payload_qty=None,
        )

    def emit_rupture(self, *, ts: datetime, store_id: str, sku_id: str,
                     lost_demand: int, lost_revenue: float,
                     streak_days: int, root_cause: str) -> None:
        self.ruptures.append(
            rupture_id=f"RUP-{uuid.uuid4().hex[:10].upper()}", detected_ts=ts,
            store_id=store_id, sku_id=sku_id,
            lost_demand=int(lost_demand), lost_revenue=float(round(lost_revenue, 2)),
            streak_days=int(streak_days), root_cause=root_cause,
        )
        sev = "CRITICAL" if streak_days >= 2 else "HIGH"
        self.causal_log.append(
            event_id=f"EVT-{uuid.uuid4().hex[:10].upper()}", event_ts=ts,
            event_type="STOCKOUT_DETECTED", store_id=store_id, sku_id=sku_id,
            severity=sev, payload_qty=int(lost_demand), supplier_id=None,
        )

    def emit_promo_event(self, *, ts: datetime, kind: str, promo_id: str,
                         store_id: str, sku_id: str) -> None:
        etype = "PROMOTION_START" if kind == "START" else "PROMOTION_END"
        self.causal_log.append(
            event_id=f"EVT-{uuid.uuid4().hex[:10].upper()}", event_ts=ts,
            event_type=etype, store_id=store_id, sku_id=sku_id,
            severity="INFO", payload_qty=None, supplier_id=None,
        )

    # ── Flush all collectors ────────────────────────────────
    def flush_all(self, bronze_root: Path, year: int, month: int) -> dict[str, Path | None]:
        return {
            "purchase_orders":     self.purchase_orders.flush(bronze_root / "purchase_orders", year, month),
            "deliveries":          self.deliveries.flush(bronze_root / "deliveries", year, month),
            "supplier_delays":     self.supplier_delays.flush(bronze_root / "supplier_delays", year, month),
            "rupture_events":      self.ruptures.flush(bronze_root / "rupture_events", year, month),
            "operational_events":  self.causal_log.flush(bronze_root / "operational_events", year, month),
        }
