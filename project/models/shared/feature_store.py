"""
Feature store — caches engineered features as parquet under data/features/.

Used by training and inference to avoid recomputing rolling windows on every
page load. Keyed by (rupture_code, dataset_version).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from config.settings import settings
from utils.time_utils import now_tz


class FeatureStore:
    """Single-file-per-cut feature persistence."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root or (settings.root / "data" / "features"))
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, code: str, tag: str) -> Path:
        return self.root / code / f"{tag}.parquet"

    def write(self, code: str, df: pd.DataFrame, *, tag: str = "latest") -> Path:
        p = self._path(code, tag)
        p.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(p, index=False, compression="zstd")
        return p

    def read(self, code: str, *, tag: str = "latest") -> pd.DataFrame | None:
        p = self._path(code, tag)
        if not p.exists():
            return None
        try:
            return pd.read_parquet(p)
        except Exception:
            # Corrupted / empty parquet — delete and signal miss
            p.unlink(missing_ok=True)
            return None

    def freshness(self, code: str, *, tag: str = "latest") -> datetime | None:
        p = self._path(code, tag)
        if not p.exists():
            return None
        return datetime.fromtimestamp(p.stat().st_mtime).astimezone(now_tz().tzinfo)
