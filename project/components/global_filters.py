"""
Global filter rail — sidebar context shared across every page.

Filters: store, region, category, supplier (free-text), date period.
State is persisted via SessionState so navigation preserves selections.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import streamlit as st

from config.constants import CATEGORIES, DEFAULT_STORES
from utils.session import SessionState


@dataclass(frozen=True)
class FilterContext:
    store_id:    str | None
    region:      str | None
    category:    str | None
    supplier_id: str | None
    date_start:  date
    date_end:    date

    @property
    def period_days(self) -> int:
        return (self.date_end - self.date_start).days + 1

    def chips(self) -> list[tuple[str, str]]:
        return [
            ("LOJA",      self.store_id or "TODAS"),
            ("REGIÃO",    self.region or "—"),
            ("CATEGORIA", self.category or "TODAS"),
            ("PERÍODO",   f"{self.period_days}d"),
        ]


def _ensure_defaults() -> None:
    today = date.today()
    SessionState.set("flt_store",    SessionState.get("flt_store", "ALL"))
    SessionState.set("flt_region",   SessionState.get("flt_region", "ALL"))
    SessionState.set("flt_category", SessionState.get("flt_category", "ALL"))
    SessionState.set("flt_supplier", SessionState.get("flt_supplier", ""))
    SessionState.set("flt_date_start", SessionState.get("flt_date_start", today - timedelta(days=29)))
    SessionState.set("flt_date_end",   SessionState.get("flt_date_end",   today))


def render_global_filters(*, show_supplier: bool = True,
                          show_dates: bool = True) -> FilterContext:
    """Render the filter rail in the sidebar and return the active context."""
    _ensure_defaults()

    with st.sidebar:
        st.markdown("### CONTEXTO OPERACIONAL")

        regions = sorted({s["region"] for s in DEFAULT_STORES})
        region_opts = ["ALL", *regions]
        region = st.selectbox(
            "Região", options=region_opts,
            index=region_opts.index(SessionState.get("flt_region", "ALL")),
            format_func=lambda x: "Todas as regiões" if x == "ALL" else x,
            key="ui_flt_region",
        )
        SessionState.set("flt_region", region)

        scoped_stores = [s for s in DEFAULT_STORES if region == "ALL" or s["region"] == region]
        store_opts = ["ALL", *[s["store_id"] for s in scoped_stores]]
        labels = {"ALL": "Toda a rede"} | {s["store_id"]: f"{s['store_id']} · {s['name']}" for s in scoped_stores}
        current_store = SessionState.get("flt_store", "ALL")
        if current_store not in store_opts:
            current_store = "ALL"
        store = st.selectbox(
            "Loja", options=store_opts,
            index=store_opts.index(current_store),
            format_func=lambda x: labels.get(x, x),
            key="ui_flt_store",
        )
        SessionState.set("flt_store", store)
        SessionState.set("selected_store", store)   # back-compat with legacy key

        cat_opts = ["ALL", *CATEGORIES]
        cat = st.selectbox(
            "Categoria", options=cat_opts,
            index=cat_opts.index(SessionState.get("flt_category", "ALL"))
                  if SessionState.get("flt_category", "ALL") in cat_opts else 0,
            format_func=lambda x: "Todas" if x == "ALL" else x,
            key="ui_flt_category",
        )
        SessionState.set("flt_category", cat)

        supplier = ""
        if show_supplier:
            supplier = st.text_input(
                "Fornecedor (ID ou nome)",
                value=SessionState.get("flt_supplier", ""),
                placeholder="ex.: SUP-0021",
                key="ui_flt_supplier",
            )
            SessionState.set("flt_supplier", supplier)

        d_start = SessionState.get("flt_date_start")
        d_end   = SessionState.get("flt_date_end")
        if show_dates:
            rng = st.date_input(
                "Período", value=(d_start, d_end),
                key="ui_flt_dates",
            )
            if isinstance(rng, tuple) and len(rng) == 2:
                d_start, d_end = rng
            SessionState.set("flt_date_start", d_start)
            SessionState.set("flt_date_end",   d_end)

        st.divider()
        st.caption("⚙ Filtros são preservados ao navegar entre páginas.")

    return FilterContext(
        store_id=None    if store    == "ALL" else store,
        region=None      if region   == "ALL" else region,
        category=None    if cat      == "ALL" else cat,
        supplier_id=None if not supplier else supplier.strip(),
        date_start=d_start, date_end=d_end,
    )
