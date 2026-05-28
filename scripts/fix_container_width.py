"""Replace deprecated use_container_width with Streamlit 1.41+ width parameter."""
import pathlib

root = pathlib.Path(__file__).parent.parent
replacements = [
    ("use_container_width=True", "width='stretch'"),
    ("use_container_width=False", "width='content'"),
]

changed = []
for f in root.rglob("*.py"):
    parts = f.parts
    if any(p in parts for p in (".venv", "__pycache__", ".git", "scripts")):
        continue
    try:
        txt = f.read_text(encoding="utf-8", errors="ignore")
        new_txt = txt
        for old, new in replacements:
            new_txt = new_txt.replace(old, new)
        if new_txt != txt:
            f.write_text(new_txt, encoding="utf-8")
            changed.append(str(f))
    except Exception as e:
        print(f"Error in {f}: {e}")

print(f"Updated {len(changed)} files:")
for fc in changed:
    print(f"  {fc}")
