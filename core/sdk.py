"""Bộ công cụ cho plugin — plugin chỉ dùng nền tảng qua mô-đun này:

    from core import sdk

    sdk.header(sdk.t("Theo dõi update nước ngoài"))
    sdk.save("updates", [{"id": "kr-2026-10-29", "region": "KR", "date": "2026-10-29", "title": "..."}])
    rows = sdk.load("updates", region="KR")

Tên và cách dùng các hàm ở đây được giữ ổn định: khi nền tảng đổi (vd dời sang server nội bộ), plugin không phải sửa.
Thêm hàm mới thì được; đổi / bỏ hàm cũ thì không. Hướng dẫn đầy đủ: PLUGIN_GUIDE.md.
"""
from __future__ import annotations

import ast
import contextlib
import contextvars
import functools
import json
import math
import re
import sys
from datetime import date, datetime
from typing import Any, Iterable

from . import config, i18n, store
from .master import short_key
from .plugins import PLUGINS_DIR, Plugin, read_manifest

VERSION = 1
COLLECTION_RE = re.compile(r"^[a-z][a-z0-9_]{0,40}$")
SECRET_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,40}$")
MAX_RECORD = 200 * 1024  # byte JSON mỗi bản ghi; file lớn đính kèm qua record(files=...)
RANK = {"viewer": 0, "member": 1, "admin": 2}
_current: contextvars.ContextVar[Plugin | None] = contextvars.ContextVar("l2m_plugin", default=None)


class SDKError(Exception):
    """Dùng sdk sai cách — thông báo nói rõ cần sửa gì."""


# ---------------------------------------------------------------------------
# Plugin đang chạy
# ---------------------------------------------------------------------------
def _bind(p: Plugin) -> contextvars.Token:
    """Nền tảng gọi trước khi chạy trang plugin (ui/plugin_host.py)."""
    return _current.set(p)


def _unbind(token: contextvars.Token) -> None:
    _current.reset(token)


@contextlib.contextmanager
def use(plugin_id: str):
    """Dùng sdk ngoài trang plugin (script, test):  with sdk.use("update_tracker"): sdk.save(...)"""
    folder = PLUGINS_DIR / plugin_id
    p = read_manifest(folder) if folder.is_dir() else Plugin(id=plugin_id, path=folder, name=plugin_id)
    token = _current.set(p)
    try:
        yield p
    finally:
        _current.reset(token)


def plugin() -> Plugin:
    """Thông tin plugin đang chạy (id, name, owners, version...)."""
    p = _current.get()
    if p is None:
        raise SDKError('core.sdk chỉ dùng được trong trang plugin, hoặc trong khối  with sdk.use("<id>"):')
    return p


def _in_streamlit() -> bool:
    if "streamlit" not in sys.modules:
        return False
    from streamlit.runtime.scriptrunner import get_script_run_ctx

    return get_script_run_ctx(suppress_warning=True) is not None


# ---------------------------------------------------------------------------
# Người dùng, quyền, game
# ---------------------------------------------------------------------------
def user() -> dict:
    """{'username', 'display_name', 'role'} của người đang dùng. role: admin / member / viewer (Chỉ xem)."""
    if _in_streamlit():
        from ui import auth

        u = auth.user() or {}
    else:
        u = {"username": "script", "display_name": "Script", "role": "member"}
    return {"username": u.get("username", ""), "display_name": u.get("display_name") or u.get("username", ""),
            "role": u.get("role", "viewer")}


def username() -> str:
    return user()["username"]


def can_edit() -> bool:
    """Được lưu / sửa / xoá dữ liệu (quyền Chỉ xem thì không). Kiểm tra trước khi hiện nút lưu."""
    return RANK.get(user()["role"], -1) >= RANK["member"]


def is_admin() -> bool:
    return user()["role"] == "admin"


def is_owner() -> bool:
    """Người đang dùng là người phụ trách plugin này (owners trong plugin.toml) hoặc admin."""
    return username() in plugin().owners or is_admin()


def game() -> dict:
    """Game đang chọn ở thanh bên: {'id': 'l2m', 'name': 'Lineage2M SEA', ...}."""
    if _in_streamlit():
        from ui import common

        return common.game()
    return config.game(config.load_settings())


def game_id() -> str:
    return game()["id"]


def now() -> datetime:
    """Giờ hiện tại theo giờ Việt Nam. Máy chủ website chạy giờ UTC — đừng dùng datetime.now()."""
    return config.now()


# ---------------------------------------------------------------------------
# Giao diện
# ---------------------------------------------------------------------------
def header(title: str, caption: str | None = None) -> None:
    """Tiêu đề trang (kèm game đang chọn, thông báo quyền Chỉ xem). Gọi ở đầu mỗi trang."""
    from ui import common

    common.page_header(title, caption)


