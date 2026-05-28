# Engenharia de features

Todas as rupturas herdam de `BaseFeatureEngineering` (`models/shared/base_feature_engineering.py`), que fornece:

- acesso DuckDB via `self.df(sql)`,
- features de calendário (`is_weekend`, `is_payday`),
- janelas rolantes (`add_rolling_features`),
- z-scores normalizados.

Features são cacheadas pelo **Feature Store** (`data/features/<code>/latest.parquet`).

### Modo backtest (`cutoff_ts`)

`build(cutoff_ts=...)` permite reconstruir features como observáveis numa data
de corte passada — usado pelo backtest walk-forward:

- `self.df()` reescreve todo `CURRENT_TIMESTAMP` no SQL para o instante do corte;
- `trim_to_cutoff()` descarta linhas cuja data-âncora `d` ultrapasse o corte.

Sem `cutoff_ts`, o comportamento é o de produção (tempo real). Ver
[prova-de-valor-backtest-e-contrafactual.md](prova-de-valor-backtest-e-contrafactual.md).

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

**Target:** sinal de quebra observável na janela atual ou na próxima — `stockout_frequency` ≥ 10% **ou** stockout no dia seguinte ≥ 10% **ou** `stock_accuracy` no quintil mais baixo. Os snapshots do seed são esparsos (~7 dias por loja-SKU); um *shift* puro de −7d apagaria todo o futuro, então o target mistura sinal corrente com um look-ahead curto.

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

**Target (estritamente futuro):** demanda máxima nos próximos H dias > 1,8× a média móvel 7d corrente. Usa apenas quantidades futuras — nenhuma feature do período atual entra no target, evitando o *target-leak* que inflava a AUC.

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

**Target (estritamente futuro):** houve evento de promoção não sinalizada nos próximos H dias — evento = `promotion_registered` == 0 **e** uplift > 50%. Misturar o uplift corrente no target (regra antiga) vazava a feature de volta para o label.

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

**Target (estritamente futuro):** cobertura mínima (`days_of_cover`) nos próximos H dias cai abaixo de 2. A regra antiga misturava `logistics_delay_score` e `supplier_delay_rate` (ambas features) no target — gerava AUC in-sample perfeita e ~0,43 out-of-time.

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

**Granularidade:** uma linha por `supplier_id` × dia (janela de 60 dias). A grade temporal substitui a linha-única por fornecedor — sem o eixo de tempo havia ~7 linhas no total, insuficiente para treinar.

**Fontes:** `dim_supplier`, `fct_inventory_snapshot`, `fct_replenishment`.

---

## Chave de entidade

| Ruptura | `entity_key` |
|---------|----------------|
| R1–R4 | `{store_id}·{sku_id}` |
| R5 | `supplier_id` |

## Boas práticas ao estender features

1. Manter `FEATURE_COLS` como tupla explícita — usada por trainer e SHAP.
2. Evitar leakage: targets devem olhar estritamente para o futuro (`shift`/`rolling`
   sobre janelas posteriores) e nunca reutilizar uma feature do período corrente.
3. Honrar o corte de backtest: `build()` deve aceitar `cutoff_ts` e terminar com
   `trim_to_cutoff(out)`.
4. Documentar novas colunas neste arquivo e no docstring do módulo.
5. Rodar `train_one` após mudança estrutural de features (invalida cache).
