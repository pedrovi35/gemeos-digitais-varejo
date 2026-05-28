#!/usr/bin/env python3
"""Automated validation suite for deploy readiness."""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@dataclass
class ValidationReport:
    ok: bool
    checks: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def run_validations() -> ValidationReport:
    report = ValidationReport(ok=True)

    def check(name: str, fn) -> None:
        try:
            fn()
            report.checks.append(f"[OK] {name}")
        except Exception as e:
            report.ok = False
            report.errors.append(f"{name}: {e}")
            report.checks.append(f"[FAIL] {name}")

    check("settings", lambda: __import__("config.settings", fromlist=["settings"]).settings)
    check("schema", lambda: __import__("database.schema", fromlist=["bootstrap_warehouse"]).bootstrap_warehouse())

    def warehouse():
        from database.connection import get_connection
        c = get_connection()
        assert c.execute("SELECT COUNT(*) FROM dim_sku").fetchone()[0] > 0
        assert c.execute("SELECT COUNT(*) FROM fct_sales").fetchone()[0] > 0

    check("warehouse_data", warehouse)
    check("rupture_registry", lambda: len(__import__("models.shared.registry", fromlist=["MODEL_CATALOG"]).MODEL_CATALOG) == 5)
    check("risk_service", lambda: __import__("services.risk_service", fromlist=["get_risk_service"]).get_risk_service())

    return report


def main() -> int:
    r = run_validations()
    for line in r.checks:
        print(line)
    if r.errors:
        for e in r.errors:
            print(f"ERROR: {e}", file=sys.stderr)
    return 0 if r.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
