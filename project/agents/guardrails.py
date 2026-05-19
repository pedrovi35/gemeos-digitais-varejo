"""
Guardrails — input and output validation.

We do not let the model generate arbitrary SQL. SQL generation is *constrained*
to a curated library of parameterized templates (see context_loader). The
guardrails module here covers:

  • prompt-injection / jailbreak detection (best-effort)
  • PII redaction in echoed user input
  • output length & shape validation
"""
from __future__ import annotations

import re

from agents.schemas import Intent


_INJECTION_PATTERNS = (
    r"ignore (?:all|previous|above)",
    r"disregard (?:the|all) (?:system|instructions)",
    r"reveal (?:the|your) (?:system|prompt)",
    r"act as (?:a )?(?:dan|developer|jailbreak)",
    r"```\s*(?:system|assistant)\s*",
)

_UNSAFE_INTENTS = (
    r"\bdrop\s+table\b", r"\btruncate\b", r"\bdelete\s+from\b",
    r"\balter\s+system\b", r"sql.injection",
)

_CNPJ_RE = re.compile(r"\d{2}\.?\d{3}\.?\d{3}\/?\d{4}-?\d{2}")
_CPF_RE  = re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}")
_EMAIL_RE= re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")


def detect_injection(text: str) -> bool:
    lo = text.lower()
    return any(re.search(p, lo) for p in _INJECTION_PATTERNS)


def is_destructive(text: str) -> bool:
    lo = text.lower()
    return any(re.search(p, lo) for p in _UNSAFE_INTENTS)


def classify_safety(query: str) -> Intent | None:
    """Return Intent.UNSAFE if the input must be blocked, else None."""
    if not query or not query.strip():
        return Intent.UNSAFE
    if len(query) > 2000:
        return Intent.UNSAFE
    if detect_injection(query) or is_destructive(query):
        return Intent.UNSAFE
    return None


def redact_pii(text: str) -> str:
    text = _CNPJ_RE.sub("[CNPJ]", text)
    text = _CPF_RE.sub("[CPF]", text)
    text = _EMAIL_RE.sub("[EMAIL]", text)
    return text


def truncate(text: str, max_chars: int = 4000) -> str:
    return text if len(text) <= max_chars else text[: max_chars - 1] + "…"
