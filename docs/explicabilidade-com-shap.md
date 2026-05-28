# Explicabilidade com SHAP

## Objetivo

Operadores e gestores precisam saber **por que** um SKU ou fornecedor está em risco — não apenas o número. A plataforma expõe **drivers causais** com impacto percentual via SHAP (SHapley Additive exPlanations).

## Implementação

`BaseShapExplainer` (`models/shared/base_shap_explainer.py`):

1. Carrega `xgb.joblib` do artefato da ruptura.
2. Tenta instanciar `shap.TreeExplainer` sobre o XGBoost.
3. Para uma linha de features, calcula contribuições SHAP.
4. Converte em lista de `FeatureContribution` (schemas).

### Estrutura `FeatureContribution`

| Campo | Significado |
|-------|-------------|
| `feature` | Nome da variável |
| `value` | Valor observado na entidade |
| `shap` | Contribuição SHAP (signed) |
| `impact_pct` | % do total \|SHAP\| (com sinal) |

### Estrutura `RiskExplanation`

Agrega score, nível, `top_drivers`, contrafactuais opcionais, narrativa (preenchida pelo agente Groq) e `confidence`.

## Fallback sem SHAP

Se a biblioteca SHAP não estiver disponível ou o modelo não carregar:

- usa `feature_importances_` do XGBoost,
- escala pela magnitude do desvio da feature em relação à média.

Assim a UI de explainability **nunca fica vazia** em ambiente restrito.

## Uso na API

```python
from services.risk_service import get_risk_service

svc = get_risk_service()
explanation = svc.explain("R1", {"store_id": "ST-001", "sku_id": "SKU-042"})
for d in explanation.top_drivers:
    print(d.feature, d.impact_pct)
```

## Integração com Groq

O agente `OperationalMLAgent` consome scores + drivers SHAP e produz narrativa executiva. O LLM **não recalcula** o score — apenas interpreta evidências numéricas.

Perguntas típicas roteadas para `Intent.ML_INTERPRETATION`:

- “Por que o SKU X está em risco R1?”
- “Explique o SHAP do fornecedor SUP-007”
- “Qual driver mais impacta R4 na loja ST-002?”

## Leitura operacional dos drivers

| Sinal SHAP | Interpretação sugerida |
|------------|------------------------|
| `stock_difference` positivo alto | Divergência sistêmica vs físico piorando o score |
| `demand_spike_score` positivo | Pico de demanda empurra risco R2 |
| `unexpected_demand_ratio` | Promo não cadastrada (R3) |
| `logistics_delay_score` | Atraso logístico composto (R4) |
| `invoice_rejection_rate` | Stress financeiro do fornecedor (R5) |

## Limitações

- SHAP TreeExplainer é local e depende da árvore XGBoost (metade do ensemble); LightGBM não entra diretamente na explicação.
- Em modo heurístico, drivers refletem importâncias aproximadas, não SHAP verdadeiro.
- Contrafactuais são heurísticos no MVP — evolução natural: integrar bibliotecas de counterfactual ML.

## Onde ver na UI

- Centros R1–R5 — painéis de drivers por entidade selecionada.
- **AI Root Cause Analysis** — combina SHAP + contexto DuckDB + Groq.
- **ML Operations Center** — status de artefatos e métricas globais.
