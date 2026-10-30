"""Check plugins against PLUGIN_GUIDE.md (reads the code, never runs it). Exits with code 1 on problems (CI turns red).
Output is in English; set L2M_LANG=vi for Vietnamese.

    .venv\\Scripts\\python.exe tools\\check_plugins.py                  every plugin in plugins\\
    .venv\\Scripts\\python.exe tools\\check_plugins.py plugins\\<id>     one plugin folder
    .venv\\Scripts\\python.exe tools\\check_plugins.py plugin.zip        one zip file
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import i18n, plugins  # noqa: E402


def main(args: list[str]) -> int:
    i18n.set_lang(os.environ.get("L2M_LANG") or "en")
    try:
        return _check(args)
    finally:
        i18n.set_lang(None)


def _check(args: list[str]) -> int:
    if not args:
        results = plugins.discover(check_code=True)
        if not results:
            print("No plugins yet in", plugins.PLUGINS_DIR)
    else:
        results = []
        for arg in args:
            path = Path(arg)
            if path.suffix.lower() == ".zip":
                results.append(plugins.validate_zip(path.read_bytes()))
            elif path.is_dir():
                results.append(plugins.validate(path.resolve()))
            else:
                print(f"Folder / zip file not found: {arg}")
                return 1
    failed = 0
    for p in results:
        if p.ok:
            print(f"OK       {p.id} v{p.version} — {p.label}")
        else:
            failed += 1
            print(f"PROBLEM  {p.id} — {len(p.problems)} things to fix:")
            for problem in p.problems:
                print(f"         - {problem}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
