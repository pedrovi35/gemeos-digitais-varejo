# Interface Streamlit e módulos

## Entry point

`app.py` — **Torre de Controle de Ruptura** (home). Executa bootstrap, renderiza KPIs de rede, health score, feed de alertas e navegação para módulos especializados.

```bash
cd project
streamlit run app.py
```

URL local: **http://localhost:8501**

## Mapa de páginas

### Torre e inteligência geral

| Arquivo | Módulo |
|---------|--------|
| `0_🗼_Rupture_Control_Tower.py` | Torre alternativa / KPIs executivos |
| `1_🚨_Rupture_Intelligence.py` | Inteligência consolidada de ruptura |
| `3_🌐_Supply_Chain_Observatory.py` | Observatório da cadeia |
| `5_📡_Operational_Timeline.py` | Linha do tempo operacional |
| `6_📦_Inventory_Health.py` | Saúde de inventário |
| `7_🔗_Supplier_Risk_Center.py` | Risco de fornecedores (visão rede) |

### Centros por modelo (R1–R5)

| Arquivo | Ruptura |
|---------|---------|
| `11_📦_R1_Inventory_Break_Center.py` | R1 Quebra de inventário |
| `12_📈_R2_Demand_Spike_Observatory.py` | R2 Demanda anormal |
| `13_🏷️_R3_Promotion_Intelligence.py` | R3 Promoção não sinalizada |
| `14_🚚_R4_Lead_Time_Risk_Center.py` | R4 Lead time |
| `15_🔒_R5_Supplier_Restriction_Center.py` | R5 Restrição faturamento |

### Simulação e IA

| Arquivo | Módulo |
|---------|--------|
| `2_🧪_Digital_Twin_Simulation.py` | Gêmeo digital / what-if |
| `4_🤖_AI_Root_Cause_Analysis.py` | Chat Groq + RCA |
| `8_🧪_Prova_de_Valor.py` | Backtest walk-forward + contrafactual de intervenção |

### Operações ML e sistema

| Arquivo | Módulo |
|---------|--------|
| `20_⚙️_ML_Operations_Center.py` | Treino, métricas, status artefatos |
| `99_🛠️_System_Console.py` | Health checks, logs, diagnóstico |

## Componentes reutilizáveis (`components/`)

| Componente | Uso |
|------------|-----|
| `kpi_card.py` | Cartões de métrica |
| `risk_card.py` | Card de entidade em risco |
| `status_badge.py` | Badge LOW/HIGH/CRITICAL |
| `data_grid.py` | Tabelas operacionais |
| `network_graph.py` | Grafo supply chain |
| `calibration_chart.py` | Diagnósticos de calibração: reliability diagram, lead time, precision@k |
| `analysis_report.py` | Relatório de análise IA |
| `rupture_center.py` | Layout padrão dos centros R* |
| `global_filters.py` | Filtros loja / período |
| `loading.py` / `fallback.py` | UX de carregamento e erro |

## Runtime compartilhado

`core/runtime.py` — helpers de página (título, filtros, checagem de bootstrap).

Padrão típico em cada `pages/*.py`:

1. Importar `ensure_runtime()` ou bootstrap equivalente.
2. Obter `get_risk_service()` ou serviço de domínio.
3. Aplicar filtros globais da sessão.
4. Renderizar visualizações Plotly + componentes.

## Tema e branding

- Configuração: `.streamlit/config.toml` (tema dark enterprise).
- Assets: `assets/` (CSS customizado, favicon).

## Filtros globais

`components/global_filters.py` persiste em `st.session_state`:

- `store_id` (opcional — visão rede inteira),
- janela temporal quando aplicável.

Serviços respeitam `store_id` em `tower_summary`, `operational_ranking` e `composite_matrix`.

## ML Operations Center

Permite ao usuário:

- disparar treino (`train_all` / `train_one`),
- visualizar métricas de `meta.json`,
- verificar freshness do feature store e gold layer.

Útil após `bootstrap --train` ou atualização de seed.

## System Console

Diagnóstico para desenvolvedores:

- status do warehouse,
- paths do lake,
- variáveis de ambiente (mascaradas),
- validações rápidas.

## Extensão: nova página

1. Criar `pages/NN_🔖_Nome.py` (prefixo numérico define ordem no menu).
2. Reutilizar `rupture_center` ou `exec_header` se for centro analítico.
3. Consumir `RiskIntelligenceService` — não chamar modelos diretamente da UI.
4. Documentar a página neste arquivo.
