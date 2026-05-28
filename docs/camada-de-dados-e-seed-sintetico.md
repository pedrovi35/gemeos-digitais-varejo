# Camada de dados e seed sintético

## DuckDB como warehouse único

Em runtime, todas as consultas analíticas passam por um arquivo DuckDB configurável (`DUCKDB_PATH`, default `./data/warehouse.duckdb`).

**Vantagens no MVP:**

- OLAP embutido, sem servidor externo,
- SQL familiar para features,
- deploy simples no Streamlit Cloud (`/tmp/warehouse.duckdb`).

## Modelo dimensional (resumo)

Definido em `database/schema.py`:

### Dimensões

| Tabela | Conteúdo |
|--------|----------|
| `dim_store` | Lojas da rede |
| `dim_supplier` | Fornecedores, tier, lead time, OTD |
| `dim_sku` | Produtos, categoria, classe de velocidade |
| `dim_calendar` | Calendário com feriados e payday |

### Fatos

| Tabela | Conteúdo |
|--------|----------|
| `fct_sales` | Vendas por timestamp, qty, revenue, promotion_flag |
| `fct_inventory_snapshot` | Estoque on_hand, on_order, days_of_cover, status |
| `fct_replenishment` | Pedidos, placed/delivered/expected, status |
| `fct_forecast` | Previsões e MAPE |

### Marts e logs

| Tabela | Conteúdo |
|--------|----------|
| `mart_kpi_daily` | service_level, fill_rate, stockout_pct, forecast_mape |
| `log_events` | Eventos operacionais |
| `log_alerts` | Alertas para a torre |

## Medallion lake (Parquet)

Estrutura sob `data/`:

```
data/
├── bronze/          # dados brutos (ex.: promotions.parquet)
├── silver/          # transformações intermediárias
├── gold/
│   └── risk_scores/ # scores ML por ruptura
├── features/        # cache de feature engineering
└── warehouse.duckdb
```

Compressão: **zstd**. Diretórios de dados são gitignored — gerados no bootstrap.

## Seed sintético com cohorts R1–R5

`database/seed.py` popula o warehouse com histórico causal:

1. Cria dimensões (lojas, fornecedores, SKUs).
2. `assign_cohorts()` — ~8% dos SKUs por ruptura + baseline.
3. Injeta padrões via `simulation/generators/rupture_scenarios.py`:
   - **R1:** drift de inventário
   - **R2:** spikes de demanda
   - **R3:** vendas promocionais sem calendário
   - **R4:** atrasos de reposição
   - **R5:** pedidos bloqueados / rejeição NF
4. Gera vendas, snapshots, reposições, KPIs e ledger de eventos de ruptura.

### Parâmetros de seed (`.env`)

| Variável | Default | Efeito |
|----------|---------|--------|
| `TWIN_LIGHT_SEED` | `false` | Seed reduzido para Cloud |
| `TWIN_SEED_HISTORY_DAYS` | `60` | Dias de histórico |
| `TWIN_SEED_N_SKUS` | `240` | Tamanho do catálogo |

### Bootstrap

```bash
python scripts/bootstrap.py --force          # schema + seed light
python scripts/bootstrap.py --force --full   # 60d, 240 SKUs
python scripts/bootstrap.py --force --train  # + treino ML
```

## Promoções (R3)

Calendário comercial em:

```
data/bronze/promotions/promotions.parquet
```

Colunas esperadas: `store_id`, `sku_id`, `start_date`, `end_date`, `discount_pct`. O feature engineering R3 cruza vendas com este calendário para detectar uplift **não sinalizado**.

## Feature Store

`models/shared/feature_store.py` persiste DataFrames engenheirados:

```
data/features/R1/latest.parquet
```

Evita recalcular janelas rolantes a cada refresh da página Streamlit.

## Conexão e cache

`database/connection.py` expõe `get_connection()` — tipicamente cacheada com `@st.cache_resource` no bootstrap.

## Evolução para produção

Substituir seed sintético por:

1. ingestão ETL de ERP/WMS/TMS,
2. bronze = landing zone,
3. silver = regras de qualidade,
4. gold = features + scores versionados.

O contrato SQL das features pode permanecer; apenas as fontes mudam.
