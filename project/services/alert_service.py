"""Alert service — open ledger, acknowledgement, escalation."""
from __future__ import annotations

import uuid

import pandas as pd

from config.constants import AlertSeverity
from database.queries import QueryRegistry
from services.base import BaseService
from utils.time_utils import now_tz


class AlertService(BaseService):

    def open(self) -> pd.DataFrame:
        return self.df(QueryRegistry.ALERTS_OPEN)

    def count_by_severity(self) -> dict[str, int]:
        df = self.df("""
            SELECT severity, COUNT(*) AS n
            FROM log_alerts
            WHERE resolved_ts IS NULL
            GROUP BY severity;
        """)
        return dict(zip(df["severity"], df["n"], strict=False))

    def raise_alert(self, severity: AlertSeverity, title: str, message: str,
                    store_id: str | None = None, sku_id: str | None = None) -> str:
        alert_id = f"ALR-{uuid.uuid4().hex[:10].upper()}"
        self.execute(
            "INSERT INTO log_alerts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);",
            [alert_id, now_tz(), severity.value, store_id, sku_id, title, message, False, None],
        )
        return alert_id

    def acknowledge(self, alert_id: str) -> None:
        self.execute("UPDATE log_alerts SET acknowledged = TRUE WHERE alert_id = ?;", [alert_id])

    def resolve(self, alert_id: str) -> None:
        self.execute("UPDATE log_alerts SET resolved_ts = ? WHERE alert_id = ?;", [now_tz(), alert_id])
