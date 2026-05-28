"""
Synthetic Retail World — Causal Operational Data Generator
===========================================================

Produces months/years of believable supermarket operations:
suppliers, SKUs, stores, sales, inventory, promotions, purchase orders,
delays and rupture events, all causally linked through a discrete daily
simulation loop and persisted as Parquet under the bronze/silver/gold
medallion lake.
"""
from simulation.generators.seasonality         import SeasonalityEngine
from simulation.generators.supplier_generator  import SupplierGenerator
from simulation.generators.dimensions          import DimensionGenerator
from simulation.generators.promotion_generator import PromotionGenerator
from simulation.generators.inventory_generator import InventoryGenerator
from simulation.generators.sales_generator     import SalesGenerator
from simulation.generators.event_generator     import EventGenerator
from simulation.generators.retail_world_simulator import RetailWorldSimulator, WorldConfig
from simulation.generators.rupture_scenarios import RuptureType, assign_cohorts, RupturePlan

__all__ = [
    "SeasonalityEngine",
    "SupplierGenerator", "DimensionGenerator",
    "PromotionGenerator", "InventoryGenerator",
    "SalesGenerator", "EventGenerator",
    "RetailWorldSimulator", "WorldConfig",
    "RuptureType", "assign_cohorts", "RupturePlan",
]
