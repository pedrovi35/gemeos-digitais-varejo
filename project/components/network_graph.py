"""
Supply-chain network graph — Plotly node/edge visualization.

Renders suppliers → stores using a spring layout from NetworkX. Node size
reflects supplier capacity (or store volume), color reflects risk score.
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
) -> go.Figure:
    """Build a Plotly figure of supplier↔store edges with risk-tinted nodes.

    suppliers/stores: must each have at minimum an `id` column.
    edges: columns (supplier_id, store_id, weight?, risk?).
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

    pos = nx.spring_layout(G, seed=7, k=0.35, iterations=60)

    # Edges
    edge_x, edge_y, edge_c = [], [], []
    for u, v, d in G.edges(data=True):
        x0, y0 = pos[u]; x1, y1 = pos[v]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
        edge_c.append(d.get("risk", 0.0))
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line=dict(color=THEME["border_strong"], width=1.0),
        opacity=0.55, hoverinfo="none",
    )

    # Nodes
    sx, sy, sc, ssz, stxt, ssym = [], [], [], [], [], []
    for n, d in G.nodes(data=True):
        x, y = pos[n]; sx.append(x); sy.append(y)
        sc.append(d.get("risk", 0.0))
        deg = max(1, G.degree(n))
        ssz.append(12 + deg * 1.6)
        stxt.append(f"<b>{d['label']}</b><br>{d['kind'].upper()} · grau={deg} · risk={d.get('risk',0):.1f}")
        ssym.append("diamond" if d["kind"] == "supplier" else "circle")

    node_trace = go.Scatter(
        x=sx, y=sy, mode="markers",
        marker=dict(
            size=ssz, color=sc, symbol=ssym,
            colorscale=[(0.0, THEME["healthy"]), (0.5, THEME["warning"]), (1.0, THEME["critical"])],
            cmin=0, cmax=100,
            line=dict(width=1, color=THEME["bg"]),
            colorbar=dict(
                title=dict(text="Risk", font=dict(color=THEME["text_muted"], size=11)),
                thickness=10,
                tickfont=dict(color=THEME["text_dim"], size=10),
            ),
        ),
        text=stxt, hovertemplate="%{text}<extra></extra>",
    )
    fig = go.Figure([edge_trace, node_trace])
    fig.update_layout(
        height=520, showlegend=False,
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        margin=dict(l=4, r=4, t=8, b=4),
    )
    return fig
