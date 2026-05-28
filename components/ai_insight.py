"""AI insight panel — premium surface for LLM-generated commentary."""
from __future__ import annotations

import streamlit as st


def ai_insight(
    body_md: str, *,
    eyebrow: str = "AI INSIGHT · OPERATIONS COPILOT",
    citation: str | None = None,
) -> None:
    """Render a single AI insight block. `body_md` is rendered as markdown."""
    cite_html = f"<div class='ai-panel__cite'>{citation}</div>" if citation else ""
    container = st.container()
    with container:
        st.markdown(
            f"""<div class="ai-panel">
                  <div class="ai-panel__head"><span class="ai-dot"></span> {eyebrow}</div>
                  <div class="ai-panel__body">{body_md}</div>
                  {cite_html}
                </div>""",
            unsafe_allow_html=True,
        )


def ai_skeleton(lines: int = 3) -> None:
    """Loading state while LLM streams."""
    bars = "".join(f"<div class='shimmer' style='margin-bottom:8px; width:{w}%'></div>"
                   for w in (94, 78, 66)[:lines])
    st.markdown(f"<div class='ai-panel'>{bars}</div>", unsafe_allow_html=True)
