"""
Calibration diagnostics for the digital-twin proof-of-value page.

Three plots, each consuming the row-level scored frame from
`services.backtest_service.score_window`:

    reliability_diagram(scored)        — does P(risk=p) ≈ p?
    lead_time_distribution(scored)     — how many days before the rupture
                                          did the alert fire?
    precision_at_k_curve(scored)       — operational ranking quality
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from config.theme import THEME


def _empty(title: str) -> go.Figure:
    return go.Figure().update_layout(height=320, title=title)


def reliability_diagram(scored: pd.DataFrame, *, n_bins: int = 10,
                        title: str = "Calibração (predito vs realizado)") -> go.Figure:
    """For each decile of predicted risk, plot the empirical event rate.

    A perfectly calibrated model lies on the y=x diagonal.
    """
    if scored.empty or scored["realized"].sum() == 0:
        return _empty(title)

    df = scored[["risk", "realized"]].copy()
    df["bin"] = pd.qcut(df["risk"], q=n_bins, duplicates="drop")
    agg = df.groupby("bin", observed=True).agg(
        predicted=("risk", "mean"),
        realized=("realized", "mean"),
        n=("risk", "size"),
    ).reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1], mode="lines",
        line=dict(color=THEME["text_dim"], dash="dash", width=1),
        name="Calibração perfeita", hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=agg["predicted"], y=agg["realized"],
        mode="markers+lines",
        marker=dict(size=agg["n"].clip(8, 28), color=THEME["accent"],
                    line=dict(color=THEME["primary"], width=1)),
        line=dict(color=THEME["primary"], width=2),
        name="Observado",
        hovertemplate=("Risco predito: %{x:.2f}<br>"
                       "Realizado: %{y:.2f}<br>"
                       "n=%{marker.size}<extra></extra>"),
    ))
    fig.update_layout(
        height=360, title=title,
        xaxis=dict(title="Risco médio predito", range=[0, 1], gridcolor=THEME["grid"]),
        yaxis=dict(title="Taxa real de ruptura", range=[0, 1], gridcolor=THEME["grid"]),
        showlegend=True, margin=dict(l=60, r=30, t=50, b=50),
    )
    return fig


def lead_time_distribution(scored: pd.DataFrame, *, risk_threshold: float = 0.5,
                           title: str = "Lead time do alerta (dias)") -> go.Figure:
    """Histogram of days between cutoff and first rupture, restricted to
    entities the model would have alerted on (risk ≥ threshold AND realized)."""
    flagged = scored[(scored["risk"] >= risk_threshold) & (scored["realized"] == 1)]
    if flagged.empty:
        return _empty(title)
    leads = flagged["lead_days"].dropna().astype(int)
    if leads.empty:
        return _empty(title)

    fig = go.Figure(go.Histogram(
        x=leads, xbins=dict(start=0, end=int(leads.max()) + 1, size=1),
        marker_color=THEME["healthy"],
        hovertemplate="Lead: %{x} dias<br>casos: %{y}<extra></extra>",
    ))
    mean_lead = float(leads.mean())
    fig.add_vline(x=mean_lead, line_dash="dot", line_color=THEME["critical"],
                  annotation_text=f"Média {mean_lead:.1f}d",
                  annotation_position="top right")
    fig.update_layout(
        height=320, title=title,
        xaxis=dict(title="Dias entre alerta e ruptura", gridcolor=THEME["grid"]),
        yaxis=dict(title="# eventos", gridcolor=THEME["grid"]),
        margin=dict(l=50, r=30, t=50, b=50),
    )
    return fig


def precision_at_k_curve(scored: pd.DataFrame, *,
                         ks: tuple[int, ...] = (5, 10, 20, 30, 50, 75, 100),
                         title: str = "Precision@k — ranking operacional") -> go.Figure:
    """For each k, share of the top-k predicted that actually ruptured."""
    if scored.empty:
        return _empty(title)
    ordered = scored.sort_values("risk", ascending=False).reset_index(drop=True)
    rows = []
    base_rate = float(ordered["realized"].mean()) if len(ordered) else 0.0
    for k in ks:
        k = min(k, len(ordered))
        if k == 0:
            continue
        rows.append({"k": k, "precision": float(ordered.head(k)["realized"].mean())})
    if not rows:
        return _empty(title)
    df = pd.DataFrame(rows)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["k"], y=df["precision"],
        marker_color=THEME["primary"],
        text=[f"{v:.0%}" for v in df["precision"]],
        textposition="outside",
        hovertemplate="Top-%{x}<br>precisão: %{y:.1%}<extra></extra>",
        name="Precision@k",
    ))
    fig.add_hline(y=base_rate, line_dash="dot", line_color=THEME["text_dim"],
                  annotation_text=f"Taxa base {base_rate:.1%}",
                  annotation_position="top left")
    fig.update_layout(
        height=320, title=title,
        xaxis=dict(title="k (top-k de maior risco)", gridcolor=THEME["grid"]),
        yaxis=dict(title="Precisão", tickformat=".0%",
                   range=[0, max(1.0, df["precision"].max() * 1.2)],
                   gridcolor=THEME["grid"]),
        showlegend=False, margin=dict(l=50, r=30, t=50, b=50),
    )
    return fig
