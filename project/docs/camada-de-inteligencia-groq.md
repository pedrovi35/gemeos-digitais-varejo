# Camada de inteligência Groq

## Papel na arquitetura

A API Groq alimenta a **camada interpretativa** — transforma evidências já calculadas (SQL, scores ML, SHAP) em linguagem natural para gestores.

> **Regra de ouro:** modelos R1–R5 prevêm; Groq explica.

Sem `GROQ_API_KEY`, a aplicação continua funcional: torre, rankings e gráficos ML permanecem; apenas respostas em linguagem natural ficam indisponíveis ou simplificadas.

## Fachada: `AIService`

Arquivo: `agents/ai_service.py`

### Pipeline de uma pergunta

```
query do usuário
    → guardrails
    → route() — heurísticas regex + classificador LLM
    → agente especialista
    → AnalysisResponse
    → memória de sessão (Turn)
```

### Roteamento heurístico (exemplos)

| Padrão na pergunta | Intent |
|--------------------|--------|
| ruptura, stockout, sem estoque | `RUPTURE_INVESTIGATION` |
| causa raiz, por que | `ROOT_CAUSE` |
| forecast, previsão, MAPE | `FORECAST_INSIGHT` |
| e se, what-if, simulação | `SIMULATION_WHATIF` |
| fornecedor, OTD, lead time | `SUPPLIER_ANALYSIS` |
| SHAP, modelo, risco R1–R5 | `ML_INTERPRETATION` |
| (fallback) | `GENERAL_OPS` |

Se heurísticas não casarem, `GroqClient.classify()` usa prompt `SystemPrompts.INTENT_ROUTER`.

## Agentes especialistas

| Agente | Intent | Função |
|--------|--------|--------|
| `RuptureAgent` | Rupture / Root Cause | Investigação de ruptura com dossier SQL |
| `ForecastingAgent` | Forecast | Insights de previsão e drift |
| `SimulationAgent` | What-if | Cenários do gêmeo digital |
| `SupplierAgent` | Supplier | Análise de fornecedor e OTD |
| `OperationalAgent` | General Ops | Perguntas operacionais amplas |
| `OperationalMLAgent` | ML Interpretation | Explica scores e drivers SHAP |

Cada agente monta contexto a partir do DuckDB (`agents/ml_context_loader.py` e queries dedicadas) antes de chamar o LLM.

## Modelo LLM

Configurado via settings (default típico):

- **Modelo:** `llama-3.3-70b-versatile`
- **Cliente:** `agents/groq_client.py`

## Schemas de resposta

`agents/schemas.py` define estruturas tipadas (Pydantic), incluindo:

- `AnalysisResponse` — texto, confidence, fontes, ações sugeridas
- `Intent` — enum de intenções
- `Confidence` — LOW / MEDIUM / HIGH

## Uso na UI

```python
from agents.ai_service import AIService

svc = AIService()
resp = svc.analyze(
    "Por que o leite está em risco de ruptura na ST-001?",
    scope={"store_id": "ST-001"},
    session_id="ui:session-1",
)
print(resp.answer)
```

Página principal: `pages/4_🤖_AI_Root_Cause_Analysis.py`

## Memória de conversa

`agents/memory.py` mantém turns por `session_id` para continuidade em perguntas de follow-up dentro da mesma sessão Streamlit.

## Segurança e guardrails

- Classificador pode rotear perguntas inadequadas para `Intent.UNSAFE` (quando implementado).
- Não enviar PII ou segredos nos prompts — usar apenas IDs operacionais (store_id, sku_id).
- Chave API apenas em `.env` ou Streamlit secrets — nunca no repositório.

## Configuração

```env
GROQ_API_KEY=gsk_...
```

Streamlit Cloud (`secrets.toml`):

```toml
GROQ_API_KEY = "gsk_..."
```

## Boas práticas para prompts de negócio

1. Sempre anexar **números** (score, nível, top 3 drivers) ao contexto do LLM.
2. Pedir respostas curtas, acionáveis, com próximo passo operacional.
3. Evitar que o modelo “invente” KPIs — usar apenas o dossier fornecido.
