"""
Design system — Operations Tower dark theme.

Centralizes the visual identity so every page, component and Plotly figure
shares the same enterprise palette.
"""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio


THEME = {
    # ── Surfaces ────────────────────────────────────────────
    "bg":            "#070C14",
    "bg_elevated":   "#0D1421",
    "bg_panel":      "#121B2E",
    "bg_overlay":    "#182237",
    "bg_card":       "#0F1A2C",
    "border":        "#1E2E4A",
    "border_strong": "#293F61",
    "grid":          "#1A2740",

    # ── Typography ──────────────────────────────────────────
    "text":          "#E8F0FE",
    "text_muted":    "#8EA8C3",
    "text_dim":      "#4F6680",
    "text_label":    "#6B8AAF",

    # ── Operational status palette ─────────────────────────
    "healthy":       "#00D4AA",
    "warning":       "#FFB800",
    "critical":      "#FF3B5C",
    "stockout":      "#FF1744",
    "info":          "#4299FF",
    "neutral":       "#7C6FE8",

    # ── Brand / accents ─────────────────────────────────────
    "primary":       "#4299FF",
    "secondary":     "#9B7FFF",
    "tertiary":      "#00D4DC",
    "accent":        "#00E5FF",

    # ── Categorical palette (charts) ────────────────────────
    "palette": [
        "#4299FF", "#00D4AA", "#FFB800", "#FF3B5C",
        "#9B7FFF", "#00D4DC", "#FF6B9D", "#A3E635",
        "#FB923C", "#2DD4BF", "#C084FC", "#22D3EE",
    ],

    # ── Sequential gradients ────────────────────────────────
    "gradient_blue":  ["#070C14", "#1E3A8A", "#4299FF", "#93C5FD"],
    "gradient_heat":  ["#070C14", "#1E3A8A", "#FFB800", "#FF3B5C", "#FF1744"],
}


def _build_plotly_template() -> go.layout.Template:
    tpl = go.layout.Template()
    tpl.layout = go.Layout(
        font=dict(family="Inter, 'SF Pro Display', system-ui, sans-serif", size=12, color=THEME["text"]),
        paper_bgcolor=THEME["bg_elevated"],
        plot_bgcolor=THEME["bg_elevated"],
        colorway=THEME["palette"],
        title=dict(font=dict(size=14, color=THEME["text"], family="Inter"), x=0.01, xanchor="left", y=0.97),
        margin=dict(l=44, r=20, t=48, b=40),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=THEME["border"],
            borderwidth=0,
            font=dict(size=11, color=THEME["text_muted"]),
            orientation="h", y=-0.16, x=0,
        ),
        xaxis=dict(
            gridcolor=THEME["grid"], zerolinecolor=THEME["grid"],
            linecolor=THEME["border_strong"],
            tickfont=dict(color=THEME["text_muted"], size=10.5),
            title=dict(font=dict(color=THEME["text_muted"], size=11)),
            showgrid=True, zeroline=False,
        ),
        yaxis=dict(
            gridcolor=THEME["grid"], zerolinecolor=THEME["grid"],
            linecolor=THEME["border_strong"],
            tickfont=dict(color=THEME["text_muted"], size=10.5),
            title=dict(font=dict(color=THEME["text_muted"], size=11)),
            showgrid=True, zeroline=False,
        ),
        hoverlabel=dict(
            bgcolor=THEME["bg_overlay"], bordercolor=THEME["border_strong"],
            font=dict(color=THEME["text"], size=12, family="Inter"),
            namelength=-1,
        ),
        modebar=dict(
            bgcolor="rgba(0,0,0,0)",
            color=THEME["text_dim"],
            activecolor=THEME["primary"],
        ),
    )
    return tpl


PLOTLY_TEMPLATE = _build_plotly_template()
pio.templates["twin_dark"] = PLOTLY_TEMPLATE
pio.templates.default = "twin_dark"
