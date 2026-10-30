"""Plugin toolkit — plugins use the platform only through this module:

    from core import sdk

    sdk.header(sdk.t("Overseas updates"))
    sdk.save("updates", [{"id": "kr-2026-10-29", "region": "KR", "date": "2026-10-29", "title": "..."}])
    rows = sdk.load("updates", region="KR")

Function names and behaviour here stay stable: when the platform changes (e.g. moves to the internal server), plugins
need no changes. Adding functions is fine; renaming / removing them is not. Full rules: PLUGIN_GUIDE.md.
Docstrings are in English: they are copied as-is into AI_PROMPT.md for the team's AIs.
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
    """sdk used the wrong way — the message says what to fix."""


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
    """Use sdk outside a plugin page (scripts, tests):  with sdk.use("update_tracker"): sdk.save(...)"""
    folder = PLUGINS_DIR / plugin_id
    p = read_manifest(folder) if folder.is_dir() else Plugin(id=plugin_id, path=folder, name=plugin_id)
    token = _current.set(p)
    try:
        yield p
    finally:
        _current.reset(token)


def plugin() -> Plugin:
    """The running plugin's manifest info (id, name, owners, version...)."""
    p = _current.get()
    if p is None:
        raise SDKError('core.sdk only works inside a plugin page, or inside  with sdk.use("<id>"):')
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
    """{'username', 'display_name', 'role'} of the current user. role: admin / member / viewer (view only)."""
    if _in_streamlit():
        from ui import auth

        u = auth.user() or {}
    else:
        u = {"username": "script", "display_name": "Script", "role": "member"}
    return {"username": u.get("username", ""), "display_name": u.get("display_name") or u.get("username", ""),
            "role": u.get("role", "viewer")}


def username() -> str:
    """Website account of the current user."""
    return user()["username"]


def can_edit() -> bool:
    """Whether the user may save / edit / delete data (view-only users may not). Check before showing save buttons."""
    return RANK.get(user()["role"], -1) >= RANK["member"]


def is_admin() -> bool:
    """Whether the current user is a platform admin."""
    return user()["role"] == "admin"


def is_owner() -> bool:
    """Whether the current user is in charge of this plugin (owners in plugin.toml) or an admin."""
    return username() in plugin().owners or is_admin()


def game() -> dict:
    """The game selected in the sidebar: {'id': 'l2m', 'name': 'Lineage2M SEA', ...}."""
    if _in_streamlit():
        from ui import common

        return common.game()
    return config.game(config.load_settings())


def game_id() -> str:
    """Id of the selected game, e.g. 'l2m'."""
    return game()["id"]


def now() -> datetime:
    """Current time in Vietnam time. The website server runs on UTC — never use datetime.now()."""
    return config.now()


# ---------------------------------------------------------------------------
# Giao diện
# ---------------------------------------------------------------------------
def header(title: str, caption: str | None = None) -> None:
    """Page title (with the selected game and the view-only notice). Call at the top of every page."""
    from ui import common

    common.page_header(title, caption)


def key(name: str) -> str:
    """Widget / st.session_state key with the plugin prefix: st.text_input("Name", key=sdk.key("name"))."""
    return f"{plugin().id}_{name}"


def t(text: str, /, **kwargs) -> str:
    """Displayed text, in the user's chosen language (Tiếng Việt / English). Write the text in English or Vietnamese;
    the other language comes from the plugin's locales.py (VI = {...} / EN = {...}); without a translation the text is
    shown as written. Placeholders: sdk.t("Saved {n} rows", n=5)."""
    lang = i18n.get_lang()
    p = _current.get()
    own = _locales(p.id, lang) if p else {}
    if text in own:
        text = own[text]
    elif lang != i18n.DEFAULT:
        text = i18n.catalog(lang).get(text, text)
    return text.format(**kwargs) if kwargs else text


def _locales(plugin_id: str, lang: str) -> dict[str, str]:
    path = PLUGINS_DIR / plugin_id / "locales.py"
    return _read_locales(str(path), lang, path.stat().st_mtime) if path.is_file() else {}


@functools.lru_cache(maxsize=64)
def _read_locales(path: str, lang: str, _mtime: float) -> dict[str, str]:
    """Đọc VI = {...} / EN = {...} trong locales.py mà không chạy file (dict phải viết thẳng)."""
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
        raise SDKError(f"Invalid collection name '{name}' — lowercase ASCII letters, digits or _, starting with a letter "
                       "(e.g. 'updates')")
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
    """Normalise a Product Key the way the master does: 'com.ncv.l2m.web.item 195' -> 'web.item195' (use it when you
    build record keys yourself)."""
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
    """Add or overwrite records (same key = overwrite; the old version goes to history). Returns how many records
    actually changed. key: the field used as the record key (default 'id'). game: None = selected game,
    '' = shared by every game."""
    p = plugin()
    _collection(collection)
    if not can_edit():
        raise SDKError("View-only accounts cannot save — check sdk.can_edit() before showing a save button")
    rows: dict[str, str] = {}
    for rec in [records] if isinstance(records, dict) else list(records):
        if not isinstance(rec, dict):
            raise SDKError("Each record must be a dict")
        clean = _clean(rec)
        value = clean.get(key)
        if value is None or not str(value).strip():
            raise SDKError(f"Record without the key field '{key}': {str(rec)[:120]}")
        data = json.dumps(clean, ensure_ascii=False, sort_keys=True, default=_json_value)
        if len(data.encode("utf-8")) > MAX_RECORD:
            raise SDKError(f"Record '{value}' is too large (> {MAX_RECORD // 1024} KB) — attach large files with "
                           "sdk.record(files=...)")
        rows[str(value).strip()] = data
    return store.plugin_save(p.id, collection, _game(game), rows, username()) if rows else 0


