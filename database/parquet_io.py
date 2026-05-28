"""
Parquet I/O — bronze/silver/gold medallion architecture.

Strategy:
  bronze/  — raw immutable landing files, partitioned by date=YYYY-MM-DD
  silver/  — cleansed, type-cast, partitioned by store_id / date
  gold/    — KPI marts, single-file snapshots per period

DuckDB reads Parquet directly via `read_parquet(...)` so we can mix files +
tables in the same query plan.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from config.logging import logger
from config.settings import settings


def _layer_path(layer: str) -> Path:
    return {
        "bronze": settings.lake.bronze,
        "silver": settings.lake.silver,
        "gold":   settings.lake.gold,
    }[layer]


def write_partition(
    layer: str, dataset: str, table: pa.Table, *,
    partition_date: date | None = None, store_id: str | None = None,
) -> Path:
    """Write a Parquet file under the medallion layer.

    Path layout: <layer>/<dataset>/date=YYYY-MM-DD/[store_id=...]/part.parquet
    """
    base = _layer_path(layer) / dataset
    if partition_date:
        base = base / f"date={partition_date.isoformat()}"
    if store_id:
        base = base / f"store_id={store_id}"
    base.mkdir(parents=True, exist_ok=True)

    out = base / "part.parquet"
    pq.write_table(table, out, compression="zstd", compression_level=3)
    logger.debug(f"parquet → {out} ({table.num_rows} rows)")
    return out


def scan_dataset(layer: str, dataset: str) -> str:
    """Return a DuckDB-compatible glob path."""
    base = _layer_path(layer) / dataset
    return f"{base.as_posix()}/**/*.parquet"
