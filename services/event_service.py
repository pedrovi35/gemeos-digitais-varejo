"""Event service — append-only operational event stream."""
from __future__ import annotations

import json
import uuid

import pandas as pd

from config.constants import AlertSeverity, EventType
from database.queries import QueryRegistry
from services.base import BaseService
from utils.time_utils import now_tz


class EventService(BaseService):

    def emit(self, event_type: EventType, *, store_id: str | None = None,
             sku_id: str | None = None, payload: dict | None = None,
             severity: AlertSeverity = AlertSeverity.INFO) -> str:
        event_id = f"EVT-{uuid.uuid4().hex[:10].upper()}"
        self.execute(
            "INSERT INTO log_events VALUES (?, ?, ?, ?, ?, ?, ?);",
            [event_id, now_tz(), event_type.value, store_id, sku_id,
             json.dumps(payload or {}, default=str), severity.value],
        )
        return event_id

    def recent(self, limit: int = 200) -> pd.DataFrame:
        return self.df(QueryRegistry.EVENTS_RECENT, [limit])

    def histogram(self, hours: int = 24) -> pd.DataFrame:
        return self.df("""
            SELECT date_trunc('hour', event_ts) AS bucket,
                   event_type,
                   COUNT(*) AS n
            FROM log_events
            WHERE event_ts >= CURRENT_TIMESTAMP - INTERVAL ? HOUR
            GROUP BY bucket, event_type
            ORDER BY bucket;
        """, [hours])
