"""Timezone-aware helpers used across simulation and analytics."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from config.settings import settings


def _tz() -> ZoneInfo:
    return ZoneInfo(settings.twin.timezone)


def now_tz() -> datetime:
    return datetime.now(_tz())


def to_local(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_tz())


def daterange(start: datetime, end: datetime, step: timedelta = timedelta(days=1)):
    cur = start
    while cur <= end:
        yield cur
        cur += step
