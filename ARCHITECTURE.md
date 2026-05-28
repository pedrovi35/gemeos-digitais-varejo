# Architecture · Gêmeo Digital de Varejo

Documentação técnica da arquitetura enterprise.

## Princípios

1. **Single warehouse** — DuckDB como fonte analítica única em runtime
2. **Medallion lake** — Parquet bronze/silver/gold para histórico e ML gold layer
3. **Models predict, Groq explains** — separação clara entre ML e LLM
4. **Cache-first** — `st.cache_resource` para conexões; `st.cache_data` para queries
5. **Graceful degradation** — app funciona sem Groq e sem artefatos ML treinados

## Fluxo de dados

```
[Synthetic Seed / World Generator]
        ↓
[DuckDB Warehouse] ←→ [Feature Store Parquet]
        ↓
[ML Ensemble R1-R5] → [Gold risk_scores]
        ↓
[Streamlit UI] + [Groq Interpreter]
```

## Módulos críticos

| Módulo | Responsabilidade |
|--------|------------------|
| `core/bootstrap.py` | Init idempotente por sessão |
| `core/secrets.py` | Env + Streamlit secrets |
| `database/seed.py` | Dados sintéticos com cohorts R1–R5 |
| `models/shared/pipeline.py` | Train → score → gold |
| `services/risk_service.py` | API unificada de risco |
| `agents/ai_service.py` | Roteamento + agentes |

## Deploy topology

- **Local:** `data/warehouse.duckdb`, seed full 60d
- **Streamlit Cloud:** `/tmp/warehouse.duckdb`, light seed 21d, secrets via UI

Ver [DEPLOY.md](DEPLOY.md).

Documentação expandida: [docs/](docs/).
