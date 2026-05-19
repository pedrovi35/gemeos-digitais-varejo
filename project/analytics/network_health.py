"""Network-wide operational health composite."""
from __future__ import annotations

from services.kpi_service import KpiService


class NetworkHealthAnalytics:
    def __init__(self) -> None:
        self.kpi = KpiService()

    def score(self) -> float:
        return self.kpi.network_health_score()

    def grade(self) -> str:
        s = self.score()
        if s >= 90: return "A"
        if s >= 80: return "B"
        if s >= 70: return "C"
        if s >= 60: return "D"
        return "E"

    def status_label(self) -> str:
        s = self.score()
        if s >= 85: return "OPERAÇÃO NOMINAL"
        if s >= 70: return "DEGRADAÇÃO LEVE"
        if s >= 55: return "ATENÇÃO REQUERIDA"
        return "CRÍTICO"
