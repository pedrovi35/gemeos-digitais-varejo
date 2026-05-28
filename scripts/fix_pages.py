from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT / "pages").glob("*.py"):
    t = p.read_text(encoding="utf-8")
    o = t
    if "after_page_config" not in t:
        t = t.replace(
            "SessionState.init()\ninject_theme()\n",
            "from core.runtime import after_page_config\nafter_page_config()\n",
        )
    t = t.replace("SessionState.init()\n", "")
    t = t.replace("inject_theme()\n", "")
    if "layout=\"wide\")" in t and "favicon" not in t.split("set_page_config")[1][:200]:
        t = t.replace(
            'layout="wide")',
            'page_icon="assets/favicon.svg", layout="wide")',
            1,
        )
    if t != o:
        p.write_text(t, encoding="utf-8")
        print("fixed", p.name)
