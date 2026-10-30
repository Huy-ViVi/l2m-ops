"""Split a chat AI's answer (format "FILE: plugins/<id>/…" + ``` blocks, see AI_PROMPT.md) into the folder plugins/<id>/,
then check it against PLUGIN_GUIDE.md. make-plugin.bat calls this with ai-answer.txt. Output is in English; set
L2M_LANG=vi for Vietnamese.

    .venv\\Scripts\\python.exe tools\\plugin_from_text.py ai-answer.txt
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import i18n, plugins  # noqa: E402


def main(path: str) -> int:
    i18n.set_lang(os.environ.get("L2M_LANG") or "en")
    try:
        return _make(path)
    finally:
        i18n.set_lang(None)


def _make(path: str) -> int:
    source = Path(path)
    if not source.is_file():
        print(f"File not found: {source}")
        return 1
    pid, files, problems = plugins.files_from_text(source.read_text(encoding="utf-8-sig", errors="replace"))
    for problem in problems:
        print(f"PROBLEM  {problem}")
    if not files:
        print("No plugin could be created — did you paste the AI's WHOLE answer?")
        return 1
    folder = plugins.PLUGINS_DIR / pid
    for rel, body in files.items():
        target = folder / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    print(f"Wrote {len(files)} files to {folder}:")
    for rel in sorted(files):
        print(f"         {rel}")
    p = plugins.validate(folder)
    if p.ok:
        print(f"\nOK       {p.id} v{p.version} — {p.label}. Double-click run.bat to try it: the plugin is in the left menu.")
        if problems:
            print("         Some files in the answer were skipped (PROBLEM lines above) — send those lines to your AI if needed.")
        return 0 if not problems else 1
    print(f"\n{len(p.problems)} things to fix — copy the lines below and send them back to your AI:")
    for problem in p.problems:
        print(f"         - {problem}")
    return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "ai-answer.txt"))
