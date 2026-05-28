# Prova de valor: backtest e contrafactual

A página **Prova de Valor** (`pages/8_🧪_Prova_de_Valor.py`) é um experimento
controlado que mede o que o gêmeo digital *teria evitado* numa janela de tempo
que ele **nunca viu durante o treino**. Responde a três perguntas:

1. **Validade preditiva** — o modelo acerta fora da janela de treino? (AUC out-of-time, precision@k)
2. **Calibração** — quando o modelo diz "risco 0,7", a ruptura ocorre ~70% das vezes?
3. **Valor operacional** — quantas rupturas e quantos R$ a intervenção evita, e qual o ROI?

## Metodologia walk-forward

Para uma data de corte `T` e um horizonte `H`:

```
1. FE.build(cutoff_ts=T)      → features observáveis apenas até T (sem leakage)
2. Trainer.fit(df, persist=False) → modelo treinado em memória (não toca artefatos de produção)
3. score entidades em T       → risco da linha de feature mais recente por entidade
4. join com eventos reais em (T, T+H]  → labels nunca vistos no treino
5. métricas out-of-time       → AUC, average precision, precision@k, lead time
```

Como os labels vêm da janela **posterior** ao corte, a AUC resultante é uma
métrica preditiva honesta — não há contaminação do passado pelo futuro.

### Corte de tempo (`cutoff_ts`)

O backtest depende de o feature engineering respeitar o corte:

- `BaseFeatureEngineering._cutoff_ts` é definido por `build(cutoff_ts=...)`.
- `BaseFeatureEngineering.df()` reescreve todo `CURRENT_TIMESTAMP` no SQL para o
  instante fixo do corte — janelas de feature contêm só dados observáveis até `T`.
- `trim_to_cutoff()` descarta linhas cuja data-âncora (`d`) ultrapasse o corte.

Em produção (sem `cutoff_ts`) o comportamento é inalterado: `build()` usa o tempo real.

## Camada de serviço

### `services/backtest_service.py`

| Função | Saída |
|--------|-------|
| `score_window(code, cutoff, horizon)` | `ScoreWindow` — frame por entidade: `risk`, `realized`, `realized_date`, `lead_days`, `daily_revenue` |
| `daily_revenue_by_entity(code, cutoff)` | Receita diária média por entidade nos 28 dias antes do corte (monetiza rupturas) |
| `score_window_cached(...)` | Versão com `lru_cache` para a UI Streamlit |

`score_window` retorna `None` quando não há dados suficientes para treinar no corte
(menos de 2 eventos positivos).

### `services/counterfactual_service.py`

Compara dois universos paralelos para o mesmo `(ruptura, corte, horizonte)`:

- **Universo A — Baseline.** O gêmeo não age. Rupturas e perda vêm direto do warehouse.
- **Universo B — Gêmeo age.** O gêmeo alerta nas top-k entidades de maior risco. Cada
  alerta correto previne a ruptura com probabilidade `effectiveness`; falsos positivos
  são cobrados como custo de intervenção desperdiçada.

| Função | Uso |
|--------|-----|
| `simulate(code, cutoff, horizon, *, top_k, risk_threshold, effectiveness, intervention_unit_cost)` | Um contrafactual → `CounterfactualResult` |
| `aggregate(results)` | Soma deltas entre cortes/rupturas num único bloco de KPIs |

`CounterfactualResult` traz os deltas: `events_avoided`, `revenue_saved`,
`intervention_cost`, `net_value` (= saved − cost) e `avoidance_rate`, além do
frame `scored` por entidade para drill-down.

Fórmula central: `prevenções esperadas = (alertas corretos) × effectiveness`;
`perda evitada = receita_diária × horizonte × prevenções`.

## Diagnósticos de calibração (`components/calibration_chart.py`)

Três gráficos Plotly que consomem o frame de `score_window`:

| Função | Gráfico |
|--------|---------|
| `reliability_diagram(scored)` | Risco predito (decis) vs taxa real de ruptura — calibração perfeita = diagonal y=x |
| `lead_time_distribution(scored)` | Histograma de dias entre o alerta e a ruptura (quanto tempo de antecedência) |
| `precision_at_k_curve(scored)` | Precisão dos top-k de maior risco vs taxa-base — qualidade do ranking operacional |

## CLI: `scripts/backtest.py`

Backtest walk-forward em linha de comando, em múltiplos cortes:

```bash
python scripts/backtest.py                          # R1–R5, horizonte 7d
python scripts/backtest.py --rupture R1             # uma ruptura
python scripts/backtest.py --horizon 7 --cutoffs 35 28 21
```

Gera tabela resumo (AUC out-of-time, average precision, precision@10) e salva
`data/backtest_results.json`.

## Estado atual dos modelos

No backtest com o seed sintético, apenas **R1** e **R4** generalizam out-of-time
(AUC ≥ 0,65). R2/R3/R5 são exibidos para transparência mas precisam de mais
histórico ou redesenho de target — ver as redefinições de target em
[engenharia-de-features.md](engenharia-de-features.md), que removeram o
*target-leak* que inflava a AUC in-sample.

## Limitações

- **Dados sintéticos.** A "verdade" da prova vem do seed determinístico
  (`database/seed.py`). A mesma metodologia roda em produção com dados reais
  sem mudar o pipeline — só os números mudam.
- **Custo de intervenção** é um proxy operacional editável na barra lateral.
- **Eficácia** parametriza a fração de alertas que viram ação bem-sucedida
  (estudos de campo em varejo: 0,55–0,80).
