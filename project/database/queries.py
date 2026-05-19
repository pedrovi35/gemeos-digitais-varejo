"""
Centralized SQL registry — every query the UI executes lives here.

Keeping SQL in one module gives us:
  • single audit surface for query plans
  • static type for parameter binding
  • a clean place for parametrized DuckDB CTEs
"""
from __future__ import annotations


class QueryRegistry:
    # ─────────────────────────────────────────────────────────────
    # Operational health
    # ─────────────────────────────────────────────────────────────
    OPS_KPI_TODAY = """
        SELECT
            COALESCE(SUM(revenue), 0)                AS revenue_today,
            COALESCE(SUM(units_sold), 0)             AS units_today,
            COALESCE(AVG(stockout_pct), 0)           AS stockout_pct,
            COALESCE(AVG(fill_rate), 0)              AS fill_rate,
            COALESCE(AVG(service_level), 0)          AS service_level,
            COALESCE(AVG(forecast_mape), 0)          AS forecast_mape
        FROM mart_kpi_daily
        WHERE snapshot_date = CURRENT_DATE
          AND (? IS NULL OR store_id = ?);
    """

    OPS_KPI_TREND = """
        SELECT
            snapshot_date,
            SUM(revenue)         AS revenue,
            SUM(units_sold)      AS units_sold,
            AVG(stockout_pct)    AS stockout_pct,
            AVG(fill_rate)       AS fill_rate,
            AVG(service_level)   AS service_level
        FROM mart_kpi_daily
        WHERE snapshot_date BETWEEN CURRENT_DATE - INTERVAL ? DAY AND CURRENT_DATE
          AND (? IS NULL OR store_id = ?)
        GROUP BY snapshot_date
        ORDER BY snapshot_date;
    """

    # ─────────────────────────────────────────────────────────────
    # Inventory
    # ─────────────────────────────────────────────────────────────
    INVENTORY_LIVE = """
        WITH latest AS (
            SELECT store_id, sku_id, MAX(snapshot_ts) AS ts
            FROM fct_inventory_snapshot
            GROUP BY store_id, sku_id
        )
        SELECT
            i.snapshot_ts, i.store_id, s.name AS store_name,
            i.sku_id, k.description, k.category, k.velocity_class,
            i.on_hand, i.on_order, i.reserved,
            i.reorder_point, i.safety_stock,
            i.days_of_cover, i.status
        FROM fct_inventory_snapshot i
        INNER JOIN latest  l ON l.store_id = i.store_id AND l.sku_id = i.sku_id AND l.ts = i.snapshot_ts
        INNER JOIN dim_sku   k ON k.sku_id   = i.sku_id
        INNER JOIN dim_store s ON s.store_id = i.store_id
        WHERE (? IS NULL OR i.store_id = ?)
          AND (? IS NULL OR k.category = ?);
    """

    STOCKOUT_RANKING = """
        SELECT
            k.category,
            COUNT_IF(i.status IN ('STOCKOUT','CRITICAL')) AS at_risk,
            COUNT(*)                                       AS total,
            COUNT_IF(i.status IN ('STOCKOUT','CRITICAL'))::DOUBLE / NULLIF(COUNT(*),0) AS risk_pct
        FROM fct_inventory_snapshot i
        INNER JOIN dim_sku k ON k.sku_id = i.sku_id
        WHERE i.snapshot_ts >= CURRENT_TIMESTAMP - INTERVAL 24 HOUR
        GROUP BY k.category
        ORDER BY risk_pct DESC;
    """

    # ─────────────────────────────────────────────────────────────
    # Events & alerts
    # ─────────────────────────────────────────────────────────────
    EVENTS_RECENT = """
        SELECT event_ts, event_type, store_id, sku_id, severity, payload
        FROM log_events
        ORDER BY event_ts DESC
        LIMIT ?;
    """

    ALERTS_OPEN = """
        SELECT alert_id, raised_ts, severity, store_id, sku_id, title, message
        FROM log_alerts
        WHERE resolved_ts IS NULL
        ORDER BY
            CASE severity
                WHEN 'CRITICAL' THEN 0
                WHEN 'HIGH'     THEN 1
                WHEN 'MEDIUM'   THEN 2
                WHEN 'LOW'      THEN 3
                ELSE 4
            END,
            raised_ts DESC;
    """

    # ─────────────────────────────────────────────────────────────
    # Forecast
    # ─────────────────────────────────────────────────────────────
    FORECAST_HORIZON = """
        SELECT target_date, store_id, sku_id, demand_p50, demand_p90
        FROM fct_forecast
        WHERE target_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL ? DAY
          AND (? IS NULL OR store_id = ?);
    """