def key(name: str) -> str:
    """Khoá widget / st.session_state có tiền tố plugin: st.text_input("Tên", key=sdk.key("ten"))."""
    return f"{plugin().id}_{name}"


def t(text: str, /, **kwargs) -> str:
    """Chữ hiển thị: viết tiếng Việt; bản tiếng Anh lấy từ locales.py của plugin (EN = {...}), không có thì giữ tiếng Việt."""
    lang = i18n.get_lang()
    if lang != i18n.DEFAULT:
        p = _current.get()
        own = _locales(p.id, lang) if p else {}
        text = own.get(text) or i18n.catalog(lang).get(text, text)
    return text.format(**kwargs) if kwargs else text


def _locales(plugin_id: str, lang: str) -> dict[str, str]:
    path = PLUGINS_DIR / plugin_id / "locales.py"
    return _read_locales(str(path), lang, path.stat().st_mtime) if path.is_file() else {}


@functools.lru_cache(maxsize=64)
def _read_locales(path: str, lang: str, _mtime: float) -> dict[str, str]:
    """Đọc EN = {...} trong locales.py mà không chạy file (dict phải viết thẳng)."""
    from pathlib import Path

    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(x, ast.Name) and x.id == lang.upper() for x in node.targets):
            try:
                value = ast.literal_eval(node.value)
            except ValueError:
                return {}
            return {str(k): str(v) for k, v in value.items()} if isinstance(value, dict) else {}
    return {}


# ---------------------------------------------------------------------------
# Dữ liệu của plugin (CSDL chung của team)
# ---------------------------------------------------------------------------
def _collection(name: str) -> str:
    if not isinstance(name, str) or not COLLECTION_RE.match(name):
        raise SDKError(f"Tên bộ sưu tập '{name}' không hợp lệ — chữ thường không dấu, số hoặc _, bắt đầu bằng chữ (vd 'updates')")
    return name


def _game(value: str | None) -> str:
    return game_id() if value is None else str(value)


def _json_value(o: Any):
    if hasattr(o, "item") and callable(o.item):  # số của numpy / pandas
        return o.item()
    if isinstance(o, datetime):
        return o.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(o, date):
        return o.isoformat()
    return str(o)


def product_key(value) -> str:
    """Chuẩn hoá Product Key như master: 'com.ncv.l2m.web.item 195' -> 'web.item195' (dùng khi tự ghép khoá bản ghi)."""
    return short_key(value)


def _clean(rec: dict) -> dict:
    """Bỏ trường bắt đầu bằng _ (sdk thêm khi đọc), chuẩn hoá mã chung: product_key như master, item_id là số."""
    out = {}
    for k, v in rec.items():
        if str(k).startswith("_"):
            continue
        out[str(k)] = None if isinstance(v, float) and math.isnan(v) else v
    if out.get("product_key"):
        out["product_key"] = short_key(out["product_key"])
    item = out.get("item_id")
    if isinstance(item, str) and item.strip().isdigit():
        out["item_id"] = int(item.strip())
    return out


def save(collection: str, records: dict | Iterable[dict], key: str = "id", game: str | None = None) -> int:
    """Thêm hoặc ghi đè bản ghi (cùng khoá = ghi đè, bản cũ vào lịch sử). Trả về số bản ghi thật sự thay đổi.
    key: tên trường làm khoá (mặc định 'id'). game: None = game đang chọn, '' = dùng chung mọi game."""
    p = plugin()
    _collection(collection)
    if not can_edit():
        raise SDKError("Tài khoản quyền Chỉ xem không lưu được — kiểm tra sdk.can_edit() trước khi hiện nút lưu")
    rows: dict[str, str] = {}
    for rec in [records] if isinstance(records, dict) else list(records):
        if not isinstance(rec, dict):
            raise SDKError("Mỗi bản ghi phải là dict")
        clean = _clean(rec)
        value = clean.get(key)
        if value is None or not str(value).strip():
            raise SDKError(f"Bản ghi thiếu khoá '{key}': {str(rec)[:120]}")
        data = json.dumps(clean, ensure_ascii=False, sort_keys=True, default=_json_value)
        if len(data.encode("utf-8")) > MAX_RECORD:
            raise SDKError(f"Bản ghi '{value}' quá lớn (> {MAX_RECORD // 1024} KB) — file lớn đính kèm qua sdk.record(files=...)")
        rows[str(value).strip()] = data
    return store.plugin_save(p.id, collection, _game(game), rows, username()) if rows else 0


