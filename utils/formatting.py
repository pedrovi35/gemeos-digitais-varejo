"""Operational formatting helpers (pt-BR locale conventions)."""
from __future__ import annotations

from datetime import timedelta


def fmt_currency(value: float | int | None, *, prefix: str = "R$") -> str:
    if value is None:
        return "—"
    sign = "-" if value < 0 else ""
    v = abs(float(value))
    s = f"{v:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{sign}{prefix} {s}"


def fmt_int(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{int(value):,}".replace(",", ".")


def fmt_pct(value: float | None, *, decimals: int = 1) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.{decimals}f}%".replace(".", ",")


def fmt_compact(value: float | int | None) -> str:
    if value is None:
        return "—"
    v = float(value)
    for unit, scale in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(v) >= scale:
            return f"{v / scale:.1f}{unit}".replace(".", ",")
    return f"{v:.0f}"


def fmt_duration(seconds: float | int | None) -> str:
    if seconds is None:
        return "—"
    td = timedelta(seconds=int(seconds))
    days = td.days
    h, rem = divmod(td.seconds, 3600)
    m, _ = divmod(rem, 60)
    if days:
        return f"{days}d {h:02d}h"
    if h:
        return f"{h:02d}h {m:02d}m"
    return f"{m:02d}m"
