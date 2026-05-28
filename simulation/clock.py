"""Simulation clock — discrete-time advancement with configurable speed."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from utils.time_utils import now_tz


@dataclass
class SimulationClock:
    current: datetime
    step: timedelta = timedelta(minutes=15)
    speed: int = 60          # x real-time

    @classmethod
    def start(cls, step_minutes: int = 15, speed: int = 60) -> "SimulationClock":
        return cls(current=now_tz(), step=timedelta(minutes=step_minutes), speed=speed)

    def tick(self) -> datetime:
        self.current += self.step
        return self.current

    def fast_forward(self, hours: int) -> datetime:
        self.current += timedelta(hours=hours)
        return self.current
