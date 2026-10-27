"""Đa ngôn ngữ giao diện (Tiếng Việt / English).

Chuỗi gốc tiếng Việt trong code chính là khoá: t("Đã lưu bản ghi #{aid}.", aid=5).
Bản dịch nằm trong core/locales/<mã>_*.py (mỗi file một dict EN, gộp lại khi tải).
Thiếu bản dịch -> hiện nguyên tiếng Việt, không lỗi.

Ngôn ngữ lấy theo phiên Streamlit đang chạy (st.session_state["lang"], ô chọn ở thanh bên), nên
nhiều người dùng các ngôn ngữ khác nhau cùng lúc không lẫn nhau. Ngoài Streamlit (tiến trình
automation, test) lấy từ biến môi trường L2M_LANG. Hàm st.cache_* trả về chuỗi đã dịch phải có
ngôn ngữ trong tham số, nếu không phiên này sẽ thấy chữ của phiên khác.
"""
from __future__ import annotations

import functools
import importlib
import os
import pkgutil
import sys
import threading

LANGS = {"vi": "Tiếng Việt", "en": "English"}
DEFAULT = "vi"
_local = threading.local()


def set_lang(code: str | None) -> None:
    """Ép ngôn ngữ cho luồng hiện tại (test, script). None -> bỏ ép."""
    _local.lang = code if code in LANGS else None


def _session_lang() -> str | None:
    if "streamlit" not in sys.modules:  # automation / test: không kéo streamlit vào
        return None
    from streamlit.runtime.scriptrunner import get_script_run_ctx

    ctx = get_script_run_ctx(suppress_warning=True)
    if ctx is None:
        return None
    try:
        return ctx.session_state["lang"]
    except KeyError:
        return None


def get_lang() -> str:
    code = getattr(_local, "lang", None) or _session_lang() or os.environ.get("L2M_LANG")
    return code if code in LANGS else DEFAULT


@functools.cache
def catalog(code: str) -> dict[str, str]:
    """Gộp mọi core/locales/<code>_*.py."""
    from . import locales

    merged: dict[str, str] = {}
    for mod in sorted(m.name for m in pkgutil.iter_modules(locales.__path__) if m.name.startswith(f"{code}_")):
        merged.update(getattr(importlib.import_module(f"{locales.__name__}.{mod}"), code.upper(), {}))
    return merged


def t(text: str, /, **kwargs) -> str:
    """Dịch theo ngôn ngữ hiện tại; kwargs điền vào các chỗ {tên} như str.format."""
    lang = get_lang()
    if lang != DEFAULT and isinstance(text, str):
        text = catalog(lang).get(text, text)
    return text.format(**kwargs) if kwargs else text


def tr_value(value):
    """Dịch một giá trị hiển thị nếu nó đúng bằng một chuỗi gốc có bản dịch (tiêu đề cột, nhãn trạng thái...)."""
    lang = get_lang()
    if lang == DEFAULT or not isinstance(value, str):
        return value
    return catalog(lang).get(value, value)


def ai_language() -> str:
    """Ngôn ngữ AI nên dùng khi viết phần giải thích / tóm tắt cho người đọc."""
    return "English" if get_lang() == "en" else "tiếng Việt"
