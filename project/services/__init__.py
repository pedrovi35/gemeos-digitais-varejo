"""Service layer — single boundary between UI and domain logic."""
from services.inventory_service  import InventoryService
from services.sales_service      import SalesService
from services.replenishment_service import ReplenishmentService
from services.forecast_service   import ForecastService
from services.alert_service      import AlertService
from services.event_service      import EventService
from services.kpi_service        import KpiService
from services.risk_service       import RiskIntelligenceService, get_risk_service

__all__ = [
    "InventoryService", "SalesService", "ReplenishmentService",
    "ForecastService", "AlertService", "EventService", "KpiService",
    "RiskIntelligenceService", "get_risk_service",
]