def load(collection: str, game: str | None = None, **where) -> list[dict]:
    """Every record of a collection (most recently changed first). Filter with keyword arguments:
    load("sales", market="TH"). Each record also has _key, _updated_by, _updated_at (dropped automatically on save)."""
    p = plugin()
    want = _clean(where)
    out = []
    for r in store.plugin_load(p.id, _collection(collection), _game(game)):
        rec = json.loads(r["data"])
        if all(rec.get(k) == v for k, v in want.items()):
            out.append({**rec, "_key": r["rkey"], "_updated_by": r["updated_by"], "_updated_at": r["updated_at"]})
    return out


def get(collection: str, key: str, game: str | None = None) -> dict | None:
    """One record by key (None if missing)."""
    return next((r for r in load(collection, game) if r["_key"] == str(key)), None)


def delete(collection: str, keys: str | Iterable[str], game: str | None = None) -> int:
    """Delete by key (the old version goes to history). Returns how many records were deleted."""
    p = plugin()
    _collection(collection)
    if not can_edit():
        raise SDKError("View-only accounts cannot delete — check sdk.can_edit() before showing a delete button")
    keys = [keys] if isinstance(keys, str) else [str(k) for k in keys]
    return store.plugin_delete(p.id, collection, _game(game), keys, username()) if keys else 0


def history(collection: str, key: str, game: str | None = None, limit: int = 50) -> list[dict]:
    """Old versions of a record, newest first: [{'action': 'update'|'delete', 'data': {...}, 'changed_by', 'changed_at'}].
    Restore = sdk.save(collection, old['data'])."""
    p = plugin()
    rows = store.plugin_history(p.id, _collection(collection), _game(game), str(key), limit)
    return [{"action": r["action"], "data": json.loads(r["data"] or "{}"), "changed_by": r["changed_by"],
             "changed_at": r["changed_at"]} for r in rows]


def collections(game: str | None = None) -> dict[str, int]:
    """This plugin's collections -> record counts."""
    p, g = plugin(), _game(game)
    return {r["collection"]: r["n"] for r in store.plugin_stats() if r["plugin"] == p.id and r["game"] == g}


# ---------------------------------------------------------------------------
# Lịch sử hoạt động của team
# ---------------------------------------------------------------------------
def record(title: str, summary: dict | None = None, files: dict[str, bytes] | None = None, status: str = "done") -> int:
    """Log an entry in the team's Activity history (type Plugin), with result files if any. Returns the entry number.
    summary: {'metrics': {'Packages': 5}, 'tables': {'Table name': [dict, ...]}} is displayed nicely in the history page."""
    p = plugin()
    if not can_edit():
        raise SDKError("View-only accounts cannot write to the activity history")
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
    """The current master file (All Product Information) of the selected game, already parsed — None if none uploaded.
    .packages: Product Key -> package (name, price_usd, purchase_limit, diamonds, items[name, quantity]);
    .webshop: prices by market; .display_name(product_key); .timeline. Read-only."""
    from ui import common

    file, _, _ = common.master_paths(game_id())
    return common.load_master_path(file) if file.exists() else None


def items(game: str | None = None) -> list[dict]:
    """The team's shared Item ID table: [{'item_id', 'name', 'aliases', 'note'}]."""
    return [{"item_id": r["item_id"], "name": r["name"], "aliases": r["aliases"], "note": r.get("note", "")}
            for r in store.item_rows(_game(game))]


def ai():
    """AI using the team's shared configuration (Settings page): ai.text(system, prompt), ai.json(system, prompt, schema).
    If it is not configured, an error is shown on the page and None is returned."""
    if not _in_streamlit():
        return None
    from ui import common

    return common.ai_client()


def secret(name: str) -> str:
    """A plugin key / password installed by the admin in the website's secrets as PLUGIN_<ID>_<NAME>. Not installed -> ''."""
    if not isinstance(name, str) or not SECRET_RE.match(name):
        raise SDKError(f"Invalid secret name '{name}' — UPPERCASE letters, digits or _ (e.g. 'SHEET_KEY')")
    return config.env(f"PLUGIN_{plugin().id.upper()}_{name}", "")
