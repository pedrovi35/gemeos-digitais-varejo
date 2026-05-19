"""
Hardened Groq client — retries, structured output helpers, tracing hooks.

The client never raises uncaught; it returns a structured fallback so the
UI degrades gracefully when GROQ_API_KEY is missing or the API errors.
"""
from __future__ import annotations

import time
from collections.abc import Iterator

from groq import Groq

from config.logging import logger
from config.settings import settings


class GroqClient:

    def __init__(self) -> None:
        if not settings.groq.api_key:
            logger.warning("GROQ_API_KEY missing — AI layer in offline mode")
            self.client: Groq | None = None
        else:
            self.client = Groq(api_key=settings.groq.api_key, timeout=settings.groq.timeout)

    @property
    def online(self) -> bool:
        return self.client is not None

    # ── Core call (with retries) ────────────────────────────────────
    def complete(
        self, messages: list[dict], *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        retries: int = 2, retry_backoff: float = 0.8,
    ) -> str:
        if not self.online:
            return self._offline_response(messages)

        last_err: Exception | None = None
        for attempt in range(retries + 1):
            try:
                resp = self.client.chat.completions.create(
                    model=settings.groq.model,
                    messages=messages,
                    temperature=temperature if temperature is not None else settings.groq.temperature,
                    max_tokens=max_tokens or settings.groq.max_tokens,
                )
                content = resp.choices[0].message.content or ""
                logger.debug(f"groq · attempt={attempt+1} tokens~={len(content)//4}")
                return content
            except Exception as e:                           # pragma: no cover
                last_err = e
                logger.warning(f"groq attempt {attempt+1}/{retries+1} failed: {e}")
                if attempt < retries:
                    time.sleep(retry_backoff * (attempt + 1))

        logger.error(f"groq exhausted retries: {last_err}")
        return self._error_response(str(last_err))

    # ── Streaming ───────────────────────────────────────────────────
    def stream(self, messages: list[dict], *, temperature: float | None = None) -> Iterator[str]:
        if not self.online:
            yield self._offline_response(messages)
            return
        try:
            stream = self.client.chat.completions.create(
                model=settings.groq.model,
                messages=messages,
                temperature=temperature if temperature is not None else settings.groq.temperature,
                max_tokens=settings.groq.max_tokens, stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:                              # pragma: no cover
            logger.exception(f"groq stream failed: {e}")
            yield self._error_response(str(e))

    # ── Constrained classification ─────────────────────────────────
    def classify(self, system: str, query: str, allowed: list[str],
                 fallback: str) -> str:
        """Return one of `allowed` labels. Deterministic temperature."""
        if not self.online:
            return fallback
        try:
            raw = self.complete(
                [{"role": "system", "content": system},
                 {"role": "user", "content": query}],
                temperature=0.0, max_tokens=12,
            ).strip().upper()
            for lbl in allowed:
                if lbl in raw:
                    return lbl
        except Exception as e:                              # pragma: no cover
            logger.warning(f"classify failed: {e}")
        return fallback

    # ── Fallbacks ──────────────────────────────────────────────────
    @staticmethod
    def _offline_response(messages: list[dict]) -> str:
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        return (
            "**[Modo offline]** A camada de IA Operacional está sem `GROQ_API_KEY` configurada.\n\n"
            "### Resumo executivo\n"
            "Resposta não disponível — defina a chave de API para ativar a análise via LLM.\n\n"
            f"### Pergunta recebida\n_{last_user[:240]}…_\n\n"
            "### Recomendação operacional\n"
            "1. **P1 · Plataforma** — configurar `GROQ_API_KEY` em `.env` _(janela: 5min)_.\n"
        )

    @staticmethod
    def _error_response(err: str) -> str:
        return (
            "### Resumo executivo\n"
            "A análise falhou por instabilidade da API. O contexto operacional foi carregado, "
            "mas o LLM não respondeu dentro do timeout.\n\n"
            f"### Detalhe\n```\n{err[:300]}\n```\n\n"
            "### Recomendação\nReexecute em alguns segundos ou verifique conectividade."
        )
