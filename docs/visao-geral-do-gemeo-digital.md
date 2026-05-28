# Visão geral do Gêmeo Digital

## O que é

O **Gêmeo Digital de Varejo** é uma plataforma de inteligência operacional para redes de supermercados. Ela monitora a cadeia de suprimentos em tempo quase real, antecipa **cinco tipos críticos de ruptura** (R1–R5) e oferece interpretação executiva assistida por IA.

Não é um ERP nem um WMS: é uma **camada de observabilidade e predição** que se apoia em um data warehouse analítico (DuckDB) e modelos de machine learning especializados por tipo de ruptura.

## Problema que resolve

Em varejo, rupturas de estoque e falhas na cadeia geram:

- perda de receita (stockout),
- excesso ou falta por promoção mal sinalizada,
- divergência entre estoque sistêmico e físico,
- atrasos de reposição,
- bloqueios comerciais de fornecedores.

A plataforma unifica esses fenômenos em **scores de risco** (0–1) por entidade (loja×SKU ou fornecedor), com níveis operacionais (LOW → CRITICAL) e explicação dos principais drivers.

## Princípio central: modelos prevêm, Groq explica

| Papel | Responsável |
|-------|-------------|
| **Previsão numérica** | Modelos R1–R5 (XGBoost + LightGBM) |
| **Ranking e KPIs** | `RiskIntelligenceService` + DuckDB |
| **Narrativa executiva** | Groq (`llama-3.3-70b-versatile`) via agentes especialistas |

O LLM **não substitui** o modelo: ele interpreta scores, SHAP e contexto operacional já calculados.

## Capacidades principais

1. **Torre de Controle** — visão de rede, health score, alertas e top entidades em risco.
2. **Centros por ruptura (R1–R5)** — observatórios dedicados com ranking e drivers SHAP.
3. **Simulação (gêmeo digital)** — cenários what-if e motor de eventos.
4. **AI Root Cause Analysis** — perguntas em linguagem natural com roteamento de intenção.
5. **ML Operations Center** — treino, métricas e status dos artefatos.

## Stack resumida

- **UI:** Streamlit 1.41
- **Dados:** DuckDB + lake Parquet (bronze / silver / gold)
- **ML:** XGBoost, LightGBM, SHAP
- **LLM:** Groq API (opcional — app funciona sem chave)

## Modos de operação

| Modo | Quando | Comportamento |
|------|--------|----------------|
| **Demonstração local** | Desenvolvimento | Seed completo (~60 dias, 240 SKUs), warehouse em `data/warehouse.duckdb` |
| **Cloud leve** | Streamlit Cloud | Seed reduzido (21 dias), warehouse em `/tmp`, sem dependência de banco pago |
| **Heurístico** | Antes do primeiro treino | Predictor usa fallback estatístico; UI permanece utilizável |

## Próximos passos na documentação

- [Arquitetura e fluxo de dados](arquitetura-e-fluxo-de-dados.md)
- [Catálogo das rupturas R1–R5](catalogo-das-rupturas-r1-r5.md)
