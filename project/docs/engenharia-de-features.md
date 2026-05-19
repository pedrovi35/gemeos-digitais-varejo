# Engenharia de features

Todas as rupturas herdam de `BaseFeatureEngineering` (`models/shared/base_feature_engineering.py`), que fornece:

- acesso DuckDB via `self.df(sql)`,
- features de calendário (`is_weekend`, `is_payday`),
- janelas rolantes (`add_rolling_features`),
- z-scores normalizados.

Features são cacheadas pelo **Feature Store** (`data/features/<code>/latest.parquet`).

---

## R1 · Quebra de inventário

**Pacote:** `models/r1_inventory_break/feature_engineering.py`

| Feature | Descrição |
|---------|-----------|
| `stock_difference` | `on_hand` sistêmico − estoque reconstruído |
| `inventory_adjustments` | Contagem de dias com divergência |
| `stock_accuracy` | 1 − \|diff\| / max(estoque) |
| `shrinkage_rate` | Devoluções / vendas |
| `stockout_frequency` | Dias em stockout / total (28d) |
| `days_since_inventory_count` | Proxy de contagem física |
| `on_hand`, `days_of_cover` | Nível e cobertura |
| `is_weekend`, `is_payday` | Sazonalidade |

**Target (horizonte 7d):** quebra futura se \|diff futuro\| ≥ 3 **ou** stockout frequency ≥ 10%.

**Fontes SQL:** `fct_sales`, `fct_inventory_snapshot`.

---

## R2 · Venda acima da média

**Pacote:** `models/r2_above_average_sales/feature_engineering.py`

| Feature | Descrição |
|---------|-----------|
| `rolling_mean_7d`, `rolling_std` | Baseline de demanda |
| `demand_acceleration` | Δqty / média |
| `demand_spike_score` | (qty − média) / std |
| `qty_zscore_14d` | Z-score em 14 dias |
| `seasonal_index` | qty / média categoria×loja×mês |
| `payday_flag`, `weekend_flag` | Calendário |
| `velocity_class_a` | SKU classe A |

**Target:** spike atual ≥ 2σ **ou** qty futura > 1,8× média 7d.

**Fontes:** `fct_sales`, `dim_sku`.

---

## R3 · Promoção não sinalizada

**Pacote:** `models/r3_unsignaled_promotion/feature_engineering.py`

| Feature | Descrição |
|---------|-----------|
| `promotion_flag` | Venda com desconto na PDV |
| `promotion_registered` | Promo no calendário bronze |
| `uplift_variation` | (qty − baseline) / baseline |
| `price_drop_pct` | (preço lista − preço médio) / lista |
| `unexpected_demand_ratio` | Uplift quando promo não registrada |
| `campaign_sync_delay` | Dias desde última promo cadastrada |
| `discount_depth`, `sales_velocity_lift` | Intensidade da oferta |

**Target:** promo na PDV sem registro + uplift > 35% **ou** uplift futuro > 50%.

**Fontes:** `fct_sales`, `dim_sku`, `bronze/promotions/promotions.parquet`.

---

## R4 · Lead time de reposição

**Pacote:** `models/r4_purchase_delivery_time/feature_engineering.py`

| Feature | Descrição |
|---------|-----------|
| `average_lead_time` | LT real ou cadastro fornecedor |
| `lead_time_variance` | \|LT real − planejado\| |
| `supplier_delay_rate` | % entregas atrasadas |
| `delivery_accuracy` | 1 − delay rate |
| `replenishment_frequency` | Pedidos / 90 dias |
| `on_order_ratio` | on_order / on_hand |
| `logistics_delay_score` | Composto ponderado |
| `days_of_cover` | Cobertura em dias |

**Target:** delay score ≥ 0,55 **ou** cobertura futura < 2 dias **ou** delay rate ≥ 25%.

**Fontes:** `fct_inventory_snapshot`, `dim_supplier`, `fct_replenishment`.

---

## R5 · Restrição de faturamento

**Pacote:** `models/r5_supplier_billing_restriction/feature_engineering.py`

| Feature | Descrição |
|---------|-----------|
| `supplier_restriction_flag` | Bloqueio inferido |
| `blocked_orders` | Pedidos REJECTED/BLOCKED |
| `invoice_rejection_rate` | Taxa de rejeição NF |
| `supplier_financial_score` | Composto OTD + rejeição |
| `payment_delay`, `credit_limit_usage` | Stress financeiro |
| `otd_rate` | On-time delivery |
| `skus_at_risk`, `avg_days_of_cover` | Exposição da rede |

**Target:** flag de restrição **ou** rejeição ≥ 20% **ou** ≥ 15% SKUs em risco.

**Granularidade:** uma linha por `supplier_id` (snapshot atual).

**Fontes:** `dim_supplier`, `fct_inventory_snapshot`, `fct_replenishment`.

---

## Chave de entidade

| Ruptura | `entity_key` |
|---------|----------------|
| R1–R4 | `{store_id}·{sku_id}` |
| R5 | `supplier_id` |

## Boas práticas ao estender features

1. Manter `FEATURE_COLS` como tupla explícita — usada por trainer e SHAP.
2. Evitar leakage: targets sempre com `shift(-horizon_days)` no tempo.
3. Documentar novas colunas neste arquivo e no docstring do módulo.
4. Rodar `train_one` após mudança estrutural de features (invalida cache).
