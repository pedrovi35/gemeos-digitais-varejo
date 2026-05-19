#!/usr/bin/env python3
"""
Full environment bootstrap — directories, schema, seed, validation.

Usage:
    python scripts/bootstrap.py
    python scripts/bootstrap.py --full
    python scripts/bootstrap.py --force
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.secrets import hydrate_settings_from_secrets


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap Gêmeo Digital runtime")
    parser.add_argument("--force", action="store_true", help="Re-seed warehouse")
    parser.add_argument("--full", action="store_true", help="Full seed (disable light mode)")
    parser.add_argument("--train", action="store_true", help="Train rupture models after seed")
    args = parser.parse_args()

    hydrate_settings_from_secrets()
    if args.full:
        import os
        os.environ["TWIN_LIGHT_SEED"] = "false"

    from config.logging import configure_logging, logger
    from database.schema import bootstrap_warehouse
    from database.seed import seed_warehouse

    configure_logging()
    logger.info("Bootstrap started")
    bootstrap_warehouse()
    seed_warehouse(force=args.force)

    from scripts.validate import run_validations
    report = run_validations()
    if not report.ok:
        logger.error(f"Validation failed: {report.errors}")
        return 1

    if args.train:
        from services.risk_service import RiskIntelligenceService
        RiskIntelligenceService().train_all()

    logger.info("Bootstrap complete ✓")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
