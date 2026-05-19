"""Domain enumerations and operational constants for the retail twin."""
from __future__ import annotations

from enum import Enum


class StockStatus(str, Enum):
    HEALTHY     = "HEALTHY"
    WARNING     = "WARNING"
    CRITICAL    = "CRITICAL"
    STOCKOUT    = "STOCKOUT"
    OVERSTOCKED = "OVERSTOCKED"


class AlertSeverity(str, Enum):
    INFO     = "INFO"
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


class EventType(str, Enum):
    SALE              = "SALE"
    REPLENISHMENT     = "REPLENISHMENT"
    DELIVERY          = "DELIVERY"
    SHRINKAGE         = "SHRINKAGE"
    PRICE_CHANGE      = "PRICE_CHANGE"
    PROMOTION_START   = "PROMOTION_START"
    SUPPLIER_DELAY    = "SUPPLIER_DELAY"
    DEMAND_SPIKE      = "DEMAND_SPIKE"
    STOCKOUT_DETECTED = "STOCKOUT_DETECTED"
    REORDER_TRIGGER   = "REORDER_TRIGGER"


class OrderStatus(str, Enum):
    DRAFT       = "DRAFT"
    PLACED      = "PLACED"
    IN_TRANSIT  = "IN_TRANSIT"
    DELIVERED   = "DELIVERED"
    CANCELLED   = "CANCELLED"
    BACKORDERED = "BACKORDERED"


class SkuVelocity(str, Enum):
    A = "A"   # high velocity / 80% of revenue
    B = "B"   # medium velocity / 15% of revenue
    C = "C"   # low velocity / 5% of revenue


# Operational SLAs (referenced by analytics & alerting)
SLA_FILL_RATE          = 0.985
SLA_ON_TIME_DELIVERY   = 0.97
SLA_FORECAST_ACCURACY  = 0.85
SLA_SHELF_AVAILABILITY = 0.99

# Categories — Brazilian supermarket taxonomy
CATEGORIES: tuple[str, ...] = (
    "Hortifruti", "Padaria", "Açougue", "Peixaria", "Frios e Laticínios",
    "Mercearia", "Bebidas", "Limpeza", "Higiene Pessoal", "Bazar",
    "Congelados", "Pet Shop",
)

# Default store network
DEFAULT_STORES: tuple[dict, ...] = (
    {"store_id": "ST-001", "name": "Centro",      "region": "SP-Capital", "format": "Standard"},
    {"store_id": "ST-002", "name": "Zona Sul",    "region": "SP-Capital", "format": "Premium"},
    {"store_id": "ST-003", "name": "Zona Leste",  "region": "SP-Capital", "format": "Compact"},
    {"store_id": "ST-004", "name": "Campinas",    "region": "SP-Interior","format": "Standard"},
    {"store_id": "ST-005", "name": "Santos",      "region": "SP-Litoral", "format": "Standard"},
)
