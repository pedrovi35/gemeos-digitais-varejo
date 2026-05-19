# Arquitetura e fluxo de dados

## Princípios de design

1. **Single warehouse** — DuckDB é a fonte analítica única em runtime.
2. **Medallion lake** — Parquet bronze/silver/gold para histórico e camada gold de scores.
3. **Models predict, Groq explains** — separação estrita entre ML e LLM.
4. **Cache-first** — conexões e queries pesadas em cache Streamlit.
5. **Graceful degradation** — app operacional sem Groq e sem artefatos ML treinados.

## Diagrama de fluxo

```
[Gerador sintético / Seed R1–R5]
           │
           ▼
    [DuckDB Warehouse]  ←── consultas OLAP (fct_*, dim_*, mart_*)
           │
           ├──────────────────► [Feature Store Parquet]
           │                         │
           ▼                         ▼
    [Feature Engineering]    [Cache por ruptura]
           │
           ▼
    [Ensemble ML R1–R5]
           │
           ▼
    [Gold: risk_scores/*.parquet]
           │
           ├──────────────────► [RiskIntelligenceService]
           │                         │
           ▼                         ▼
    [Streamlit UI]            [Agentes Groq]
```

## Camadas da aplicação

### 1. UI (`app.py`, `pages/`, `components/`)

Interface multipage Streamlit. Cada página consome serviços e componentes reutilizáveis (KPI cards, heatmaps, timelines).

### 2. Core (`core/`)

| Módulo | Função |
|--------|--------|
| `bootstrap.py` | Inicialização idempotente por sessão (schema, seed, health) |
| `secrets.py` | Variáveis de ambiente + secrets do Streamlit Cloud |
| `health.py` | Checagens de warehouse, lake e artefatos |
| `errors.py` | Degradação elegante na UI |

### 3. Services (`services/`)

Fronteira entre UI e domínio. O principal é `risk_service.py` — API unificada de scores, rankings, matriz composta e explicações.

### 4. Models (`models/r*/`, `models/shared/`)

Um pacote Python por ruptura, espelhando a mesma estrutura:

```
rN_<nome>/
├── feature_engineering.py
├── trainer.py
├── predictor.py
├── inference.py
├── shap_explainer.py
└── evaluator.py
```

Classes base em `models/shared/` garantem consistência.

### 5. Agents (`agents/`)

Roteamento de intenção (heurísticas + classificador Groq) para agentes especialistas: ruptura, fornecedor, simulação, ML, forecasting.

### 6. Data (`database/`, `data/`)

- **Schema:** dimensões (loja, SKU, fornecedor) + fatos (vendas, inventário, reposição).
- **Seed:** dados sintéticos com cohorts causais R1–R5 (`database/seed.py`).
- **Lake:** `data/bronze`, `data/silver`, `data/gold`.

## Fluxo de uma requisição na Torre de Controle

1. `bootstrap` garante warehouse e seed.
2. `RiskIntelligenceService.tower_summary()` chama `score_all()`.
3. Para cada ruptura, `Inference.score_batch()` lê features (cache ou rebuild) e aplica o predictor.
4. Agregados: média de risco, contagem CRITICAL/HIGH, índice de risco da rede (média ponderada).
5. UI renderiza KPIs e tabela de top entidades.

## Índice de risco da rede

Pesos por ruptura (implementação em `risk_service.py`):

| Ruptura | Peso |
|---------|------|
| R1 | 22% |
| R2 | 20% |
| R3 | 18% |
| R4 | 20% |
| R5 | 20% |

O índice é a média ponderada dos `avg_risk` de cada ruptura, escalada para 0–100.

## Deploy

| Ambiente | Warehouse | Seed |
|----------|-----------|------|
| Local | `./data/warehouse.duckdb` | Full (60d, 240 SKUs) |
| Streamlit Cloud | `/tmp/warehouse.duckdb` | Light (`TWIN_LIGHT_SEED=true`, 21d) |

Ver [DEPLOY.md](../DEPLOY.md).
