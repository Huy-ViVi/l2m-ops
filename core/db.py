"""Kết nối CSDL cho core/store.py.

- Mặc định: SQLite, file data/app.db trên máy chạy app (như trước).
- Có DATABASE_URL (Postgres, vd Supabase): website trên Streamlit Cloud và bản local của từng thành viên
  cùng đọc/ghi một CSDL, nên mọi người thấy ngay thay đổi của nhau.

SQL trong store viết theo kiểu SQLite (dấu ?, LIKE); lớp _PgConn đổi sang cú pháp Postgres khi chạy.
"""
from __future__ import annotations

import atexit
import os
import re
import sqlite3
import threading
from contextlib import contextmanager

from . import config

try:  # chỉ cần khi dùng Postgres
    import psycopg
    from psycopg_pool import ConnectionPool

    IntegrityError: tuple = (sqlite3.IntegrityError, psycopg.IntegrityError)
except ImportError:  # pragma: no cover — máy chưa cài psycopg vẫn chạy được chế độ SQLite
    psycopg = None
    IntegrityError = (sqlite3.IntegrityError,)

_WRITE = re.compile(r"^\s*(INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\b", re.I)


def is_remote() -> bool:
    return bool(config.database_url())


def describe() -> str:
    """Mô tả ngắn để hiển thị (không lộ mật khẩu): 'postgres @ host/db' hoặc đường dẫn file SQLite."""
    url = config.database_url()
    if not url:
        return str(config.DATA_DIR / "app.db")
    m = re.match(r"^\w+://(?:[^@/]*@)?([^/:?]+)(?::\d+)?/([^?]*)", url)
    return f"postgres @ {m.group(1)}/{m.group(2)}" if m else "postgres"


class _Row(dict):
    """Dòng kết quả đọc được cả theo tên cột lẫn theo vị trí (giống sqlite3.Row)."""

    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


def _row_factory(cursor):
    names = [d.name for d in cursor.description] if cursor.description else []
    return lambda values: _Row(zip(names, values))


class _PgConn:
    """Bọc kết nối psycopg cho giống sqlite3: execute / executemany / executescript với dấu ?."""

    def __init__(self, conn):
        self._conn = conn
        self.dirty = False  # có câu lệnh ghi -> store xoá cache đọc

    @staticmethod
    def _sql(sql: str) -> str:
        return re.sub(r"\bLIKE\b", "ILIKE", sql.replace("?", "%s"))  # LIKE của SQLite không phân biệt hoa thường

    def _mark(self, sql: str) -> None:
        if _WRITE.match(sql):
            self.dirty = True

    def execute(self, sql: str, params=()):
        self._mark(sql)
        cur = self._conn.cursor()
        cur.execute(self._sql(sql), tuple(params) if params else None)
        return cur

    def executemany(self, sql: str, seq):
        self._mark(sql)
        rows = [tuple(p) for p in seq]
        cur = self._conn.cursor()
        if rows:
            cur.executemany(self._sql(sql), rows)
        return cur

    def executescript(self, script: str) -> None:
        self.dirty = True
        self._conn.execute(script)


class _SqliteConn(sqlite3.Connection):
    dirty = False

    def execute(self, sql, params=()):
        if _WRITE.match(sql):
            self.dirty = True
        return super().execute(sql, params)

    def executemany(self, sql, seq):
        if _WRITE.match(sql):
            self.dirty = True
        return super().executemany(sql, seq)


_pools: dict[tuple, "ConnectionPool"] = {}
_pool_lock = threading.Lock()


def _db_schema() -> str | None:
    """L2M_DB_SCHEMA: dùng schema riêng trong cùng CSDL (để chạy test mà không đụng dữ liệu thật)."""
    name = os.environ.get("L2M_DB_SCHEMA", "").strip()
    if name and not re.fullmatch(r"[a-z_][a-z0-9_]{0,40}", name):
        raise ValueError(f"L2M_DB_SCHEMA không hợp lệ: {name}")
    return name or None


def pooled_url(url: str) -> str:
    """Pooler của Supabase: dùng cổng 6543 (chế độ transaction) thay cho 5432 (chế độ session).
    Chế độ session giữ riêng một kết nối máy chủ cho mỗi kết nối của ứng dụng, cả team (website + agent của từng người +
    tiến trình chạy lệnh của agent) chỉ được 15 -> hết chỗ thì báo EMAXCONNSESSION / PoolTimeout. Chế độ transaction chỉ
    mượn kết nối máy chủ trong lúc chạy một giao dịch, nhận tới ~200 kết nối. Địa chỉ đã lưu (secrets, data/local.json,
    zip agent) giữ nguyên cổng 5432, đổi ở đây."""
    return re.sub(r"(@[^/@?]+\.pooler\.supabase\.com):5432(?=/|\?|$)", r"\1:6543", url)


