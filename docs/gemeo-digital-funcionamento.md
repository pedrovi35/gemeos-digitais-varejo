# Gêmeo Digital — como funciona

Este documento descreve **o que é o gêmeo digital da plataforma e como ele
opera por dentro**: as três formas em que o "gêmeo" se manifesta, o motor de
simulação de eventos discretos e o projetor what-if.

## A ideia

Um gêmeo digital é uma réplica computacional da operação real que permite
**observar, prever e experimentar** sem tocar na loja física. Nesta plataforma
o gêmeo não é um único objeto — ele aparece em três camadas complementares:

| Camada | O que replica | Direção no tempo | Onde vive |
|--------|---------------|------------------|-----------|
| **Gêmeo de estado** | A operação como está agora | Presente | Warehouse DuckDB + scores R1–R5 |
| **Gêmeo de simulação** | Como a operação evoluiria sob um cenário | Futuro | `simulation/` (motor de eventos) |
| **Gêmeo contrafactual** | O que teria acontecido com/sem intervenção | Passado | `services/backtest_service.py` + `counterfactual_service.py` |

As duas primeiras estão descritas aqui. A terceira tem documento próprio:
[prova-de-valor-backtest-e-contrafactual.md](prova-de-valor-backtest-e-contrafactual.md).

---

## 1. Gêmeo de estado

É o "espelho" da rede no instante atual. O warehouse DuckDB (`fct_*`, `dim_*`,
`mart_*`) carrega o estado de inventário, vendas, reposição e fornecedores; os
cinco modelos R1–R5 transformam esse estado em **scores de risco** por entidade
(loja×SKU ou fornecedor). A Torre de Controle e os centros por ruptura leem esse
gêmeo de estado — ele responde "como estamos agora e o que está em risco".

Detalhes em [pipeline-de-machine-learning.md](pipeline-de-machine-learning.md)
e [arquitetura-e-fluxo-de-dados.md](arquitetura-e-fluxo-de-dados.md).

---

## 2. Gêmeo de simulação

Quando o usuário quer responder *"e se?"*, o gêmeo de simulação projeta o futuro.
Há dois motores, escolhidos pelo custo computacional aceitável:

### 2a. Projetor what-if (forma fechada)

`analytics/what_if.py` — `WhatIfAnalytics.project()`. Um projetor **closed-form**
(fórmula direta, sem laço de simulação) — rápido o suficiente para reagir a
sliders em tempo real.

Entradas: service level e stockout de baseline, receita diária, e os parâmetros
de stress (`demand_shock`, `supply_otd`, `lead_time_days`, `horizon_days`).

Lógica:

```
penalidade_SL = (demand_shock − 1.0)·0.04 + (0.95 − supply_otd)·0.30
SL_projetado  = baseline_SL − penalidade_SL
ruptura       = baseline_stockout + penalidade_SL·1.2 + max(0, lead_time−3)·0.005
perda         = receita_diária · ruptura_projetada · horizonte
```

Retorna `WhatIfResult` com baseline vs projetado e uma `confidence` fixa de 0,82.

### 2b. Motor de eventos discretos

`simulation/engine.py` — `SimulationEngine`. Uma simulação **discrete-event**:
o tempo avança em *ticks* e, a cada tick, demanda e oferta são amostradas
estocasticamente, alterando o inventário e disparando eventos.

Componentes:

| Módulo | Papel |
|--------|-------|
| `clock.py` · `SimulationClock` | Relógio discreto — passo de 15 min, avança via `tick()` |
| `demand_model.py` · `DemandModel` | Demanda estocástica — Poisson composto com sazonalidade dia-da-semana × hora, classe de velocidade (A/B/C), `promo_lift` e `shock_multiplier` |
| `supply_model.py` · `SupplyModel` | Lead time (normal), `otd_rate` e penalidade de disrupção |
| `scenarios.py` · `ScenarioCatalog` | Catálogo de cenários nomeados (ver abaixo) |
| `event_bus.py` · `EventBus` | Pub/sub singleton — desacopla quem emite de quem consome eventos |
| `engine.py` · `SimulationEngine` | Orquestra relógio + modelos + cenário, escreve no warehouse e nos serviços |

