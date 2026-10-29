"""Kiểm tra plugin theo PLUGIN_GUIDE.md (chỉ đọc code, không chạy). Có lỗi thì thoát mã 1 (GitHub Actions báo đỏ).

    .venv\\Scripts\\python.exe tools\\check_plugins.py                  mọi plugin trong plugins\\
    .venv\\Scripts\\python.exe tools\\check_plugins.py plugins\\<id>     một thư mục plugin
    .venv\\Scripts\\python.exe tools\\check_plugins.py plugin.zip        một file zip
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import plugins  # noqa: E402


def main(args: list[str]) -> int:
    if not args:
        results = plugins.discover(check_code=True)
        if not results:
            print("Chưa có plugin nào trong", plugins.PLUGINS_DIR)
    else:
        results = []
        for arg in args:
            path = Path(arg)
            if path.suffix.lower() == ".zip":
                results.append(plugins.validate_zip(path.read_bytes()))
            elif path.is_dir():
                results.append(plugins.validate(path.resolve()))
            else:
                print(f"Không thấy thư mục / file zip: {arg}")
                return 1
    failed = 0
    for p in results:
        if p.ok:
            print(f"OK    {p.id} v{p.version} — {p.label}")
        else:
            failed += 1
            print(f"LỖI   {p.id} — {len(p.problems)} điểm cần sửa:")
            for problem in p.problems:
                print(f"      - {problem}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
