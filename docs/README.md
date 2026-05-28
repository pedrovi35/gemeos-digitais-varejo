# Documentação · Gêmeo Digital de Varejo

Guia completo da plataforma de inteligência operacional para supply chain de supermercados.

## Índice

| Documento | Conteúdo |
|-----------|----------|
| [Visão geral do Gêmeo Digital](visao-geral-do-gemeo-digital.md) | O que é a plataforma, objetivos e capacidades |
| [Gêmeo Digital — como funciona](gemeo-digital-funcionamento.md) | As três camadas do gêmeo, motor de simulação e projetor what-if |
| [Arquitetura e fluxo de dados](arquitetura-e-fluxo-de-dados.md) | Camadas, módulos e pipeline end-to-end |
| [Catálogo das rupturas R1–R5](catalogo-das-rupturas-r1-r5.md) | Definição operacional de cada tipo de ruptura |
| [Pipeline de machine learning](pipeline-de-machine-learning.md) | Treino, scoring, gold layer e serviço de risco |
| [Engenharia de features](engenharia-de-features.md) | Variáveis, targets e lógica por modelo |
| [Treinamento, avaliação e artefatos](treinamento-avaliacao-e-artefatos.md) | Ensemble XGBoost + LightGBM, métricas e fallback |
| [Explicabilidade com SHAP](explicabilidade-com-shap.md) | Drivers causais e interpretação de scores |
| [Prova de valor: backtest e contrafactual](prova-de-valor-backtest-e-contrafactual.md) | Backtest walk-forward, simulador contrafactual e calibração |
| [Camada de dados e seed sintético](camada-de-dados-e-seed-sintetico.md) | DuckDB, lake Parquet e cohorts R1–R5 |
| [Camada de inteligência Groq](camada-de-inteligencia-groq.md) | Agentes, roteamento e princípio “ML prevê, LLM explica” |
| [Interface Streamlit e módulos](interface-streamlit-e-modulos.md) | Páginas, torre de controle e ML Ops |
| [Glossário operacional](glossario-operacional.md) | Termos de negócio e técnica |
| [Roteiro de apresentação](apresentacao-do-sistema.md) | Fala de apresentação + demo guiada da interface Streamlit |

## Documentação relacionada

- [ARCHITECTURE.md](../ARCHITECTURE.md) — resumo técnico da arquitetura
- [README.md](../README.md) — setup, deploy e scripts
- [DEPLOY.md](../DEPLOY.md) — Streamlit Cloud

## Público-alvo

- **Operações / supply chain** — entender rupturas e KPIs
- **Ciência de dados** — features, treino e explainability
- **Engenharia** — bootstrap, warehouse e integração
