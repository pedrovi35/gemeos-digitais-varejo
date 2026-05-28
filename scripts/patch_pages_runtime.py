#!/usr/bin/env python3
"""One-off patch: unify pages on core.runtime.after_page_config."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / "pages"

REPLACEMENT = (
    "from core.runtime import after_page_config\n"
    "after_page_config()\n"
)

for path in PAGES.glob("*.py"):
    text = path.read_text(encoding="utf-8")
    orig = text

    text = re.sub(
        r"@st\.cache_resource[^\n]*\n(?:.*?\n)*?def _boot\(\):.*?\n(?:.*?\n)*?_boot\(\)\n+",
        "",
        text,
        flags=re.DOTALL,
    )
    text = text.replace(
        "from database.schema import bootstrap_warehouse\nfrom database.seed import seed_warehouse\n",
        "",
    )
    text = text.replace("SessionState.init()\ninject_theme()\n", REPLACEMENT)
    text = text.replace("SessionState.init()\n", "")
    if "inject_theme()\n" in text and "after_page_config" not in text:
        text = text.replace("inject_theme()\n", REPLACEMENT)

    text = re.sub(
        r'st\.set_page_config\(([^)]*?)page_icon="[^"]*"',
        r'st.set_page_config(\1page_icon="assets/favicon.svg"',
        text,
        count=1,
    )

    if text != orig:
        path.write_text(text, encoding="utf-8")
        print("patched", path.name)
