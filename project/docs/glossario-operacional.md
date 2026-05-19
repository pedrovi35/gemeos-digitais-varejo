# Glossário operacional

Termos usados na plataforma, na documentação e nas telas Streamlit.

## Negócio · Supply chain

| Termo | Definição |
|-------|-----------|
| **Ruptura** | Falha na continuidade de abastecimento ou venda — stockout, divergência, atraso, etc. |
| **R1–R5** | Cinco tipos modelados de ruptura (ver [catálogo](catalogo-das-rupturas-r1-r5.md)). |
| **Torre de controle** | Visão executiva consolidada de KPIs e riscos da rede. |
| **Gêmeo digital** | Representação simulada da operação para cenários what-if. |
| **OTD** | On-Time Delivery — entregas no prazo. |
| **Lead time** | Tempo entre pedido e entrega. |
| **Days of cover** | Dias de estoque estimados com base na demanda. |
| **Fill rate** | Taxa de atendimento da demanda com estoque disponível. |
| **Service level** | Nível de serviço ao cliente (disponibilidade). |
| **Stockout** | Situação sem estoque vendável. |
| **Shrinkage** | Perda de mercadoria (quebra, furto, ajuste negativo). |
| **Uplift** | Aumento de vendas acima do baseline. |
| **Promoção sinalizada** | Campanha registrada no calendário comercial / supply. |

## Técnica · Dados

| Termo | Definição |
|-------|-----------|
| **Warehouse** | Banco analítico DuckDB (`warehouse.duckdb`). |
| **Medallion** | Padrão bronze → silver → gold em Parquet. |
| **Gold layer** | Camada curada; inclui `risk_scores` dos modelos. |
| **Feature store** | Cache Parquet de features engenheiradas por ruptura. |
| **Cohort** | Subconjunto de SKUs/fornecedores com assinatura de ruptura no seed. |
| **Entity key** | Identificador único da entidade scored (`ST-001·SKU-042` ou `SUP-007`). |

## Técnica · Machine learning

| Termo | Definição |
|-------|-----------|
| **Score de risco** | Probabilidade ou índice em [0, 1] de evento adverso. |
| **Target** | Variável binária que o modelo aprende a prever. |
| **Horizonte** | Janela futura (default 7 dias) para definir o target. |
| **Ensemble** | Combinação XGBoost + LightGBM (média de probabilidades). |
| **Artefato** | Arquivo `.joblib` ou `meta.json` persistido após treino. |
| **Heuristic mode** | Scoring sem modelo treinado (fallback estatístico). |
| **SHAP** | Valores de contribuição por feature para uma predição. |
| **ROC-AUC** | Área sob curva ROC — qualidade de ranking do classificador. |
| **Split temporal** | Treino em passado, validação em futuro (evita leakage). |

## Técnica · Plataforma

| Termo | Definição |
|-------|-----------|
| **Bootstrap** | Script de init: schema + seed + validação (+ treino opcional). |
| **Light seed** | Seed reduzido para ambientes com pouca memória (Cloud). |
| **Graceful degradation** | App continua sem Groq ou sem ML treinado. |
| **Intent** | Classificação da pergunta do usuário para roteamento de agente. |
| **RiskIntelligenceService** | API unificada de scores e explicações na UI. |

## Siglas de páginas

| Sigla | Página |
|-------|--------|
| RCA | Root Cause Analysis (`AI_Root_Cause_Analysis`) |
| ML Ops | ML Operations Center |
| OBS | Supply Chain Observatory |

## Mapeamento coluna → ruptura

| Coluna | Ruptura |
|--------|---------|
| `inventory_break_risk` | R1 |
| `above_average_sales_risk` | R2 |
| `unsignaled_promotion_risk` | R3 |
| `purchase_delivery_risk` | R4 |
| `supplier_billing_restriction_risk` | R5 |
