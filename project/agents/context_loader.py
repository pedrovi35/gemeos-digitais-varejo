"""
Operational context loader — converts the warehouse into a compact JSON
dossier for the LLM. SQL is template-based; the agents pick which
templates to run, never construct SQL from free text.

Each loader returns a dict suitable for embedding in the system prompt.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd

from agents.schemas import Evidence
from database.connection import get_connection


# ─────────────────────────────────────────────────────────────────────────────
# Whitelisted query templates — parameterized, no free-text concatenation
# ─────────────────────────────────────────────────────────────────────────────
_TEMPLATES: dict[str, str] = {
    "kpi_today": """
        SELECT * FROM mart_kpi_daily
        WHERE snapshot_date = CURRENT_DATE
          AND (? IS NULL OR store_id = ?)
    """,
    "kpi_trend_14d": """
        SELECT snapshot_date, AVG(service_level) sl, AVG(fill_rate) fr,
               AVG(stockout_pct) so, SUM(revenue) rev
        FROM mart_kpi_daily
        WHERE snapshot_date >= CURRENT_DATE - INTERVAL 14 DAY
          AND (? IS NULL OR store_id = ?)
        GROUP BY snapshot_date ORDER BY snapshot_date
    """,
    "top_risk_categories": """
        SELECT k.category,
               COUNT_IF(i.status IN ('STOCKOUT','CRITICAL'))                 AS at_risk,
               COUNT(*)                                                       AS total,
               COUNT_IF(i.status IN ('STOCKOUT','CRITICAL'))::DOUBLE
                   / NULLIF(COUNT(*),0)                                       AS risk_pct
        FROM fct_inventory_snapshot i
        INNER JOIN dim_sku k USING (sku_id)
        WHERE i.snapshot_ts >= CURRENT_TIMESTAMP - INTERVAL 24 HOUR
        GROUP BY k.category ORDER BY risk_pct DESC LIMIT 6
    """,
    "ruptured_skus": """
        SELECT i.store_id, i.sku_id, k.description, k.category, k.velocity_class,
               i.on_hand, i.reorder_point, i.safety_stock, i.days_of_cover
        FROM fct_inventory_snapshot i
        INNER JOIN dim_sku k USING (sku_id)
        WHERE i.status IN ('STOCKOUT','CRITICAL')
          AND i.snapshot_ts >= CURRENT_TIMESTAMP - INTERVAL 24 HOUR
          AND (? IS NULL OR i.store_id = ?)
          AND (? IS NULL OR k.category = ?)
        ORDER BY i.days_of_cover ASC LIMIT 20
    """,
    "sku_sales_28d": """
        SELECT CAST(sale_ts AS DATE) d,
               SUM(quantity) q, SUM(revenue) rev,
               BOOL_OR(promotion_flag) had_promo
        FROM fct_sales
        WHERE sku_id = ? AND store_id = ?
          AND sale_ts >= CURRENT_TIMESTAMP - INTERVAL 28 DAY
        GROUP BY d ORDER BY d
    """,
    "open_alerts": """
        SELECT severity, title, store_id, sku_id, message, raised_ts
        FROM log_alerts WHERE resolved_ts IS NULL
        ORDER BY CASE severity WHEN 'CRITICAL' THEN 0 WHEN 'HIGH' THEN 1
                               WHEN 'MEDIUM' THEN 2 ELSE 3 END,
                 raised_ts DESC LIMIT 10
    """,
    "supplier_otd_recent": """
        SELECT s.supplier_id, s.name, s.tier, s.otd_rate, s.lead_time_days
        FROM dim_supplier s
        WHERE s.otd_rate < 0.95
        ORDER BY s.otd_rate ASC LIMIT 10
    """,
    "lost_sales_7d": """
        WITH expected AS (
            SELECT sku_id, AVG(quantity * unit_price) AS daily_loss
            FROM fct_sales
            WHERE sale_ts >= CURRENT_TIMESTAMP - INTERVAL 30 DAY
            GROUP BY sku_id
        ),
        out_days AS (
            SELECT sku_id, COUNT(DISTINCT CAST(snapshot_ts AS DATE)) days_out
            FROM fct_inventory_snapshot
            WHERE status = 'STOCKOUT'
              AND snapshot_ts >= CURRENT_TIMESTAMP - INTERVAL 7 DAY
            GROUP BY sku_id
        )
        SELECT COALESCE(SUM(e.daily_loss * o.days_out), 0) AS lost
        FROM expected e JOIN out_days o USING (sku_id)
    """,
}


def run_template(name: str, params: list[Any] | None = None) -> pd.DataFrame:
    """Run a whitelisted SQL template. Raises if `name` is not registered."""
    if name not in _TEMPLATES:
        raise KeyError(f"template not whitelisted: {name}")
    conn = get_connection()
    return conn.execute(_TEMPLATES[name], params or []).fetch_df()


# ─────────────────────────────────────────────────────────────────────────────
# High-level dossier builders
# ─────────────────────────────────────────────────────────────────────────────
def load_general_context(store_id: str | None = None) -> dict:
    """Compact dossier for general operational questions."""
    kpi = run_template("kpi_today", [store_id, store_id])
    trend = run_template("kpi_trend_14d", [store_id, store_id])
    risks = run_template("top_risk_categories")
    alerts = run_template("open_alerts")
    lost = float(run_template("lost_sales_7d").iloc[0, 0]) if not run_template("lost_sales_7d").empty else 0.0

    return {
        "scope":          {"store_id": store_id or "ALL"},
        "kpi_today":      kpi.iloc[0].to_dict() if not kpi.empty else {},
        "trend_14d":      trend.to_dict(orient="records"),
        "top_risks":      risks.to_dict(orient="records"),
        "open_alerts":    alerts.to_dict(orient="records"),
        "lost_sales_7d":  round(lost, 2),
    }


def load_rupture_context(store_id: str | None = None,
                         category: str | None = None) -> dict:
    """Detailed dossier for rupture investigation."""
    ruptured = run_template("ruptured_skus", [store_id, store_id, category, category])
    risks    = run_template("top_risk_categories")
    suppliers= run_template("supplier_otd_recent")
    lost_df  = run_template("lost_sales_7d")
    lost     = float(lost_df.iloc[0, 0]) if not lost_df.empty else 0.0
    return {
        "scope":               {"store_id": store_id or "ALL", "category": category or "ALL"},
        "ruptured_skus":       ruptured.to_dict(orient="records"),
        "top_risk_categories": risks.to_dict(orient="records"),
        "suppliers_below_sla": suppliers.to_dict(orient="records"),
        "lost_sales_7d_brl":   round(lost, 2),
    }


def load_sku_context(sku_id: str, store_id: str) -> dict:
    """Per-SKU deep dive for root-cause analysis."""
    sales = run_template("sku_sales_28d", [sku_id, store_id])
    conn  = get_connection()
    sku_meta = conn.execute(
        "SELECT s.*, sup.name supplier_name, sup.tier, sup.otd_rate, sup.lead_time_days "
        "FROM dim_sku s LEFT JOIN dim_supplier sup ON s.supplier_id = sup.supplier_id "
        "WHERE s.sku_id = ?", [sku_id],
    ).fetch_df()
    inventory = conn.execute(
        "SELECT * FROM fct_inventory_snapshot "
        "WHERE sku_id = ? AND store_id = ? "
        "ORDER BY snapshot_ts DESC LIMIT 1", [sku_id, store_id],
    ).fetch_df()
    return {
        "sku":           sku_meta.iloc[0].to_dict() if not sku_meta.empty else {},
        "inventory_now": inventory.iloc[0].to_dict() if not inventory.empty else {},
        "sales_28d":     sales.to_dict(orient="records"),
    }


def evidence_from_context(ctx: dict) -> list[Evidence]:
    """Distill quantitative evidence items from a dossier for the response."""
    ev: list[Evidence] = []
    kpi = ctx.get("kpi_today", {}) or {}
    if "service_level" in kpi:
        ev.append(Evidence(label="Service Level (hoje)",
                           value=f"{float(kpi['service_level']):.2%}",
                           source="mart_kpi_daily", weight=0.9))
    if "stockout_pct" in kpi:
        ev.append(Evidence(label="Taxa de ruptura (hoje)",
                           value=f"{float(kpi['stockout_pct']):.2%}",
                           source="mart_kpi_daily", weight=1.0))
    if ctx.get("lost_sales_7d"):
        ev.append(Evidence(label="Perda estimada · 7d",
                           value=f"R$ {ctx['lost_sales_7d']:,.2f}",
                           source="fct_sales × fct_inventory_snapshot", weight=0.85))
    if ctx.get("top_risks"):
        top = ctx["top_risks"][0]
        ev.append(Evidence(label=f"Categoria com maior risco · {top.get('category','—')}",
                           value=f"{float(top.get('risk_pct', 0)):.1%}",
                           source="fct_inventory_snapshot", weight=0.75))
    if ctx.get("open_alerts"):
        ev.append(Evidence(label="Alertas críticos abertos",
                           value=str(sum(1 for a in ctx["open_alerts"] if a.get("severity") == "CRITICAL")),
                           source="log_alerts", weight=0.7))
    return ev
