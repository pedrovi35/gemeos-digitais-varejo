"""Reusable Plotly chart factories — all using the twin_dark template."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config.theme import THEME


# ──────────────────────────────────────────────────────────────────────────
def sparkline(values: list[float], *, color: str | None = None, height: int = 60) -> go.Figure:
    fig = go.Figure(go.Scatter(
        y=values, mode="lines",
        line=dict(color=color or THEME["primary"], width=2, shape="spline"),
        fill="tozeroy", fillcolor=f"{(color or THEME['primary'])}22",
    ))
    fig.update_layout(
        height=height, margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def kpi_gauge(value: float, *, title: str, vmin: float = 0, vmax: float = 100,
              threshold_warn: float = 70, threshold_crit: float = 55) -> go.Figure:
    color = THEME["healthy"] if value >= threshold_warn else THEME["warning"] if value >= threshold_crit else THEME["critical"]
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number=dict(font=dict(size=30, color=THEME["text"])),
        title=dict(text=title, font=dict(size=12, color=THEME["text_muted"])),
        gauge=dict(
            axis=dict(range=[vmin, vmax], tickfont=dict(color=THEME["text_dim"], size=10)),
            bar=dict(color=color, thickness=0.30),
            bgcolor=THEME["bg_panel"], borderwidth=0,
            steps=[
                {"range": [vmin, threshold_crit],         "color": "rgba(239,68,68,0.18)"},
                {"range": [threshold_crit, threshold_warn], "color": "rgba(245,158,11,0.18)"},
                {"range": [threshold_warn, vmax],         "color": "rgba(16,185,129,0.18)"},
            ],
        ),
    ))
    fig.update_layout(height=240, margin=dict(l=20, r=20, t=20, b=20))
    return fig


def stockout_heatmap(df: pd.DataFrame, *, x: str, y: str, z: str) -> go.Figure:
    pivot = df.pivot_table(index=y, columns=x, values=z, aggfunc="mean").fillna(0)
    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=pivot.columns, y=pivot.index,
        colorscale=[(0.0, THEME["bg_panel"]), (0.4, THEME["primary"]),
                    (0.7, THEME["warning"]),  (1.0, THEME["critical"])],
        showscale=True,
        hovertemplate=f"{y}: %{{y}}<br>{x}: %{{x}}<br>{z}: %{{z:.1f}}<extra></extra>",
    ))
    fig.update_layout(height=380, title=f"Mapa de calor — {z}")
    return fig


def coverage_histogram(df: pd.DataFrame) -> go.Figure:
    palette = {
        "< 1d":  THEME["critical"], "1-3d": THEME["warning"], "3-7d": THEME["primary"],
        "7-14d": THEME["healthy"],  "14-30d": THEME["secondary"], "30d+": THEME["text_dim"],
    }
    colors = [palette.get(b, THEME["primary"]) for b in df["bucket"]]
    fig = go.Figure(go.Bar(x=df["bucket"], y=df["n"], marker_color=colors,
                           hovertemplate="%{x}: %{y} SKUs<extra></extra>"))
    fig.update_layout(height=300, title="Distribuição de cobertura (dias)",
                      xaxis_title=None, yaxis_title="SKUs")
    return fig


def network_treemap(df: pd.DataFrame, *, path: list[str], values: str, color: str) -> go.Figure:
    fig = px.treemap(df, path=path, values=values, color=color,
                     color_continuous_scale=[THEME["healthy"], THEME["warning"], THEME["critical"]])
    fig.update_traces(marker=dict(line=dict(color=THEME["bg"], width=1)))
    fig.update_layout(height=440, margin=dict(l=8, r=8, t=32, b=8))
    return fig


def event_timeline(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return go.Figure().update_layout(height=260, title="Timeline operacional (sem eventos)")
    fig = px.scatter(
        df, x="event_ts", y="event_type", color="event_type",
        hover_data=["store_id", "sku_id", "severity"],
    )
    fig.update_traces(marker=dict(size=8, line=dict(width=0.5, color=THEME["bg"])))
    fig.update_layout(height=320, title="Stream de eventos operacionais",
                      showlegend=False, xaxis_title=None, yaxis_title=None)
    return fig


# ──────────────────────────────────────────────────────────────────────────
# Premium new chart factories
# ──────────────────────────────────────────────────────────────────────────
def kpi_radial(values: dict[str, float]) -> go.Figure:
    """Polar / radial chart for executive KPI snapshot (0-100)."""
    labels = list(values.keys())
    series = list(values.values())
    series += [series[0]]; labels += [labels[0]]
    fig = go.Figure(go.Scatterpolar(
        r=series, theta=labels, fill="toself",
        line=dict(color=THEME["primary"], width=2),
        fillcolor="rgba(59,130,246,0.22)",
    ))
    fig.update_layout(
        height=360, showlegend=False,
        polar=dict(
            bgcolor=THEME["bg_elevated"],
            radialaxis=dict(range=[0, 100], gridcolor=THEME["grid"],
                            tickfont=dict(color=THEME["text_dim"], size=10)),
            angularaxis=dict(gridcolor=THEME["grid"],
                             tickfont=dict(color=THEME["text_muted"], size=11)),
        ),
        margin=dict(l=40, r=40, t=20, b=20),
    )
    return fig


def waterfall_lost_sales(buckets: list[tuple[str, float]]) -> go.Figure:
    """Cascata de perdas por causa raiz."""
    labels = [b[0] for b in buckets] + ["TOTAL"]
    values = [b[1] for b in buckets] + [sum(b[1] for b in buckets)]
    measures = ["relative"] * len(buckets) + ["total"]
    fig = go.Figure(go.Waterfall(
        x=labels, y=values, measure=measures,
        increasing=dict(marker=dict(color=THEME["critical"])),
        decreasing=dict(marker=dict(color=THEME["healthy"])),
        totals=dict(marker=dict(color=THEME["primary"])),
        connector=dict(line=dict(color=THEME["border"])),
        textposition="outside",
    ))
    fig.update_layout(height=340, title="Decomposição de perdas por causa-raiz")
    return fig


def gauge_compact(value: float, *, title: str, threshold_warn: float = 70,
                  threshold_crit: float = 55) -> go.Figure:
    """Slim gauge for inline KPI tiles."""
    color = (THEME["healthy"] if value >= threshold_warn else
             THEME["warning"] if value >= threshold_crit else THEME["critical"])
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value,
        number=dict(font=dict(size=22, color=THEME["text"])),
        gauge=dict(
            shape="bullet",
            axis=dict(range=[0, 100], tickfont=dict(color=THEME["text_dim"], size=9)),
            bar=dict(color=color),
            bgcolor=THEME["bg_panel"], borderwidth=0,
        ),
        title=dict(text=title, font=dict(size=11, color=THEME["text_muted"])),
    ))
    fig.update_layout(height=110, margin=dict(l=20, r=20, t=14, b=14))
    return fig
