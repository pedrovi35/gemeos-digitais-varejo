# Catálogo das rupturas R1–R5

Cada ruptura é um **fenômeno operacional distinto**, modelado de forma independente com features, target e granularidade próprios. O catálogo oficial está em `models/shared/registry.py`.

## Resumo comparativo

| Código | Nome operacional | Entidade | Coluna de score | Horizonte típico |
|--------|------------------|----------|-----------------|----------------|
| **R1** | Quebra de inventário | loja × SKU | `inventory_break_risk` | 7 dias |
| **R2** | Venda acima da média | loja × SKU | `above_average_sales_risk` | 7 dias |
| **R3** | Promoção não sinalizada | loja × SKU | `unsignaled_promotion_risk` | 7 dias |
| **R4** | Lead time / entrega | loja × SKU | `purchase_delivery_risk` | 7 dias |
| **R5** | Restrição de faturamento | fornecedor | `supplier_billing_restriction_risk` | 7 dias |

## Níveis de risco

Scores contínuos em `[0, 1]` são convertidos em níveis (`models/shared/schemas.py`):

| Score | Nível |
|-------|-------|
| ≥ 0,80 | CRITICAL |
| ≥ 0,60 | HIGH |
| ≥ 0,35 | MODERATE |
| < 0,35 | LOW |

---

## R1 · Quebra de inventário

**Definição:** inconsistência entre estoque sistêmico (WMS/ERP) e estoque real reconstruído a partir de movimentações.

**Sinais operacionais:**

- divergência `on_hand` vs estoque reconstruído (vendas + reposição),
- ajustes frequentes,
- alta taxa de stockout,
- shrinkage elevado.

**Cenário sintético:** cohort de SKUs com drift periódico de inventário (`simulation/generators/rupture_scenarios.py` → `r1_inventory_drift`).

**Página dedicada:** `pages/11_📦_R1_Inventory_Break_Center.py`

---

## R2 · Venda acima da média

**Definição:** pico de demanda anormal em relação à baseline rolante (média/std 7–14 dias), fora de sazonalidade esperada.

**Sinais operacionais:**

- z-score de quantidade elevado,
- aceleração de demanda,
- efeito payday/fim de semana,
- SKUs classe A mais expostos.

**Cenário sintético:** spikes de demanda em múltiplas lojas do cohort R2.

**Página dedicada:** `pages/12_📈_R2_Demand_Spike_Observatory.py`

---

## R3 · Promoção não sinalizada

**Definição:** uplift de vendas com flag de promoção na PDV, mas **sem** registro correspondente no calendário comercial / supply chain.

**Sinais operacionais:**

- `promotion_flag = true` e `promotion_registered = false`,
- queda de preço sem campanha cadastrada,
- ratio de demanda inesperada,
- atraso de sincronização de campanha.

**Dados auxiliares:** calendário em `data/bronze/promotions/promotions.parquet`.

**Página dedicada:** `pages/13_🏷️_R3_Promotion_Intelligence.py`

---

## R4 · Lead time de reposição

**Definição:** risco operacional por atraso ou variabilidade no ciclo compra → entrega, impactando cobertura de estoque.

**Sinais operacionais:**

- taxa de atraso do fornecedor,
- variância de lead time real vs planejado,
- baixa `days_of_cover`,
- alto `on_order_ratio` sem conversão em estoque.

**Cenário sintético:** fornecedor com perfil de atraso ligado ao cohort R4.

**Página dedicada:** `pages/14_🚚_R4_Lead_Time_Risk_Center.py`

---

## R5 · Restrição de faturamento do fornecedor

**Definição:** bloqueio comercial ou restrição financeira que impede faturamento/reposição normal (pedidos rejeitados, limite de crédito).

**Sinais operacionais:**

- pedidos BLOCKED/REJECTED,
- taxa de rejeição de NF,
- score financeiro do fornecedor,
- SKUs em stockout/critical sob o fornecedor.

**Granularidade:** por `supplier_id` (não loja×SKU).

**Página dedicada:** `pages/15_🔒_R5_Supplier_Restriction_Center.py`

---

## Cohorts no seed sintético

O seed divide ~8% dos SKUs por ruptura (`assign_cohorts`). Cada cohort recebe assinatura causal injetada nas tabelas fato, permitindo que modelos e demos reflitam padrões reais de negócio.

Baseline: SKUs restantes sem assinatura de ruptura forçada.
