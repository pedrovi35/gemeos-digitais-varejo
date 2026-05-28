#!/usr/bin/env python3
"""
Train all five rupture models end-to-end.

Usage:
    python scripts/train_rupture_models.py
    python scripts/train_rupture_models.py --rupture R1
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config.logging import configure_logging, logger
from database.schema import bootstrap_warehouse
from database.seed import seed_warehouse
from models.shared.registry import RuptureCode
from services.risk_service import RiskIntelligenceService


def main() -> None:
    parser = argparse.ArgumentParser(description="Train rupture ML models")
    parser.add_argument("--rupture", choices=[c.value for c in RuptureCode], default=None)
    parser.add_argument("--force-seed", action="store_true")
    args = parser.parse_args()

    configure_logging()
    bootstrap_warehouse()
    seed_warehouse(force=args.force_seed)

    svc = RiskIntelligenceService()
    codes = [RuptureCode(args.rupture)] if args.rupture else list(RuptureCode)

    for code in codes:
        logger.info(f"═══ Training {code.value} ═══")
        result = svc.train_one(code)
        m = result.metrics
        logger.info(
            f"[{code.value}] rows={result.n_rows:,} elapsed={result.elapsed_s:.1f}s "
            f"AUC={m.roc_auc} F1={m.f1} precision={m.precision} recall={m.recall}"
        )

    logger.info("Training pipeline complete.")


if __name__ == "__main__":
    main()
