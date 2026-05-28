"""
Counterfactual proof-of-value simulator.

Compares two parallel universes for the same (rupture, cutoff, horizon):

    Universe A — Baseline. The twin does nothing. Realized stockouts and
                 lost-sales come straight from the warehouse for the window
                 (cutoff, cutoff+H].

    Universe B — Twin acts. The twin alerts on the top-k entities by risk.
                 For each alerted entity that would have ruptured, the
                 intervention prevents the rupture with probability `effectiveness`
                 (e.g., 0.7 means 7 out of 10 alerts trigger a successful
                 replenishment / transfer / unblock). False positives are
                 charged as the cost of the wasted intervention.

The delta in events and R$ is the digital-twin's measured impact under
a controlled simulation — ground truth comes from the seed, but the twin
never saw the post-cutoff window during training.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from models.shared.registry import RuptureCode
from services.backtest_service import ScoreWindow, score_window


@dataclass
class CounterfactualResult:
    code: str
    cutoff: str
    horizon: int
    top_k: int
    risk_threshold: float
    effectiveness: float
    intervention_unit_cost: float

    # Universe A — baseline
    baseline_events: int
    baseline_lost_revenue: float

    # Universe B — twin acts
    interventions_total: int
    interventions_effective: int           # would-rupture × effectiveness
    interventions_wasted: int              # false-positive alerts
    twin_events: float                     # expected residual ruptures
    twin_lost_revenue: float
    intervention_cost: float

    # Deltas
    events_avoided: float
    revenue_saved: float
    net_value: float                       # revenue_saved - intervention_cost
    avoidance_rate: float                  # events_avoided / baseline_events

    # For drill-down
    scored: pd.DataFrame                   # entity-level: risk, realized, alerted, prevented, $


def simulate(
    code: RuptureCode,
    cutoff: pd.Timestamp,
    horizon: int = 7,
    *,
    top_k: int | None = None,
    risk_threshold: float = 0.5,
    effectiveness: float = 0.7,
    intervention_unit_cost: float = 50.0,
) -> CounterfactualResult | None:
    """Run one (rupture, cutoff) counterfactual.

    `top_k` overrides `risk_threshold` when provided — the twin alerts the
    fixed number of highest-risk entities. Otherwise it alerts everything at
    or above `risk_threshold`.
    """
    win = score_window(code, cutoff, horizon)
    if win is None:
        return None

    s = win.scored.copy()
    s["lost_revenue_if_rupture"] = s["daily_revenue"] * horizon * s["realized"]
    baseline_events = int(s["realized"].sum())
    baseline_lost_revenue = float(s["lost_revenue_if_rupture"].sum())

    if top_k is not None:
        s["alerted"] = 0
        s.loc[s.head(top_k).index, "alerted"] = 1
    else:
        s["alerted"] = (s["risk"] >= risk_threshold).astype(int)

    interventions_total = int(s["alerted"].sum())
    would_rupture_and_alerted = s[(s["alerted"] == 1) & (s["realized"] == 1)]
    interventions_effective = int(round(len(would_rupture_and_alerted) * effectiveness))
    interventions_wasted = interventions_total - len(would_rupture_and_alerted)

    s["prevented"] = 0.0
    s.loc[would_rupture_and_alerted.index, "prevented"] = effectiveness

    events_avoided = float(s["prevented"].sum())
    revenue_saved = float((s["lost_revenue_if_rupture"] * s["prevented"]).sum())
    intervention_cost = float(interventions_total * intervention_unit_cost)
    net_value = revenue_saved - intervention_cost
    twin_events = max(0.0, baseline_events - events_avoided)
    twin_lost_revenue = max(0.0, baseline_lost_revenue - revenue_saved)
    avoidance_rate = (events_avoided / baseline_events) if baseline_events else 0.0

    s["lost_revenue_avoided"] = s["lost_revenue_if_rupture"] * s["prevented"]
    return CounterfactualResult(
        code=code.value,
        cutoff=str(pd.Timestamp(cutoff).date()),
        horizon=horizon,
        top_k=top_k if top_k is not None else -1,
        risk_threshold=risk_threshold,
        effectiveness=effectiveness,
        intervention_unit_cost=intervention_unit_cost,
        baseline_events=baseline_events,
        baseline_lost_revenue=baseline_lost_revenue,
        interventions_total=interventions_total,
        interventions_effective=interventions_effective,
        interventions_wasted=interventions_wasted,
        twin_events=twin_events,
        twin_lost_revenue=twin_lost_revenue,
        intervention_cost=intervention_cost,
        events_avoided=events_avoided,
        revenue_saved=revenue_saved,
        net_value=net_value,
        avoidance_rate=avoidance_rate,
        scored=s,
    )


def aggregate(results: list[CounterfactualResult]) -> dict:
    """Sum deltas across cutoffs / ruptures for a single proof-of-value KPI block."""
    if not results:
        return {
            "baseline_events": 0, "events_avoided": 0.0,
            "baseline_lost_revenue": 0.0, "revenue_saved": 0.0,
            "intervention_cost": 0.0, "net_value": 0.0,
            "avoidance_rate": 0.0, "n_scenarios": 0,
        }
    base = sum(r.baseline_events for r in results)
    avoided = sum(r.events_avoided for r in results)
    return {
        "baseline_events":      base,
        "events_avoided":       avoided,
        "baseline_lost_revenue": sum(r.baseline_lost_revenue for r in results),
        "revenue_saved":        sum(r.revenue_saved for r in results),
        "intervention_cost":    sum(r.intervention_cost for r in results),
        "net_value":            sum(r.net_value for r in results),
        "avoidance_rate":       (avoided / base) if base else 0.0,
        "n_scenarios":          len(results),
    }
