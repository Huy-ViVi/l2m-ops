"""Kiểm tra bản dịch giao diện.   python tests/test_i18n.py   (hoặc pytest)

Công cụ khi dịch:
  python tests/test_i18n.py --missing [file ...]    chuỗi còn thiếu bản dịch (theo file)
  python tests/test_i18n.py --unwrapped [file ...]  chuỗi tiếng Việt ở views/ui chưa bọc t() (để rà: hiển thị mà chưa bọc = vẫn hiện tiếng Việt)
"""
from __future__ import annotations

import ast
import os
import re
import string
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("L2M_DATA_DIR", tempfile.mkdtemp(prefix="l2m-test-"))

from core import i18n  # noqa: E402

VI = re.compile(r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]", re.I)
UI_DIRS = ("views", "ui")  # mọi chuỗi tiếng Việt ở đây là chữ hiển thị -> phải có bản dịch
ALL_DIRS = ("views", "ui", "core", "automation")
EN_OK = {"Tiếng Việt"}  # bản dịch được phép giữ dấu (tên ngôn ngữ)


def _files(dirs=ALL_DIRS) -> list[Path]:
    out = [p for d in dirs for p in sorted((ROOT / d).glob("*.py"))]
    if "views" in dirs:
        out.append(ROOT / "app.py")
    return [p for p in out if "locales" not in p.parts]


def _is_t(node: ast.Call) -> bool:
    f = node.func
    return (isinstance(f, ast.Name) and f.id == "t") or (isinstance(f, ast.Attribute) and f.attr == "t")


def _scan(path: Path) -> tuple[list[tuple[int, str]], list[tuple[int, str]], list[tuple[int, str]]]:
    """-> (khoá trong t(), lỗi dùng t() sai, chuỗi tiếng Việt chưa bọc t()) của một file. Bỏ docstring."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    skip, keys, bad = set(), [], []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                skip.add(id(first.value))
        if isinstance(node, ast.Call) and _is_t(node) and node.args:
            arg = node.args[0]
            for sub in ast.walk(arg):
                skip.add(id(sub))
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                keys.append((node.lineno, arg.value))
                names = {f for _, f, _, _ in string.Formatter().parse(arg.value) if f}
                given = {k.arg for k in node.keywords}
                if None not in given and names - given:
                    bad.append((node.lineno, f"thiếu tham số {sorted(names - given)} cho: {arg.value[:60]}"))
            elif isinstance(arg, ast.JoinedStr):
                bad.append((node.lineno, "t() nhận f-string — dùng t('... {ten} ...', ten=...)"))
    plain = sorted({(n.lineno, n.value) for n in ast.walk(tree)
                    if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in skip and VI.search(n.value)})
    return keys, bad, plain


def _placeholders(s: str) -> set[str]:
    try:
        return {f.split(".")[0].split("[")[0] for _, f, _, _ in string.Formatter().parse(s) if f}
    except ValueError:
        return {"<lỗi định dạng>"}


def missing(files: list[Path] | None = None) -> dict[str, list[tuple[int, str]]]:
    en = i18n.catalog("en")
    ui = {ROOT / d for d in UI_DIRS}
    out = {}
    for p in files or _files():
        keys, _, plain = _scan(p)
        need = keys + (plain if p.parent in ui or p.name == "app.py" else [])
        gaps = sorted({(ln, s) for ln, s in need if s not in en})
        if gaps:
            out[str(p.relative_to(ROOT))] = gaps
    return out


# ---------------------------------------------------------------------------
def test_t_basics():
    i18n.set_lang("en")
    try:
        assert i18n.t("Chuỗi chưa có bản dịch {x}", x=1) == "Chuỗi chưa có bản dịch 1"  # thiếu -> giữ nguyên
        assert i18n.t("Lịch sử hoạt động") == "Activity history"
        assert i18n.tr_value("Lịch sử hoạt động") == "Activity history" and i18n.tr_value(5) == 5
        assert i18n.ai_language() == "English"
    finally:
        i18n.set_lang(None)
    assert i18n.get_lang() == "vi" and i18n.t("Lịch sử hoạt động") == "Lịch sử hoạt động"
    assert i18n.t("{n} gói", n=3) == "3 gói"


def test_t_calls_well_formed():
    problems = [f"{p.relative_to(ROOT)}:{ln} {msg}" for p in _files() for ln, msg in _scan(p)[1]]
    assert not problems, "\n".join(problems)


def test_everything_translated():
    gaps = missing()
    lines = [f"{f}:{ln} {s[:80]!r}" for f, items in gaps.items() for ln, s in items]
    assert not lines, f"{len(lines)} chuỗi thiếu bản dịch tiếng Anh:\n" + "\n".join(lines[:80])


def test_translations_consistent():
    from core import locales
    import importlib
    import pkgutil

    seen, problems = {}, []
    for m in pkgutil.iter_modules(locales.__path__):
        if not m.name.startswith("en_"):
            continue
        for vi, en in importlib.import_module(f"core.locales.{m.name}").EN.items():
            if not en.strip():
                problems.append(f"{m.name}: bản dịch rỗng cho {vi!r}")
            if VI.search(en) and not any(ok in en for ok in EN_OK):
                problems.append(f"{m.name}: bản dịch còn tiếng Việt: {en!r}")
            if _placeholders(vi) != _placeholders(en):
                problems.append(f"{m.name}: chỗ {{}} không khớp: {vi!r} -> {en!r}")
            if vi in seen and seen[vi][1] != en:
                problems.append(f"{m.name}: {vi!r} dịch khác {seen[vi][0]} ({seen[vi][1]!r} vs {en!r})")
            seen.setdefault(vi, (m.name, en))
    assert not problems, "\n".join(problems[:80])


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    picked = [(ROOT / a).resolve() for a in args] or None
    if "--missing" in sys.argv:
        gaps = missing(picked)
        for f, items in gaps.items():
            print(f"{f}: {len(items)}")
            for ln, s in items:
                print(f"  {ln}: {s!r}")
        print("TOTAL", sum(len(v) for v in gaps.values()))
        sys.exit(0)
    if "--unwrapped" in sys.argv:
        for p in picked or _files(UI_DIRS):
            plain = _scan(p)[2]
            if plain:
                print(f"{p.relative_to(ROOT)}: {len(plain)}")
                for ln, s in plain:
                    print(f"  {ln}: {s[:100]!r}")
        sys.exit(0)
    failed = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception as e:  # noqa: BLE001
                failed += 1
                print(f"FAIL {name}: {type(e).__name__}: {e}")
    sys.exit(1 if failed else 0)
