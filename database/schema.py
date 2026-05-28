"""
Warehouse schema bootstrap.

Layout:
    raw_*       — bronze landing tables (append-only, schema-on-read)
    dim_*       — silver dimensions
    fct_*       — silver facts
    mart_*      — gold aggregates (precomputed for the UI)
    log_events  — append-only operational event stream
    log_alerts  — append-only alerts ledger
"""
from __future__ import annotations

from config.logging import logger
from database.connection import get_connection


DDL_STATEMENTS: tuple[str, ...] = (
    # ── Dimensions ─────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dim_store (
        store_id        VARCHAR PRIMARY KEY,
        name            VARCHAR NOT NULL,
        region          VARCHAR NOT NULL,
        format          VARCHAR NOT NULL,
        opened_at       DATE,
        sqm             INTEGER,
        is_active       BOOLEAN DEFAULT TRUE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS dim_supplier (
        supplier_id     VARCHAR PRIMARY KEY,
        name            VARCHAR NOT NULL,
        tier            VARCHAR NOT NULL,
        lead_time_days  INTEGER NOT NULL,
        otd_rate        DOUBLE  DEFAULT 0.95,
        country         VARCHAR DEFAULT 'BR'
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS dim_sku (
        sku_id          VARCHAR PRIMARY KEY,
        ean             VARCHAR,
        description     VARCHAR NOT NULL,
        category        VARCHAR NOT NULL,
        subcategory     VARCHAR,
        brand           VARCHAR,
        unit            VARCHAR DEFAULT 'UN',
        velocity_class  VARCHAR DEFAULT 'B',
        unit_cost       DOUBLE,
        unit_price      DOUBLE,
        shelf_life_days INTEGER,
        supplier_id     VARCHAR REFERENCES dim_supplier(supplier_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS dim_calendar (
        date            DATE PRIMARY KEY,
        dow             INTEGER,
        is_weekend      BOOLEAN,
        is_holiday      BOOLEAN DEFAULT FALSE,
        season          VARCHAR
    );
    """,
    # ── Facts ──────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS fct_inventory_snapshot (
        snapshot_ts     TIMESTAMP NOT NULL,
        store_id        VARCHAR NOT NULL,
        sku_id          VARCHAR NOT NULL,
        on_hand         INTEGER NOT NULL,
        on_order        INTEGER DEFAULT 0,
        reserved        INTEGER DEFAULT 0,
        reorder_point   INTEGER,
        safety_stock    INTEGER,
        days_of_cover   DOUBLE,
        status          VARCHAR
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS fct_sales (
        sale_ts         TIMESTAMP NOT NULL,
        store_id        VARCHAR NOT NULL,
        sku_id          VARCHAR NOT NULL,
        quantity        INTEGER NOT NULL,
        unit_price      DOUBLE NOT NULL,
        revenue         DOUBLE NOT NULL,
        promotion_flag  BOOLEAN DEFAULT FALSE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS fct_replenishment (
        order_id        VARCHAR PRIMARY KEY,
        placed_ts       TIMESTAMP NOT NULL,
        expected_ts     TIMESTAMP,
        delivered_ts    TIMESTAMP,
        store_id        VARCHAR NOT NULL,
        sku_id          VARCHAR NOT NULL,
        supplier_id     VARCHAR NOT NULL,
        quantity        INTEGER NOT NULL,
        status          VARCHAR NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS fct_forecast (
        forecast_ts     TIMESTAMP NOT NULL,
        target_date     DATE NOT NULL,
        store_id        VARCHAR NOT NULL,
        sku_id          VARCHAR NOT NULL,
        demand_p50      DOUBLE,
        demand_p90      DOUBLE,
        model_version   VARCHAR
    );
    """,
    # ── Ledgers ────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS log_events (
        event_id        VARCHAR PRIMARY KEY,
        event_ts        TIMESTAMP NOT NULL,
        event_type      VARCHAR NOT NULL,
        store_id        VARCHAR,
        sku_id          VARCHAR,
        payload         JSON,
        severity        VARCHAR
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS log_alerts (
        alert_id        VARCHAR PRIMARY KEY,
        raised_ts       TIMESTAMP NOT NULL,
        severity        VARCHAR NOT NULL,
        store_id        VARCHAR,
        sku_id          VARCHAR,
        title           VARCHAR NOT NULL,
        message         VARCHAR,
        acknowledged    BOOLEAN DEFAULT FALSE,
        resolved_ts     TIMESTAMP
    );
    """,
    # ── Marts (gold) ───────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS mart_kpi_daily (
        snapshot_date   DATE NOT NULL,
        store_id        VARCHAR,
        revenue         DOUBLE,
        units_sold      INTEGER,
        stockout_pct    DOUBLE,
        fill_rate       DOUBLE,
        service_level   DOUBLE,
        forecast_mape   DOUBLE,
        PRIMARY KEY (snapshot_date, store_id)
    );
    """,
)


INDEX_STATEMENTS: tuple[str, ...] = (
    "CREATE INDEX IF NOT EXISTS idx_inv_store_sku ON fct_inventory_snapshot(store_id, sku_id);",
    "CREATE INDEX IF NOT EXISTS idx_sales_ts      ON fct_sales(sale_ts);",
    "CREATE INDEX IF NOT EXISTS idx_events_ts     ON log_events(event_ts);",
    "CREATE INDEX IF NOT EXISTS idx_alerts_sev    ON log_alerts(severity);",
)


def bootstrap_warehouse() -> None:
    """Idempotent: safe to call on every app startup."""
    conn = get_connection()
    for ddl in DDL_STATEMENTS:
        conn.execute(ddl)
    for idx in INDEX_STATEMENTS:
        conn.execute(idx)
    logger.info("Warehouse schema bootstrapped")
