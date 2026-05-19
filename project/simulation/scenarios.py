"""
Scenario catalog — named operational stress tests the user can fire from the UI.

Each scenario is a small descriptor; the engine applies its parameter overrides
to the demand & supply models for a bounded horizon.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Scenario:
    code: str
    name: str
    description: str
    horizon_hours: int = 72
    demand_overrides: dict[str, Any] = field(default_factory=dict)
    supply_overrides: dict[str, Any] = field(default_factory=dict)
    severity: str = "MEDIUM"


class ScenarioCatalog:
    """Curated catalog of repeatable what-if scenarios."""

    BASELINE = Scenario(
        code="BASELINE",
        name="Operação Baseline",
        description="Operação normal sem disrupções — referência para comparação.",
        severity="INFO",
    )

    SUPPLIER_DISRUPTION = Scenario(
        code="SUPPLIER_OUT",
        name="Disrupção crítica de fornecedor T1",
        description="Fornecedor tier-1 indisponível por 96h; lead times sobem +4d.",
        horizon_hours=96,
        supply_overrides={"disruption_active": True, "otd_rate": 0.55},
        severity="CRITICAL",
    )

    DEMAND_SPIKE = Scenario(
        code="DEMAND_SPIKE",
        name="Pico de demanda promocional",
        description="Campanha de Black Friday — demanda 2.2x baseline por 72h.",
        horizon_hours=72,
        demand_overrides={"shock_multiplier": 2.2, "promo_lift": 1.65},
        severity="HIGH",
    )

    HEATWAVE = Scenario(
        code="HEATWAVE",
        name="Onda de calor (clima extremo)",
        description="Demanda de bebidas e congelados 1.8x por 5 dias.",
        horizon_hours=120,
        demand_overrides={"shock_multiplier": 1.8},
        severity="HIGH",
    )

    LOGISTICS_STRIKE = Scenario(
        code="LOG_STRIKE",
        name="Greve de transporte",
        description="OTD da malha logística cai para 60% por 48h.",
        horizon_hours=48,
        supply_overrides={"otd_rate": 0.60, "disruption_active": True, "disruption_lead_penalty_days": 2.0},
        severity="HIGH",
    )

    @classmethod
    def all(cls) -> list[Scenario]:
        return [v for k, v in vars(cls).items()
                if not k.startswith("_") and isinstance(v, Scenario)]

    @classmethod
    def by_code(cls, code: str) -> Scenario | None:
        return next((s for s in cls.all() if s.code == code), None)
