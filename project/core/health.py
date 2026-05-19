"""Runtime health checks — warehouse, lake, ML artifacts, LLM."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from config.settings import settings


@dataclass
class HealthReport:
    healthy: bool
    checks: dict[str, bool] = field(default_factory=dict)
    details: dict[str, str] = field(default_factory=dict)

    def badge(self) -> str:
        return "HEALTHY" if self.healthy else "DEGRADED"


def check_health() -> HealthReport:
    checks: dict[str, bool] = {}
    details: dict[str, str] = {}

    # DuckDB
    db_path = Path(settings.duckdb.path)
    checks["duckdb_file"] = db_path.exists()
    details["duckdb"] = str(db_path)

    try:
        from database.connection import get_connection
        conn = get_connection()
        n_skus = conn.execute("SELECT COUNT(*) FROM dim_sku").fetchone()[0]
        n_sales = conn.execute("SELECT COUNT(*) FROM fct_sales").fetchone()[0]
        checks["warehouse_seeded"] = n_skus > 0 and n_sales > 0
        details["warehouse"] = f"{n_skus} SKUs · {n_sales:,} sales rows"
    except Exception as e:
        checks["warehouse_seeded"] = False
        details["warehouse"] = f"error: {e}"

    # Lake
    bronze = settings.lake.bronze
    checks["lake_bronze"] = bronze.exists()
    details["lake"] = str(bronze)

    # ML artifacts (optional)
    art = settings.root / "models" / "artifacts"
    trained = list(art.glob("R*/meta.json")) if art.exists() else []
    checks["ml_trained"] = len(trained) >= 1
    details["ml"] = f"{len(trained)}/5 rupture models trained"

    # LLM
    checks["groq_configured"] = bool(settings.groq.api_key)
    details["groq"] = settings.groq.model if settings.groq.api_key else "offline mode"

    healthy = checks.get("warehouse_seeded", False)
    return HealthReport(healthy=healthy, checks=checks, details=details)