**Laço de tick** (`SimulationEngine.tick()`):

1. avança o relógio (`clock.tick()`);
2. lê o snapshot vivo de inventário (`InventoryService.live_snapshot()`);
3. amostra até 40 linhas e, para cada loja×SKU, gera a venda do período via
   `DemandModel.sample(dow, hour, velocity)`;
4. abate `on_hand`, reclassifica o status (`OK` / `CRITICAL` / `STOCKOUT`) e
   grava de volta em `fct_inventory_snapshot`;
5. publica eventos (`SALE`, `STOCKOUT_DETECTED`, `REORDER_TRIGGER`) no event bus
   e nos serviços de evento/alerta;
6. acumula `EngineStats` (ticks, eventos, stockouts, reorders).

`run(ticks=24)` executa o laço; `reset()` zera estatísticas, relógio e cenário.

### Catálogo de cenários

`ScenarioCatalog` (`simulation/scenarios.py`) define stress tests repetíveis.
Cada `Scenario` carrega `demand_overrides` / `supply_overrides` que
`apply_scenario()` injeta nos modelos:

| Código | Cenário | Efeito |
|--------|---------|--------|
| `BASELINE` | Operação normal | Referência, sem overrides |
| `SUPPLIER_OUT` | Disrupção crítica de fornecedor T1 | OTD cai para 0,55 por 96h |
| `DEMAND_SPIKE` | Pico promocional (Black Friday) | Demanda 2,2× por 72h |
| `HEATWAVE` | Onda de calor | Demanda 1,8× por 120h |
| `LOG_STRIKE` | Greve de transporte | OTD 0,60 + penalidade de lead time por 48h |

---

## 3. Interface: a página de simulação

`pages/2_🧪_Digital_Twin_Simulation.py` — o *Simulation Lab*. Fluxo da tela:

1. usuário escolhe um cenário do catálogo e ajusta os sliders de stress
   (multiplicador de demanda, OTD, lead time, horizonte);
2. o **projetor what-if** roda na hora e exibe KPIs baseline vs projetado
   (service level, ruptura, perda de receita estimada);
3. o botão **"Rodar simulação (24 ticks)"** aciona o `SimulationEngine`:
   aplica o cenário e executa o laço de eventos discretos;
4. opcionalmente, o `OperationsCopilot` gera um **briefing executivo** via Groq
   interpretando a projeção (princípio "modelos prevêem, LLM explica").

O `SimulationAgent` (`agents/simulation_agent.py`) permite perguntas em
linguagem natural sobre a projeção — ele monta o contexto operacional geral e
anexa os parâmetros do cenário antes de chamar o LLM.

---

## Como os três gêmeos se conectam

```
        PASSADO                PRESENTE                FUTURO
   ┌──────────────┐      ┌──────────────────┐    ┌──────────────────┐
   │  Contrafactual│      │ Gêmeo de estado  │    │ Gêmeo de simulação│
   │  (backtest)   │      │ warehouse + R1–R5│    │ what-if / eventos │
   └──────┬───────┘      └────────┬─────────┘    └─────────┬────────┘
          │                       │                        │
     mede o valor          mostra o risco            projeta o impacto
     da intervenção         agora                    de um cenário
```

- O **gêmeo de estado** alimenta os modelos com a realidade corrente.
- O **gêmeo de simulação** parte desse estado e o empurra para a frente sob um
  cenário de stress.
- O **gêmeo contrafactual** valida, no passado, se as previsões teriam de fato
  gerado valor — fechando o ciclo de confiança.

## Limitações atuais

- O motor de eventos discretos escreve direto em `fct_inventory_snapshot`; rode
  com seed dedicada ou após backup se quiser preservar o estado do warehouse.
- O projetor what-if é uma forma fechada calibrada por heurística — bom para
  comparação relativa de cenários, não para previsão absoluta.
- A `confidence` do `WhatIfResult` é fixa (0,82), não derivada dos dados.
