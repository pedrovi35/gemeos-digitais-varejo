#!/usr/bin/env python3
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from database.schema import bootstrap_warehouse
from database.seed import seed_warehouse
from database.connection import get_connection

bootstrap_warehouse()
seed_warehouse(force=True)
c = get_connection()
for label, sql in [
    ("sales", "SELECT COUNT(*) FROM fct_sales"),
    ("inv_snapshots", "SELECT COUNT(*) FROM fct_inventory_snapshot"),
    ("repl", "SELECT COUNT(*) FROM fct_replenishment"),
    ("blocked_po", "SELECT COUNT(*) FROM fct_replenishment WHERE status IN ('BLOCKED','REJECTED')"),
    ("promo_sales", "SELECT COUNT(*) FROM fct_sales WHERE promotion_flag"),
    ("neg_inventory", "SELECT COUNT(*) FROM fct_inventory_snapshot WHERE on_hand < 0"),
    ("stockout_days", "SELECT COUNT(*) FROM fct_inventory_snapshot WHERE status='STOCKOUT'"),
    ("rupture_events", "SELECT COUNT(*) FROM log_events WHERE event_type LIKE '%R%' OR event_type LIKE '%INVENTORY%' OR event_type LIKE '%DEMAND%'"),
]:
    print(f"{label}: {c.execute(sql).fetchone()[0]}")
