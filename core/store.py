"""Cơ sở dữ liệu dùng chung: thành viên, lịch sử hoạt động + file kết quả, bảng Item ID, nhật ký thay đổi,
và (khi dùng CSDL chung) cài đặt chung + các phiên bản master.

SQLite (data/app.db) hoặc Postgres qua DATABASE_URL — xem core/db.py. Với Postgres ở xa, các hàm đọc được
cache ngắn trong tiến trình (mỗi lần ghi xoá cache) để trang không phải chờ CSDL ở mỗi lượt chạy.
"""
from __future__ import annotations

import functools
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from contextlib import contextmanager
from copy import deepcopy
from datetime import timedelta

from . import config, db
from .i18n import t

ROLES = {"admin": "Admin", "member": "Thành viên", "viewer": "Chỉ xem"}
KINDS = {
    "payment_errors": "Case nạp lỗi",
    "nc_setup": "Tạo gói NC",
    "webshop_audit": "Kiểm tra webshop",
    "master": "Cập nhật master",
}
STATUSES = {"draft": "Nháp", "done": "Hoàn thành", "need_check": "Cần kiểm tra", "cancelled": "Huỷ"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, display_name TEXT, password_hash TEXT NOT NULL,
    role TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, token_hash TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY, kind TEXT NOT NULL, title TEXT, status TEXT, summary TEXT, note TEXT,
    source TEXT, sync_status TEXT, created_by TEXT, created_at TEXT, updated_by TEXT, updated_at TEXT,
    deleted INTEGER NOT NULL DEFAULT 0, game TEXT NOT NULL DEFAULT 'l2m'
);
CREATE TABLE IF NOT EXISTS activity_files (
    id INTEGER PRIMARY KEY, activity_id INTEGER NOT NULL, name TEXT NOT NULL, content BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS item_ids (
    game TEXT NOT NULL DEFAULT 'l2m', item_id INTEGER NOT NULL, name TEXT NOT NULL, aliases TEXT NOT NULL DEFAULT '[]',
    updated_by TEXT, updated_at TEXT, PRIMARY KEY (game, item_id)
);
CREATE TABLE IF NOT EXISTS changelog (
    id INTEGER PRIMARY KEY, at TEXT, username TEXT, action TEXT, target TEXT, detail TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY, username TEXT NOT NULL, created_at TEXT, expires_at TEXT
);
CREATE TABLE IF NOT EXISTS tool_items (
    game TEXT NOT NULL, item_id INTEGER NOT NULL, name TEXT NOT NULL, updated_at TEXT, PRIMARY KEY (game, item_id)
);
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_by TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS master_files (
    id INTEGER PRIMARY KEY, game TEXT NOT NULL, name TEXT NOT NULL, uploaded_by TEXT, uploaded_at TEXT,
    is_current INTEGER NOT NULL DEFAULT 0, content BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY, job TEXT NOT NULL, payload TEXT NOT NULL, requested_by TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued', agent TEXT, log TEXT NOT NULL DEFAULT '', result TEXT,
    created_at TEXT, started_at TEXT, finished_at TEXT
);
CREATE TABLE IF NOT EXISTS job_files (
    id INTEGER PRIMARY KEY, job_id INTEGER NOT NULL, name TEXT NOT NULL, content BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS agents (
    username TEXT PRIMARY KEY, host TEXT, seen_at TEXT, version TEXT
);
"""
SESSION_DAYS = 14


def now() -> str:
    return config.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# Cache đọc (chỉ khi CSDL ở xa): giữ CACHE_TTL giây, xoá ngay khi tiến trình này ghi gì vào CSDL.
# Thay đổi từ máy khác hiện ra sau tối đa CACHE_TTL giây.
# ---------------------------------------------------------------------------
CACHE_TTL = 15
_cache: dict = {}
_cache_lock = threading.Lock()


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


def _cached(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if not db.is_remote():
            return fn(*args, **kwargs)
        key = (fn.__name__, repr(args), repr(sorted(kwargs.items())))
        hit = _cache.get(key)
        if hit and time.monotonic() - hit[0] < CACHE_TTL:
            return deepcopy(hit[1])
        value = fn(*args, **kwargs)
        with _cache_lock:
            _cache[key] = (time.monotonic(), value)
        return deepcopy(value)
    return wrapper


@contextmanager
def connect():
    with db.connect() as c:
        yield c
    if getattr(c, "dirty", False):
        clear_cache()


_ready: set[str] = set()


def _columns(c, table: str) -> set[str]:
    return db.columns(c, table)


def _migrate(c) -> None:
    """Nâng CSDL bản cũ (chỉ có Lineage2M) lên bản nhiều game: dữ liệu cũ gán game 'l2m'."""
    if "game" not in _columns(c, "activities"):
        c.execute("ALTER TABLE activities ADD COLUMN game TEXT NOT NULL DEFAULT 'l2m'")
    if "game" not in _columns(c, "item_ids"):
        c.execute("ALTER TABLE item_ids RENAME TO item_ids_old")
        c.execute("""CREATE TABLE item_ids (
            game TEXT NOT NULL DEFAULT 'l2m', item_id INTEGER NOT NULL, name TEXT NOT NULL, aliases TEXT NOT NULL DEFAULT '[]',
            updated_by TEXT, updated_at TEXT, PRIMARY KEY (game, item_id))""")
        c.execute("INSERT INTO item_ids(game, item_id, name, aliases, updated_by, updated_at) "
                  "SELECT 'l2m', item_id, name, aliases, updated_by, updated_at FROM item_ids_old")
        c.execute("DROP TABLE item_ids_old")
    cols = _columns(c, "item_ids")
    for col in ("game_item_key", "note"):
        if col not in cols:
            c.execute(f"ALTER TABLE item_ids ADD COLUMN {col} TEXT NOT NULL DEFAULT ''")


SEED_FILES = {"l2m": ("item_ids.json",)}  # Item ID có sẵn theo game (resources/)


def _seed_entries(gid: str) -> list[dict]:
    entries = []
    for f in SEED_FILES.get(gid, ()):
        path = config.RESOURCES_DIR / f
        if path.exists():
            entries += json.loads(path.read_text(encoding="utf-8-sig")).get("items", [])
    return entries


def blocked_items(gid: str) -> dict[int, str]:
    """Item ID không được dùng (vd 83 — bản trùng tên, key sai) -> lý do."""
    out = {}
    for f in SEED_FILES.get(gid, ()):
        path = config.RESOURCES_DIR / f
        if path.exists():
            out.update({int(b["id"]): b["reason"] for b in json.loads(path.read_text(encoding="utf-8-sig")).get("blocked", [])})
    return out


def _sync_seed(c, gid: str) -> None:
    """Bổ sung/cập nhật Item ID có sẵn từ resources/. Dòng người dùng đã sửa (updated_by khác 'seed') được giữ nguyên."""
    rows = {r["item_id"]: r for r in c.execute("SELECT item_id, updated_by FROM item_ids WHERE game = ?", (gid,))}
    learned = config.DATA_DIR / "item_ids.json"  # item học được ở bản đầu tiên của app
    extra = json.loads(learned.read_text(encoding="utf-8-sig")).get("items", []) if gid == "l2m" and learned.exists() else []
    batch = []
    for e in _seed_entries(gid) + extra:
        iid = int(e["id"])
        if iid in rows and rows[iid]["updated_by"] != "seed":
            continue
        aliases = list(dict.fromkeys(e.get("aliases", []) + ([e["tool_name"]] if e.get("tool_name") else [])))
        batch.append((gid, iid, e["name"], json.dumps(aliases, ensure_ascii=False), "seed", now(), e.get("key", ""), e.get("note", "")))
    c.executemany(ITEM_UPSERT, batch)


# Thêm hoặc ghi đè một Item ID (cú pháp chạy được trên cả SQLite lẫn Postgres)
ITEM_UPSERT = (
    "INSERT INTO item_ids(game, item_id, name, aliases, updated_by, updated_at, game_item_key, note) VALUES (?,?,?,?,?,?,?,?) "
    "ON CONFLICT(game, item_id) DO UPDATE SET name = excluded.name, aliases = excluded.aliases, updated_by = excluded.updated_by, "
    "updated_at = excluded.updated_at, game_item_key = excluded.game_item_key, note = excluded.note")


def init() -> None:
    """Tạo bảng nếu chưa có, nâng cấp CSDL cũ và đồng bộ bảng Item ID có sẵn."""
    key = db.describe() + "|" + os.environ.get("L2M_DB_SCHEMA", "")
    if key in _ready:
        return
    with connect() as c:
        c.executescript(db.schema(SCHEMA))
        _migrate(c)
        for gid in SEED_FILES:
            _sync_seed(c, gid)
    _ready.add(key)


def log(username: str, action: str, target: str, detail: str = "") -> None:
    init()
    with connect() as c:
        c.execute("INSERT INTO changelog(at, username, action, target, detail) VALUES (?,?,?,?,?)",
                  (now(), username, action, target, detail[:2000]))


@_cached
def changelog(limit: int = 300) -> list[dict]:
    init()
    with connect() as c:
        return [dict(r) for r in c.execute("SELECT at, username, action, target, detail FROM changelog ORDER BY id DESC LIMIT ?", (limit,))]


# ---------------------------------------------------------------------------
# Thành viên
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, digest = stored.split("$")
        dk = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt), n=2**14, r=8, p=1)
        return hmac.compare_digest(dk.hex(), digest)
    except (ValueError, TypeError):
        return False


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _public(row) -> dict:
    d = dict(row)
    d.pop("password_hash", None)
    d["has_token"] = bool(d.pop("token_hash", None))
    return d


@_cached
def user_count() -> int:
    init()
    with connect() as c:
        return c.execute("SELECT COUNT(*) FROM users").fetchone()[0]


def create_user(username: str, display_name: str, password: str, role: str, by: str) -> None:
    username = username.strip().lower()
    if not username or not password:
        raise ValueError(t("Cần username và mật khẩu"))
    if len(password) < 8:
        raise ValueError(t("Mật khẩu tối thiểu 8 ký tự"))
    if role not in ROLES:
        raise ValueError(t("Vai trò không hợp lệ"))
    init()
    with connect() as c:
        try:
            c.execute("INSERT INTO users(username, display_name, password_hash, role, created_at) VALUES (?,?,?,?,?)",
                      (username, display_name.strip() or username, hash_password(password), role, now()))
        except db.IntegrityError as e:
            raise ValueError(t("Username '{username}' đã tồn tại", username=username)) from e
    log(by, "tạo thành viên", username, f"vai trò {ROLES[role]}")


def authenticate(username: str, password: str) -> dict | None:
    init()
    with connect() as c:
        row = c.execute("SELECT * FROM users WHERE username = ?", (username.strip().lower(),)).fetchone()
    if row and row["active"] and verify_password(password, row["password_hash"]):
        return _public(row)
    return None


@_cached
def get_user(username: str) -> dict | None:
    init()
    with connect() as c:
        row = c.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    return _public(row) if row else None


@_cached
def list_users() -> list[dict]:
    init()
    with connect() as c:
        return [_public(r) for r in c.execute("SELECT * FROM users ORDER BY username")]


def update_user(username: str, by: str, role: str | None = None, active: bool | None = None,
                display_name: str | None = None) -> None:
    changes = []
    with connect() as c:
        if role is not None:
            if role not in ROLES:
                raise ValueError(t("Vai trò không hợp lệ"))
            c.execute("UPDATE users SET role = ? WHERE username = ?", (role, username))
            changes.append(f"vai trò → {ROLES[role]}")
        if active is not None:
            c.execute("UPDATE users SET active = ? WHERE username = ?", (1 if active else 0, username))
            if not active:
                c.execute("DELETE FROM sessions WHERE username = ?", (username,))
            changes.append("kích hoạt" if active else "khoá tài khoản")
        if display_name is not None:
            c.execute("UPDATE users SET display_name = ? WHERE username = ?", (display_name, username))
            changes.append(f"tên hiển thị → {display_name}")
    if changes:
        log(by, "sửa thành viên", username, "; ".join(changes))


def set_password(username: str, password: str, by: str) -> None:
    if len(password) < 8:
        raise ValueError(t("Mật khẩu tối thiểu 8 ký tự"))
    with connect() as c:
        c.execute("UPDATE users SET password_hash = ? WHERE username = ?", (hash_password(password), username))
        c.execute("DELETE FROM sessions WHERE username = ?", (username,))  # đăng xuất mọi thiết bị
    log(by, "đặt lại mật khẩu", username)


def issue_token(username: str, by: str) -> str:
    """Token để bản local của thành viên đẩy kết quả lên server. Chỉ hiện một lần."""
    token = "l2m_" + secrets.token_urlsafe(24)
    with connect() as c:
        c.execute("UPDATE users SET token_hash = ? WHERE username = ?", (_hash_token(token), username))
    log(by, "cấp token đồng bộ", username)
    return token


def create_session(username: str) -> str:
    """Phiên đăng nhập ghi nhớ qua cookie (để F5 không bị đăng xuất). Lưu dạng băm."""
    token = secrets.token_urlsafe(32)
    expires = config.now() + timedelta(days=SESSION_DAYS)
    with connect() as c:
        c.execute("DELETE FROM sessions WHERE expires_at < ?", (now(),))
        c.execute("INSERT INTO sessions(token_hash, username, created_at, expires_at) VALUES (?,?,?,?)",
                  (_hash_token(token), username, now(), expires.strftime("%Y-%m-%d %H:%M:%S")))
    return token


@_cached
def session_user(token: str | None) -> dict | None:
    if not isinstance(token, str) or not token:
        return None
    init()
    with connect() as c:
        row = c.execute("SELECT username FROM sessions WHERE token_hash = ? AND expires_at > ?",
                        (_hash_token(token), now())).fetchone()
    if not row:
        return None
    user = get_user(row["username"])
    return user if user and user["active"] else None


def delete_session(token: str | None) -> None:
    if token:
        with connect() as c:
            c.execute("DELETE FROM sessions WHERE token_hash = ?", (_hash_token(token),))


def user_by_token(token: str) -> dict | None:
    if not token:
        return None
    init()
    with connect() as c:
        row = c.execute("SELECT * FROM users WHERE token_hash = ? AND active = 1", (_hash_token(token),)).fetchone()
    return _public(row) if row else None


# ---------------------------------------------------------------------------
# Lịch sử hoạt động
# ---------------------------------------------------------------------------
def add_activity(kind: str, title: str, summary: dict, by: str, files: dict[str, bytes] | None = None,
                 note: str = "", status: str = "done", source: str = "web", game: str = "l2m",
                 created_at: str | None = None) -> int:
    init()
    ts = created_at or now()
    with connect() as c:
        aid = c.execute(
            "INSERT INTO activities(kind, title, status, summary, note, source, created_by, created_at, updated_by, updated_at, game) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?) RETURNING id",
            (kind, title, status, json.dumps(summary, ensure_ascii=False, default=str), note, source, by, ts, by, ts, game),
        ).fetchone()[0]
        c.executemany("INSERT INTO activity_files(activity_id, name, content) VALUES (?,?,?)",
                      [(aid, name, content) for name, content in (files or {}).items()])
    log(by, "tạo", f"#{aid} {KINDS.get(kind, kind)} [{game}]", title)
    return aid


@_cached
def list_activities(kinds: list[str] | None = None, search: str = "", include_deleted: bool = False,
                    limit: int = 500, game: str | None = None) -> list[dict]:
    init()
    sql = ("SELECT id, kind, title, status, source, sync_status, created_by, created_at, updated_by, updated_at, deleted, game "
           "FROM activities WHERE 1=1")
    args: list = []
    if game:
        sql += " AND game = ?"
        args.append(game)
    if not include_deleted:
        sql += " AND deleted = 0"
    if kinds:
        sql += f" AND kind IN ({','.join('?' * len(kinds))})"
        args += kinds
    if search:
        sql += " AND (title LIKE ? OR note LIKE ? OR summary LIKE ? OR created_by LIKE ?)"
        args += [f"%{search}%"] * 4
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    with connect() as c:
        return [dict(r) for r in c.execute(sql, args)]


@_cached
def get_activity(aid: int) -> dict | None:
    init()
    with connect() as c:
        row = c.execute("SELECT * FROM activities WHERE id = ?", (aid,)).fetchone()
        if not row:
            return None
        files = [dict(r) for r in c.execute(
            "SELECT id, name, length(content) AS size FROM activity_files WHERE activity_id = ? ORDER BY id", (aid,))]
    d = dict(row)
    d["summary"] = json.loads(d["summary"] or "{}")
    d["files"] = files
    return d


def get_file(file_id: int) -> tuple[str, bytes] | None:
    return _get_file_remote(db.describe(), file_id) if db.is_remote() else _read_file(file_id)


def _read_file(file_id: int) -> tuple[str, bytes] | None:
    with connect() as c:
        row = c.execute("SELECT name, content FROM activity_files WHERE id = ?", (file_id,)).fetchone()
    return (row["name"], bytes(row["content"])) if row else None


@functools.lru_cache(maxsize=32)  # file đính kèm không bao giờ sửa -> tải từ CSDL ở xa một lần
def _get_file_remote(_where: str, file_id: int) -> tuple[str, bytes] | None:
    return _read_file(file_id)


def update_activity(aid: int, by: str, title: str | None = None, note: str | None = None, status: str | None = None,
                    summary: dict | None = None, sync_status: str | None = None) -> None:
    fields, args, changes = [], [], []
    for col, value, label in (("title", title, "tiêu đề"), ("note", note, "ghi chú"), ("status", status, "trạng thái")):
        if value is not None:
            fields.append(f"{col} = ?")
            args.append(value)
            changes.append(f"{label}: {STATUSES.get(value, value) if col == 'status' else value}"[:200])
    if summary is not None:
        fields.append("summary = ?")
        args.append(json.dumps(summary, ensure_ascii=False, default=str))
        changes.append("cập nhật kết quả")
    if sync_status is not None:
        fields.append("sync_status = ?")
        args.append(sync_status)
    if not fields:
        return
    fields += ["updated_by = ?", "updated_at = ?"]
    args += [by, now(), aid]
    with connect() as c:
        c.execute(f"UPDATE activities SET {', '.join(fields)} WHERE id = ?", args)
    if changes:
        log(by, "sửa", f"#{aid}", "; ".join(changes))


def add_files(aid: int, files: dict[str, bytes], by: str) -> None:
    with connect() as c:
        c.executemany("INSERT INTO activity_files(activity_id, name, content) VALUES (?,?,?)",
                      [(aid, name, content) for name, content in files.items()])
    log(by, "thêm file", f"#{aid}", ", ".join(files))


def delete_activity(aid: int, by: str, restore: bool = False) -> None:
    with connect() as c:
        c.execute("UPDATE activities SET deleted = ?, updated_by = ?, updated_at = ? WHERE id = ?",
                  (0 if restore else 1, by, now(), aid))
    log(by, "khôi phục" if restore else "xoá", f"#{aid}")


# ---------------------------------------------------------------------------
# Bảng Item ID dùng chung
# ---------------------------------------------------------------------------
@_cached
def item_rows(game: str = "l2m") -> list[dict]:
    """Item ID theo game — mỗi game (app group trên NC tool) có bộ Item ID riêng."""
    init()
    with connect() as c:
        rows = [dict(r) for r in c.execute("SELECT * FROM item_ids WHERE game = ? ORDER BY item_id", (game,))]
    for r in rows:
        r["aliases"] = json.loads(r["aliases"] or "[]")
    return rows


def upsert_item(item_id: int, name: str, aliases: list[str], by: str, game: str = "l2m",
                game_item_key: str | None = None, note: str | None = None) -> None:
    """Thêm/sửa Item ID. game_item_key / note = None -> giữ giá trị đang có."""
    init()
    aliases = [a.strip() for a in aliases if a and a.strip() and a.strip() != name]
    with connect() as c:
        old = c.execute("SELECT name, aliases, game_item_key, note FROM item_ids WHERE game = ? AND item_id = ?",
                        (game, item_id)).fetchone()
        key = game_item_key if game_item_key is not None else (old["game_item_key"] if old else "")
        nt = note if note is not None else (old["note"] if old else "")
        c.execute(ITEM_UPSERT,
                  (game, int(item_id), name.strip(), json.dumps(aliases, ensure_ascii=False), by, now(), (key or "").strip(), nt or ""))
    if old is None:
        log(by, "thêm Item ID", f"[{game}] {item_id}", name)
    elif old["name"] != name.strip() or json.loads(old["aliases"]) != aliases:
        log(by, "sửa Item ID", f"[{game}] {item_id}", f"{old['name']} → {name}; alias: {', '.join(aliases)}")


def add_alias(item_id: int, alias: str, by: str, game: str = "l2m") -> None:
    for r in item_rows(game):
        if r["item_id"] == int(item_id):
            if alias != r["name"] and alias not in r["aliases"]:
                upsert_item(r["item_id"], r["name"], r["aliases"] + [alias], by, game)
            return
    upsert_item(int(item_id), alias, [], by, game)


# ---------------------------------------------------------------------------
# Danh sách item tải từ NC tool (Item lookup) — nguồn để so khớp tên khi tên Excel khác tên trên tool
# ---------------------------------------------------------------------------
def save_tool_items(game: str, items: list[dict]) -> int:
    init()
    ts = now()
    rows = {int(it["item_id"]): str(it["name"]).strip() for it in items if it.get("item_id") is not None and it.get("name")}
    with connect() as c:
        c.executemany("INSERT INTO tool_items(game, item_id, name, updated_at) VALUES (?,?,?,?) "
                      "ON CONFLICT(game, item_id) DO UPDATE SET name = excluded.name, updated_at = excluded.updated_at",
                      [(game, iid, name, ts) for iid, name in rows.items()])
    return len(items)


@_cached
def tool_items(game: str) -> list[dict]:
    init()
    with connect() as c:
        return [dict(r) for r in c.execute("SELECT item_id, name, updated_at FROM tool_items WHERE game = ? ORDER BY item_id", (game,))]


@_cached
def tool_items_info(game: str) -> tuple[int, str | None]:
    init()
    with connect() as c:
        row = c.execute("SELECT COUNT(*), MAX(updated_at) FROM tool_items WHERE game = ?", (game,)).fetchone()
    return row[0], row[1]


def delete_item(item_id: int, by: str, game: str = "l2m") -> None:
    with connect() as c:
        c.execute("DELETE FROM item_ids WHERE game = ? AND item_id = ?", (game, int(item_id)))
    log(by, "xoá Item ID", f"[{game}] {item_id}")

# ---------------------------------------------------------------------------
# Cài đặt chung (khi dùng CSDL chung): thông số game, AI... để website và bản local cùng một cấu hình
# ---------------------------------------------------------------------------
@_cached
def get_app_setting(key: str):
    init()
    with connect() as c:
        row = c.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return json.loads(row["value"]) if row else None


def set_app_setting(key: str, value, by: str) -> None:
    init()
    with connect() as c:
        c.execute("INSERT INTO app_settings(key, value, updated_by, updated_at) VALUES (?,?,?,?) "
                  "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_by = excluded.updated_by, updated_at = excluded.updated_at",
                  (key, json.dumps(value, ensure_ascii=False), by, now()))


# ---------------------------------------------------------------------------
# File master trong CSDL (khi dùng CSDL chung — ổ đĩa của website trên cloud bị xoá mỗi lần khởi động lại)
# ---------------------------------------------------------------------------
def add_master(game: str, name: str, content: bytes, by: str, uploaded_at: str | None = None, current: bool = True) -> int:
    init()
    with connect() as c:
        if current:
            c.execute("UPDATE master_files SET is_current = 0 WHERE game = ?", (game,))
        return c.execute("INSERT INTO master_files(game, name, uploaded_by, uploaded_at, is_current, content) "
                         "VALUES (?,?,?,?,?,?) RETURNING id",
                         (game, name, by, uploaded_at or now(), 1 if current else 0, content)).fetchone()[0]


@_cached
def master_versions(game: str, limit: int = 30) -> list[dict]:
    """Các phiên bản master của một game, mới nhất trước (không kèm nội dung)."""
    init()
    with connect() as c:
        return [dict(r) for r in c.execute(
            "SELECT id, name, uploaded_by, uploaded_at, is_current, length(content) AS size FROM master_files "
            "WHERE game = ? ORDER BY id DESC LIMIT ?", (game, limit))]


def current_master(game: str) -> dict | None:
    return next((v for v in master_versions(game) if v["is_current"]), None)


def master_content(master_id: int) -> bytes | None:
    return _master_content(db.describe(), int(master_id))


@functools.lru_cache(maxsize=8)  # một phiên bản master không bao giờ sửa
def _master_content(_where: str, master_id: int) -> bytes | None:
    with connect() as c:
        row = c.execute("SELECT content FROM master_files WHERE id = ?", (master_id,)).fetchone()
    return bytes(row["content"]) if row else None
