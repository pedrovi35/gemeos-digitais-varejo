# Pipeline de machine learning

## Visão do ciclo de vida

O pipeline unificado (`models/shared/pipeline.py` — classe `RiskPipeline`) orquestra:

```
DuckDB → Feature Engineering → Feature Store (cache)
              ↓
         Train (XGB + LGBM)
              ↓
         Avaliação (AUC, F1, …)
              ↓
         Batch Score → Gold Parquet
```

O mesmo fluxo é exposto via CLI (`scripts/train_rupture_models.py`) e pelo **ML Operations Center** na UI.

## Orquestrador: `RiskPipeline`

### `train_one(code)`

1. Instancia `Inference` do modelo R1–R5.
2. `feature_engineer.build()` — query DuckDB + transformações pandas.
3. Persiste features em `data/features/<code>/latest.parquet`.
4. `Trainer.fit(df)` — split temporal, ensemble, métricas.
5. `score_batch(use_cache=False)` — scoring completo.
6. Grava `data/gold/risk_scores/<code>/latest.parquet`.

### `train_all()`

Executa `train_one` para R1, R2, R3, R4 e R5 em sequência. Falhas em um modelo não interrompem os demais (log + continua).

### `score_all()`

Scoring sem retreino — útil após atualização de dados ou refresh da torre.

## Serviço operacional: `RiskIntelligenceService`

Camada consumida pela UI (`services/risk_service.py`):

| Método | Uso |
|--------|-----|
| `score_rupture(code)` | DataFrame com scores de uma ruptura |
| `score_all()` | Dict `{ "R1": df, … }` |
| `load_gold(code)` | Lê parquet gold se existir |
| `tower_summary(store_id?)` | Agregados para Torre de Controle |
| `operational_ranking(code, k)` | Top-K entidades |
| `composite_matrix(store_id?)` | Heatmap entidade × ruptura |
| `explain(code, entity)` | `RiskExplanation` com SHAP |
| `model_metrics(code)` | Métricas do `meta.json` |
| `train_all()` / `train_one(code)` | Dispara pipeline |

## Schemas de saída

Definidos em `models/shared/schemas.py`:

- **`RiskScore`** — score, nível, probabilidade, horizonte, versão do modelo.
- **`RiskExplanation`** — top drivers SHAP, contrafactuais, narrativa opcional.
- **`ModelMetrics`** — ROC-AUC, PR-AUC, precision, recall, F1, tamanhos de treino/validação.

## Registro de modelos

`MODEL_CATALOG` em `registry.py` é a **fonte única da verdade** para:

- nome longo da ruptura,
- pacote Python (`models.r1_inventory_break`, …),
- coluna de output,
- tipo de entidade (`store_sku` vs `supplier`).

Função `get_model(code)` carrega dinamicamente a classe `Inference` correta.

## Modo heurístico (sem treino)

Se `models/artifacts/<RN>/xgb.joblib` não existir, `BasePredictor` calcula um score via média z-score das features + sigmoid. A plataforma permanece demonstrável antes do primeiro `bootstrap --train`.

## Comandos úteis

```bash
# Bootstrap + treino de todos os modelos
python scripts/bootstrap.py --force --train

# Apenas treino
python scripts/train_rupture_models.py

# Verificar assinaturas R1–R5 no warehouse
python scripts/verify_rupture_seed.py
```

## Artefatos gerados

```
models/artifacts/
├── R1/
│   ├── xgb.joblib
│   ├── lgbm.joblib
│   └── meta.json
├── R2/ … R5/

data/gold/risk_scores/
├── R1/latest.parquet
└── …
```
