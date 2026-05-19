# Retail World — Synthetic Data Engine

Generates a believable year of supermarket operations:

| Dataset                 | Layer  | Volume (12 months, 20 stores × 3 000 SKUs) |
|-------------------------|--------|---------------------------------------------|
| `sales`                 | bronze | ~30–60 M rows (POS-like, hourly stamps)     |
| `inventory_snapshots`   | bronze | ~22 M rows (daily, store × sku)             |
| `promotions`            | bronze | ~250 k–500 k rows                           |
| `purchase_orders`       | bronze | ~1–3 M rows                                 |
| `deliveries`            | bronze | ~1–3 M rows                                 |
| `supplier_delays`       | bronze | ~20–60 k rows                               |
| `rupture_events`        | bronze | ~200 k–1 M rows                             |
| `operational_events`    | bronze | causal ledger (everything)                  |
| `fct_sales`             | silver | unioned + cleansed                          |
| `fct_inventory_snapshot`| silver | unioned + cleansed                          |
| `mart_kpi_daily`        | gold   | daily KPI mart (revenue, SL, fill, ruptura) |
| `mart_rupture_summary`  | gold   | ruptura × root-cause × day                  |
| `mart_supplier_perf`    | gold   | OTD & lead by supplier                      |

## Causal chain modeled per day

```
PROMOTION_START
   ↓  (lift demand)
↑ demanda diária
   ↓  (consumo)
↓ on_hand → ROP atingido
   ↓
REORDER_TRIGGER → PURCHASE_ORDER
   ↓  (lead time sample, OTD roll)
SUPPLIER_DISRUPTION? ──→ atraso adicional
   ↓
DELIVERY (on_time | atraso)
   ↓  ou…
STOCKOUT_DETECTED (root_cause atribuído)
   ↓  perda de demanda + receita
```

## How to run

```bash
python scripts/generate_world.py --months 12 --stores 20 --skus 3000
```

Outputs land under `data/bronze/<dataset>/year=YYYY/month=MM/part.parquet`,
plus consolidated silver/gold files under `data/silver` and `data/gold`.

## Realism levers built-in

- **Seasonality**: DOW (Fri/Sat peak), month curve, BR holidays, payday (5/15/20/30)
- **Category × month sensitivity** (bebidas+verão, açougue+inverno, etc.)
- **Weather shocks** (heatwaves & cold snaps drive demand spikes)
- **Macro drift** (gentle YoY growth)
- **Promotions** (per-SKU cadence + Black-Friday/Natal blocks; elasticity-driven lift)
- **Supplier behavior** (tier-driven lead times, OTD, multi-day disruptions)
- **Operational dirt**: ~0.3% nulls on `on_order`, ~0.05% sale returns (neg qty/revenue)
- **Root-cause attribution** on every rupture: SUPPLIER_DISRUPTION,
  LEAD_TIME_GAP, PROMO_UNDERFORECAST, DEMAND_SHOCK

All generators are deterministic given `--seed`.
