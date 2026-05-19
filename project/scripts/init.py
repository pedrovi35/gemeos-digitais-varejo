#!/usr/bin/env python3
"""Quick init — schema + light seed (CI / Cloud friendly)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("TWIN_LIGHT_SEED", "true")

from database.schema import bootstrap_warehouse
from database.seed import seed_warehouse


def main() -> int:
    bootstrap_warehouse()
    seed_warehouse(force=False)
    print("init OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