def _configure(conn) -> None:
    name = _db_schema()
    if name:
        try:
            conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{name}"')
        except psycopg.errors.UniqueViolation:  # hai kết nối của pool cùng tạo schema một lúc
            conn.rollback()
        conn.commit()


def _pool(url: str) -> "ConnectionPool":
    if psycopg is None:
        from .i18n import t

        raise RuntimeError(t("Chưa cài psycopg — chạy: pip install -r requirements.txt"))
    key = (url, _db_schema())
    with _pool_lock:
        pool = _pools.get(key)
        if pool is None:
            # prepare_threshold=None: chạy được qua pooler của Supabase ở chế độ transaction.
            pool = ConnectionPool(pooled_url(url), min_size=1, max_size=4, max_idle=300, timeout=30, open=True,
                                  check=ConnectionPool.check_connection, configure=_configure,
                                  kwargs={"prepare_threshold": None, "row_factory": _row_factory, "connect_timeout": 15})
            _pools[key] = pool
        return pool


@contextmanager
def connect():
    """Một giao dịch: thoát bình thường thì commit, có lỗi thì rollback."""
    url = config.database_url()
    if url:
        with _pool(url).connection() as conn:  # pool tự commit / rollback
            name = _db_schema()
            if name:  # SET LOCAL: chỉ trong giao dịch này — kết nối máy chủ của pooler dùng chung, SET thường sẽ lọt sang người khác
                conn.execute(f'SET LOCAL search_path TO "{name}"')
            yield _PgConn(conn)
        return
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DATA_DIR / "app.db", timeout=15, factory=_SqliteConn)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.dirty = False
        yield conn
        conn.commit()
    finally:
        conn.close()


def now_sql(seconds_ago: int = 0) -> str:
    """Biểu thức SQL: giờ hiện tại *của CSDL* theo giờ team, dạng 'YYYY-MM-DD HH:MM:SS'. Dùng khi so mốc giờ do nhiều máy
    ghi (website, agent): đồng hồ từng máy có thể lệch nhau, đồng hồ CSDL thì chỉ có một."""
    hours = int(config.TEAM_TZ.utcoffset(None).total_seconds() // 3600)
    seconds = int(seconds_ago)
    if is_remote():
        return (f"to_char((now() AT TIME ZONE 'UTC') + interval '{hours} hours' - interval '{seconds} seconds', "
                "'YYYY-MM-DD HH24:MI:SS')")
    return f"datetime('now', '{hours:+d} hours', '-{seconds} seconds')"


def schema(sqlite_schema: str) -> str:
    """Schema viết cho SQLite -> Postgres khi cần."""
    if not is_remote():
        return sqlite_schema
    return sqlite_schema.replace("INTEGER PRIMARY KEY,", "BIGSERIAL PRIMARY KEY,").replace("BLOB", "BYTEA")


def columns(c, table: str) -> set[str]:
    if is_remote():
        return {r["name"] for r in c.execute(
            "SELECT column_name AS name FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = ?",
            (table,))}
    return {r["name"] for r in c.execute(f"PRAGMA table_info({table})")}


def test_connection(url: str) -> tuple[bool, str]:
    """Thử kết nối một địa chỉ Postgres (trước khi lưu). Thông báo lỗi không chứa mật khẩu."""
    from .i18n import t

    if psycopg is None:
        return False, t("Chưa cài psycopg — chạy: pip install -r requirements.txt")
    if not re.match(r"^postgres(ql)?://", url or ""):
        return False, t("Địa chỉ phải bắt đầu bằng postgresql://")
    try:
        with psycopg.connect(pooled_url(url), connect_timeout=10, prepare_threshold=None) as conn:
            version = conn.execute("SHOW server_version").fetchone()[0]
        return True, t("Kết nối được (Postgres {version}).", version=version)
    except Exception as e:  # noqa: BLE001 — lỗi mạng / sai mật khẩu đều báo lên UI
        message = str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__
        return False, t("Không kết nối được: {error}", error=message.replace(url, "***"))


def close_all() -> None:
    with _pool_lock:
        for pool in _pools.values():
            pool.close()
        _pools.clear()


atexit.register(close_all)  # đóng pool khi tiến trình thoát (tránh lỗi "cannot join thread at interpreter shutdown")
