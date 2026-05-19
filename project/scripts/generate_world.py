"""
CLI runner — synthesize the full retail world into the medallion lake.

Usage:
    python scripts/generate_world.py
    python scripts/generate_world.py --months 12 --stores 20 --skus 3000

The script writes:
    data/bronze/<dataset>/year=YYYY/month=MM/*.parquet
    data/silver/{dim_*, fct_sales, fct_inventory_snapshot}.parquet
    data/gold/{mart_kpi_daily, mart_rupture_summary, mart_supplier_performance}.parquet
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

# Make `project/` importable when invoked from anywhere
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from simulation.generators import RetailWorldSimulator, WorldConfig   # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Retail Digital Twin · Synthetic World Generator")
    p.add_argument("--months",   type=int, default=12, help="Months of history to synthesize")
    p.add_argument("--stores",   type=int, default=20)
    p.add_argument("--skus",     type=int, default=3000)
    p.add_argument("--suppliers",type=int, default=200)
    p.add_argument("--seed",     type=int, default=7)
    p.add_argument("--bronze",   type=Path, default=ROOT / "data" / "bronze")
    p.add_argument("--silver",   type=Path, default=ROOT / "data" / "silver")
    p.add_argument("--gold",     type=Path, default=ROOT / "data" / "gold")
    p.add_argument("--quiet",    action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    end   = date.today()
    start = (end - timedelta(days=args.months * 30)).replace(day=1)
    cfg = WorldConfig(
        start_date=start, end_date=end,
        n_stores=args.stores, n_skus=args.skus, n_suppliers=args.suppliers,
        seed=args.seed,
        bronze_root=args.bronze, silver_root=args.silver, gold_root=args.gold,
        verbose=not args.quiet,
    )
    stats = RetailWorldSimulator(cfg).run()
    print()
    print("─" * 64)
    print(f"days         : {stats.days:>12,}")
    print(f"sales rows   : {stats.sales_rows:>12,}")
    print(f"snapshot rows: {stats.snapshot_rows:>12,}")
    print(f"purchase POs : {stats.purchase_orders:>12,}")
    print(f"deliveries   : {stats.deliveries:>12,}")
    print(f"ruptures     : {stats.ruptures:>12,}")
    print(f"delays       : {stats.delays:>12,}")
    print(f"elapsed (s)  : {stats.elapsed_s:>12.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
