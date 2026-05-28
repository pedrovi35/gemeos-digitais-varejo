"""ML / SHAP visualization factories for the rupture intelligence layer."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from config.theme import THEME
from models.shared.schemas import FeatureContribution


def shap_waterfall(drivers: list[FeatureContribution], *, title: str = "Drivers SHAP") -> go.Figure:
    if not drivers:
        return go.Figure().update_layout(height=280, title=title)
    labels = [d.feature.replace("_", " ").title() for d in drivers]
    values = [d.impact_pct for d in drivers]
    colors = [THEME["critical"] if v > 0 else THEME["healthy"] for v in values]
    fig = go.Figure(go.Bar(
        y=labels[::-1], x=values[::-1], orientation="h",
        marker_color=colors[::-1],
        text=[f"{v:+.1f}%" for v in values[::-1]],
        textposition="outside",
        hovertemplate="%{y}<br>impacto: %{x:+.1f}%<extra></extra>",
    ))
    fig.update_layout(
        height=max(280, 44 * len(drivers)),
        title=title,
        xaxis_title="Impacto % (|SHAP| normalizado)",
        margin=dict(l=160, r=40, t=40, b=30),
    )
    return fig


def risk_matrix_heatmap(matrix: pd.DataFrame) -> go.Figure:
    if matrix.empty:
        return go.Figure().update_layout(height=360, title="Matriz de risco composta")
    fig = go.Figure(go.Heatmap(
        z=matrix.values,
        x=matrix.columns,
        y=matrix.index,
        colorscale=[
            (0.0, THEME["bg_panel"]),
            (0.35, THEME["primary"]),
            (0.65, THEME["warning"]),
            (1.0, THEME["critical"]),
        ],
        hovertemplate="Entidade: %{y}<br>%{x}: %{z:.2f}<extra></extra>",
    ))
    fig.update_layout(height=420, title="Matriz de risco · entidade × ruptura",
                      xaxis_title="Ruptura", yaxis_title="Entidade")
    return fig


def rupture_radar(stats: list[dict]) -> go.Figure:
    if not stats:
        return go.Figure().update_layout(height=300)
    labels = [s["code"] for s in stats]
    values = [s["avg_risk"] * 100 for s in stats]
    values_closed = values + [values[0]]
    labels_closed = labels + [labels[0]]
    fig = go.Figure(go.Scatterpolar(
        r=values_closed, theta=labels_closed, fill="toself",
        line=dict(color=THEME["critical"], width=2),
        fillcolor="rgba(239,68,68,0.18)",
        name="Risco médio",
    ))
    fig.update_layout(
        height=340,
        polar=dict(
            radialaxis=dict(range=[0, 100], gridcolor=THEME["grid"],
                            tickfont=dict(color=THEME["text_dim"], size=10)),
            angularaxis=dict(tickfont=dict(color=THEME["text_muted"], size=12)),
            bgcolor=THEME["bg_elevated"],
        ),
        showlegend=False,
        title="Radar de rupturas críticas",
    )
    return fig


def feature_importance_bar(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return go.Figure().update_layout(height=260, title="Importância global")
    top = df.head(12)
    fig = go.Figure(go.Bar(
        y=top["feature"], x=top["importance"], orientation="h",
        marker_color=THEME["primary"],
    ))
    fig.update_layout(height=320, title="Importância global de features (XGBoost)",
                      margin=dict(l=140))
    return fig


def risk_timeline(df: pd.DataFrame, *, score_col: str) -> go.Figure:
    if df.empty or "d" not in df.columns:
        return go.Figure().update_layout(height=260, title="Timeline de risco")
    agg = df.groupby("d")[score_col].mean().reset_index()
    fig = go.Figure(go.Scatter(
        x=agg["d"], y=agg[score_col],
        mode="lines+markers",
        line=dict(color=THEME["critical"], width=2.2),
        fill="tozeroy", fillcolor="rgba(239,68,68,0.12)",
    ))
    fig.update_layout(height=280, title="Evolução do score de risco",
                      yaxis_tickformat=".0%")
    return fig