def load(collection: str, game: str | None = None, **where) -> list[dict]:
    """Mọi bản ghi của một bộ sưu tập (mới sửa trước). Lọc bằng tham số: load("sales", market="TH").
    Mỗi bản ghi có thêm _key, _updated_by, _updated_at (sdk tự bỏ khi lưu lại)."""
    p = plugin()
    want = _clean(where)
    out = []
    for r in store.plugin_load(p.id, _collection(collection), _game(game)):
        rec = json.loads(r["data"])
        if all(rec.get(k) == v for k, v in want.items()):
            out.append({**rec, "_key": r["rkey"], "_updated_by": r["updated_by"], "_updated_at": r["updated_at"]})
    return out


def get(collection: str, key: str, game: str | None = None) -> dict | None:
    return next((r for r in load(collection, game) if r["_key"] == str(key)), None)


def delete(collection: str, keys: str | Iterable[str], game: str | None = None) -> int:
    """Xoá theo khoá (bản cũ vào lịch sử). Trả về số bản ghi đã xoá."""
    p = plugin()
    _collection(collection)
    if not can_edit():
        raise SDKError("Tài khoản quyền Chỉ xem không xoá được — kiểm tra sdk.can_edit() trước khi hiện nút xoá")
    keys = [keys] if isinstance(keys, str) else [str(k) for k in keys]
    return store.plugin_delete(p.id, collection, _game(game), keys, username()) if keys else 0


def history(collection: str, key: str, game: str | None = None, limit: int = 50) -> list[dict]:
    """Các bản cũ của một bản ghi, mới nhất trước: [{'action': 'update'|'delete', 'data': {...}, 'changed_by', 'changed_at'}].
    Khôi phục = sdk.save(collection, bản_cũ['data'])."""
    p = plugin()
    rows = store.plugin_history(p.id, _collection(collection), _game(game), str(key), limit)
    return [{"action": r["action"], "data": json.loads(r["data"] or "{}"), "changed_by": r["changed_by"],
             "changed_at": r["changed_at"]} for r in rows]


def collections(game: str | None = None) -> dict[str, int]:
    """Bộ sưu tập của plugin này -> số bản ghi."""
    p, g = plugin(), _game(game)
    return {r["collection"]: r["n"] for r in store.plugin_stats() if r["plugin"] == p.id and r["game"] == g}


# ---------------------------------------------------------------------------
# Lịch sử hoạt động của team
# ---------------------------------------------------------------------------
def record(title: str, summary: dict | None = None, files: dict[str, bytes] | None = None, status: str = "done") -> int:
    """Ghi một bản vào trang Lịch sử hoạt động (loại Plugin), kèm file kết quả nếu có. Trả về số bản ghi.
    summary: {'metrics': {'Số gói': 5}, 'tables': {'Tên bảng': [dict, ...]}} hiện đẹp ở trang Lịch sử."""
    p = plugin()
    if not can_edit():
        raise SDKError("Tài khoản quyền Chỉ xem không ghi lịch sử được")
    title = f"[{p.label}] {title}"
    summary = {"plugin": p.id, **(summary or {})}
    if _in_streamlit():
        from ui import common

        return common.record("plugin", title, summary, files, status=status)[0]
    return store.add_activity("plugin", title, summary, username(), files, status=status, source="script", game=game_id())


# ---------------------------------------------------------------------------
# Dữ liệu dùng chung của nền tảng (chỉ đọc), AI, bí mật
# ---------------------------------------------------------------------------
def master():
    """File master (All Product Information) hiện hành của game đang chọn, đã đọc sẵn — None nếu chưa có.
    .packages: Product Key -> gói (name, price_usd, purchase_limit, diamonds, items[name, quantity]);
    .webshop: giá theo thị trường; .display_name(product_key); .timeline. Không sửa được."""
    from ui import common

    file, _, _ = common.master_paths(game_id())
    return common.load_master_path(file) if file.exists() else None


def items(game: str | None = None) -> list[dict]:
    """Bảng Item ID dùng chung: [{'item_id', 'name', 'aliases', 'note'}]."""
    return [{"item_id": r["item_id"], "name": r["name"], "aliases": r["aliases"], "note": r.get("note", "")}
            for r in store.item_rows(_game(game))]


def ai():
    """AI theo cấu hình chung của team (trang Cài đặt): ai.text(...), ai.json(...). Chưa cấu hình thì báo lỗi trên trang và
    trả về None."""
    if not _in_streamlit():
        return None
    from ui import common

    return common.ai_client()


def secret(name: str) -> str:
    """Key / mật khẩu của plugin do admin cài vào secrets của website, tên PLUGIN_<ID>_<NAME>. Chưa cài -> ''."""
    if not isinstance(name, str) or not SECRET_RE.match(name):
        raise SDKError(f"Tên secret '{name}' không hợp lệ — CHỮ_IN_HOA, số hoặc _ (vd 'SHEET_KEY')")
    return config.env(f"PLUGIN_{plugin().id.upper()}_{name}", "")
