"""
Supply-chain network graph — Plotly node/edge visualization.

Renders suppliers → stores using a spring layout from NetworkX. Node size
reflects supplier capacity (or store volume), color reflects risk score.
Edge width is proportional to flow weight; edge color tracks risk level.
"""
from __future__ import annotations

import networkx as nx
import pandas as pd
import plotly.graph_objects as go

from config.theme import THEME


def supplier_store_network(
    suppliers: pd.DataFrame,
    stores: pd.DataFrame,
    edges: pd.DataFrame,
    *,
    risk_col: str = "risk",
    weight_col: str = "weight",
    layout: str = "spring",
) -> go.Figure:
    """Build a Plotly figure of supplier↔store edges with risk-tinted nodes.

    suppliers/stores: must each have at minimum an `id` column.
    edges: columns (supplier_id, store_id, weight?, risk?).
    layout: "spring" (default) or "bipartite" (two-column alignment).
    """
    G = nx.Graph()
    for _, s in suppliers.iterrows():
        G.add_node(s["id"], kind="supplier",
                   label=s.get("name", s["id"]),
                   risk=float(s.get(risk_col, 0.0)))
    for _, s in stores.iterrows():
        G.add_node(s["id"], kind="store",
                   label=s.get("name", s["id"]),
                   risk=float(s.get(risk_col, 0.0)))
    for _, e in edges.iterrows():
        G.add_edge(e["supplier_id"], e["store_id"],
                   weight=float(e.get(weight_col, 1.0)),
                   risk=float(e.get(risk_col, 0.0)))

    if len(G) == 0:
        return go.Figure().update_layout(height=480, title="Network · sem dados")

    pos = _layout(G, layout, suppliers["id"].tolist(), stores["id"].tolist())

    # ── Edge traces — 3 traces bucketed by risk band (scales to large graphs) ──
    # low (0–33), medium (33–66), high (66–100)
    _BANDS = [
        (0.0,  0.33, THEME["healthy"],  1.5),
        (0.33, 0.66, THEME["warning"],  2.0),
        (0.66, 1.01, THEME["critical"], 2.5),
    ]
    band_xy: list[tuple[list, list]] = [([], []) for _ in _BANDS]
    for u, v, d in G.edges(data=True):
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        r = max(0.0, min(1.0, d.get("risk", 0.0) / 100.0))
        for i, (lo, hi, *_) in enumerate(_BANDS):
            if lo <= r < hi:
                band_xy[i][0].extend([x0, x1, None])
                band_xy[i][1].extend([y0, y1, None])
                break

    edge_traces: list[go.Scatter] = []
    for (_, _, color, width), (xs, ys) in zip(_BANDS, band_xy):
        if xs:
            edge_traces.append(go.Scatter(
                x=xs, y=ys,
                mode="lines",
                line=dict(color=color, width=width),
                opacity=0.65,
                hoverinfo="none",
                showlegend=False,
            ))

    # ── Node trace ─────────────────────────────────────────────────────
    sx, sy, sc, ssz, stxt, ssym, slbl = [], [], [], [], [], [], []
    for n, d in G.nodes(data=True):
        x, y = pos[n]
        sx.append(x); sy.append(y)
        sc.append(d.get("risk", 0.0))
        deg = max(1, G.degree(n))
        ssz.append(14 + deg * 2.0)
        label = d["label"]
        # Abbreviated label for display (≤12 chars)
        short = label[:11] + "…" if len(label) > 12 else label
        slbl.append(short)
        stxt.append(
            f"<b>{label}</b><br>"
            f"{d['kind'].upper()} · degree={deg}<br>"
            f"Risk: {d.get('risk', 0.0):.1f}/100"
        )
        ssym.append("diamond" if d["kind"] == "supplier" else "circle")

    node_trace = go.Scatter(
        x=sx, y=sy,
        mode="markers+text",
        text=slbl,
        textposition="top center",
        textfont=dict(color=THEME["text_muted"], size=9),
        marker=dict(
            size=ssz, color=sc, symbol=ssym,
            colorscale=[
                (0.0, THEME["healthy"]),
                (0.5, THEME["warning"]),
                (1.0, THEME["critical"]),
            ],
            cmin=0, cmax=100,
            line=dict(width=1, color=THEME["bg"]),
            colorbar=dict(
                title=dict(text="Risk", font=dict(color=THEME["text_muted"], size=11)),
                thickness=10,
                tickfont=dict(color=THEME["text_dim"], size=10),
                x=1.01,
            ),
        ),
        hovertext=stxt,
        hovertemplate="%{hovertext}<extra></extra>",
        showlegend=False,
    )

    # ── Legend items (invisible scatter for shape/color legend) ────────
    legend_supplier = go.Scatter(
        x=[None], y=[None], mode="markers",
        marker=dict(symbol="diamond", size=10, color=THEME["primary"]),
        name="Fornecedor", showlegend=True,
    )
    legend_store = go.Scatter(
        x=[None], y=[None], mode="markers",
        marker=dict(symbol="circle", size=10, color=THEME["secondary"]),
        name="Loja", showlegend=True,
    )

    fig = go.Figure([*edge_traces, node_trace, legend_supplier, legend_store])
    fig.update_layout(
        height=540, showlegend=True,
        legend=dict(
            orientation="h", x=0.01, y=-0.04,
            font=dict(color=THEME["text_muted"], size=11),
            bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        margin=dict(l=4, r=4, t=8, b=30),
    )
    return fig


# ── Layout helpers ──────────────────────────────────────────────────────────

def _layout(
    G: nx.Graph,
    mode: str,
    supplier_ids: list,
    store_ids: list,
) -> dict:
    if mode == "bipartite" and supplier_ids and store_ids:
        pos: dict = {}
        n_sup = len(supplier_ids)
        n_sto = len(store_ids)
        for i, sid in enumerate(supplier_ids):
            if sid in G:
                pos[sid] = (0.0, 1.0 - i / max(n_sup - 1, 1))
        for i, sid in enumerate(store_ids):
            if sid in G:
                pos[sid] = (1.0, 1.0 - i / max(n_sto - 1, 1))
        # Isolated nodes that weren't placed — distribute on a row below
        placed = set(pos)
        unplaced = [n for n in G.nodes if n not in placed]
        n_un = len(unplaced)
        for i, n in enumerate(unplaced):
            x = i / max(n_un - 1, 1) if n_un > 1 else 0.5
            pos[n] = (x, -0.2)
        return pos

    return nx.spring_layout(G, seed=7, k=0.40, iterations=80)
