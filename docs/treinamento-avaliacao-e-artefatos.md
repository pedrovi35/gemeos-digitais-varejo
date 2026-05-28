# Treinamento, avaliação e artefatos

## Ensemble: XGBoost + LightGBM

O treinamento é padronizado em `BaseTrainer` (`models/shared/base_trainer.py`):

| Componente | Configuração padrão |
|------------|---------------------|
| **XGBoost** | 400 árvores, depth 6, lr 0,06, `tree_method=hist` |
| **LightGBM** | 500 estimators, 63 leaves, early stopping 30 rounds |
| **Ensemble** | Média das probabilidades: `0.5 × P_xgb + 0.5 × P_lgbm` |
| **Split** | Temporal 80/20 por coluna `d` (quando disponível) |
| **Fallback split** | Estratificado aleatório se sem coluna temporal **ou** com menos de 40 linhas |

## API do `BaseTrainer`

| Método | Função |
|--------|--------|
| `fit(df, *, time_col="d", persist=True)` | Treina o ensemble; `persist=False` mantém os modelos só em memória, sem gravar artefatos — usado pelo backtest |
| `predict(X)` | Score com o ensemble em memória do último `fit()` (sem ler joblib) |

### Robustez em datasets pequenos

Cohorts pequenas (ex.: R5 ao nível de fornecedor) não sustentam um split temporal:

- com menos de 40 linhas, o split cai para estratificado aleatório;
- a estratificação só é aplicada se ambas as classes têm > 1 exemplo;
- `eval_set` do XGBoost/LightGBM é omitido quando um fold tem classe única
  (LightGBM falha se `y_va` carrega um label ausente em `y_tr`).

## Fluxo de treino por ruptura

```python
from models.shared.pipeline import RiskPipeline
from models.shared.registry import RuptureCode

pipeline = RiskPipeline()
result = pipeline.train_one(RuptureCode.R1)
# result.metrics → ModelMetrics
# result.n_rows, result.elapsed_s
```

## Métricas de avaliação

`BaseEvaluator` calcula sobre o conjunto de validação:

- **ROC-AUC** — discriminação geral
- **PR-AUC** — relevante em classes desbalanceadas
- **Precision, Recall, F1**
- **Accuracy**
- **positive_rate** — prevalência do target
- **n_train, n_valid** — tamanhos dos conjuntos

Métricas são serializadas em `models/artifacts/<RN>/meta.json`.

## Persistência de artefatos

Após `fit()`:

```
models/artifacts/R1/
├── xgb.joblib      # modelo XGBoost treinado
├── lgbm.joblib     # modelo LightGBM (se ensemble ativo)
└── meta.json       # feature_cols, metrics, config
```

O `meta.json` é a referência para a UI do ML Ops Center (`RiskIntelligenceService.model_metrics`).

## Inferência e batch scoring

`BasePredictor` (`models/shared/base_predictor.py`):

1. Carrega joblibs se existirem.
2. `predict_proba(df)` alinha colunas de `FEATURE_COLS`.
3. Se não treinado → `_heuristic_score()` (z-score + sigmoid).

Cada `Inference` (por ruptura) compõe: feature engineer + predictor + SHAP explainer + `score_batch()`.

## Gold layer

Após treino ou scoring em lote:

```
data/gold/risk_scores/R1/latest.parquet
```

Colunas típicas: `entity_key`, `store_id`, `sku_id` (ou `supplier_id`), coluna `*_risk`, `risk_level`, `probability`.

## Considerações sobre dados sintéticos

No MVP com seed sintético, a prevalência do target pode ser baixa ou zero em alguns cortes — métricas no `meta.json` podem refletir isso (ex.: `positive_rate: 0`). Para demonstrações:

1. Use `python scripts/bootstrap.py --force --full` para histórico mais rico.
2. Verifique cohorts com `python scripts/verify_rupture_seed.py`.
3. Retreine com `python scripts/bootstrap.py --force --train`.

Em produção real, targets viriam de labels operacionais (rupturas confirmadas, tickets, auditorias de inventário).

Para avaliar o desempenho **out-of-time** (não apenas as métricas in-sample do
`meta.json`), use o backtest walk-forward — ver
[prova-de-valor-backtest-e-contrafactual.md](prova-de-valor-backtest-e-contrafactual.md).

## Hiperparâmetros customizados

Passe `TrainingConfig` ao construir um `Trainer` específico:

```python
from models.shared.base_trainer import TrainingConfig

cfg = TrainingConfig(test_size=0.15, use_ensemble=True)
# cfg.xgb_params / cfg.lgbm_params podem ser sobrescritos
```

## Versionamento recomendado (produção)

- Tag em `meta.json`: `model_version`, `trained_at`, hash do dataset.
- Não commitar `models/artifacts/*.joblib` se forem grandes — usar artefato em object storage.
- Manter histórico de `gold/risk_scores/<code>/YYYY-MM-DD.parquet` para auditoria.
