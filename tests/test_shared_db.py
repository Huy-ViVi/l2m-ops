"""Kiểm tra chế độ CSDL chung (Postgres / Supabase) trên một schema tạm — không đụng dữ liệu thật, xoá schema khi xong.

    set L2M_TEST_DATABASE_URL=postgresql://...      (cùng địa chỉ với CSDL chung là được)
    .venv\\Scripts\\python.exe tests\\test_shared_db.py

Không có L2M_TEST_DATABASE_URL thì bỏ qua.
"""
from __future__ import annotations

import os
import secrets
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

URL = os.environ.get("L2M_TEST_DATABASE_URL", "").strip()
SCHEMA = f"l2m_test_{secrets.token_hex(4)}"
if URL:
    os.environ["DATABASE_URL"] = URL
    os.environ["L2M_DB_SCHEMA"] = SCHEMA
    os.environ["L2M_DATA_DIR"] = tempfile.mkdtemp(prefix="l2m-shared-test-")
    os.environ.pop("L2M_APP_MODE", None)

from core import config, db, store  # noqa: E402


def test_mode_and_schema():
    assert db.is_remote() and config.team_mode(), "nối CSDL chung thì phải là chế độ team"
    from urllib.parse import urlparse

    password = urlparse(URL).password
    assert db.describe().startswith("postgres @") and (not password or password not in db.describe()), "không được lộ mật khẩu"
    store.init()
    with store.connect() as c:
        assert c.execute("SELECT current_schema()").fetchone()[0] == SCHEMA
        tables = {r["t"] for r in c.execute(
            "SELECT table_name AS t FROM information_schema.tables WHERE table_schema = current_schema()")}
    assert {"users", "activities", "activity_files", "item_ids", "tool_items", "app_settings", "master_files"} <= tables
    rows = store.item_rows("l2m")
    assert len(rows) >= 40 and any(r["item_id"] == 79 for r in rows), "bảng Item ID có sẵn phải được nạp"


def test_transaction_pooler():
    """Pooler Supabase: dùng cổng 6543 (transaction, ~200 kết nối) thay 5432 (session, cả team chỉ 15 — hết chỗ là lỗi
    EMAXCONNSESSION). Schema test đặt bằng SET LOCAL nên không lọt sang kết nối máy chủ dùng chung."""
    import psycopg

    pooler = "postgresql://postgres.abc:pw@aws-0-ap-northeast-2.pooler.supabase.com"
    assert db.pooled_url(pooler + ":5432/postgres") == pooler + ":6543/postgres"
    assert db.pooled_url(pooler + ":6543/postgres") == pooler + ":6543/postgres"
    assert db.pooled_url("postgresql://u:pw@db.example.com:5432/app") == "postgresql://u:pw@db.example.com:5432/app"
    for _ in range(3):
        with store.connect() as c:
            assert c.execute("SELECT current_schema()").fetchone()[0] == SCHEMA
    with psycopg.connect(db.pooled_url(URL), prepare_threshold=None, autocommit=True) as plain:
        for _ in range(5):
            assert plain.execute("SELECT current_schema()").fetchone()[0] == "public", "schema test lọt sang kết nối khác"


def test_users_sessions():
    store.create_user("Huy", "Huy", "password-123", "admin", by="test")
    try:
        store.create_user("huy", "x", "password-123", "member", by="test")
        raise AssertionError("trùng username phải báo lỗi")
    except ValueError:
        pass
    assert store.authenticate("HUY", "password-123")["role"] == "admin"
    assert store.authenticate("huy", "sai-mat-khau") is None
    sid = store.create_session("huy")
    assert store.session_user(sid)["username"] == "huy"
    store.update_user("huy", "test", active=False)  # khoá -> phiên bị xoá, cache phải cập nhật ngay
    assert store.session_user(sid) is None and store.get_user("huy")["active"] == 0
    store.update_user("huy", "test", active=True)
    assert store.user_count() == 1 and store.list_users()[0]["username"] == "huy"


def test_activities_files_search():
    aid = store.add_activity("nc_setup", "Setup 2 gói Diamond", {"metrics": {"Gói": 2}}, "huy",
                             files={"plan.json": b'{"a": 1}', "x.bin": bytes(range(256))}, game="l2m")
    assert isinstance(aid, int) and aid > 0
    rec = store.get_activity(aid)
    assert rec["summary"]["metrics"]["Gói"] == 2 and [f["name"] for f in rec["files"]] == ["plan.json", "x.bin"]
    assert rec["files"][1]["size"] == 256
    assert store.get_file(rec["files"][1]["id"]) == ("x.bin", bytes(range(256)))
    assert [r["id"] for r in store.list_activities(search="diamond")] == [aid], "tìm kiếm không phân biệt hoa thường"
    store.update_activity(aid, "huy", note="đã kiểm", status="need_check")
    assert store.get_activity(aid)["status"] == "need_check"
    store.delete_activity(aid, "huy")
    assert not store.list_activities(game="l2m") and store.list_activities(include_deleted=True, game="l2m")
    assert store.changelog()[0]["action"] == "xoá"


def test_items_and_tool_items():
    store.upsert_item(901, "Test Item", ["Alias A"], "huy", "l2m", game_item_key="123")
    store.add_alias(901, "Alias B", "huy", "l2m")
    row = next(r for r in store.item_rows("l2m") if r["item_id"] == 901)
    assert row["aliases"] == ["Alias A", "Alias B"] and row["game_item_key"] == "123"
    store.delete_item(901, "huy", "l2m")
    assert all(r["item_id"] != 901 for r in store.item_rows("l2m"))
    n = store.save_tool_items("l2m", [{"item_id": i, "name": f"Item {i}"} for i in range(1, 301)] + [{"item_id": 5, "name": "Item 5b"}])
    assert n == 301 and store.tool_items_info("l2m")[0] == 300
    assert next(r for r in store.tool_items("l2m") if r["item_id"] == 5)["name"] == "Item 5b"


def test_shared_settings():
    s = config.load_settings()  # lần đầu: cấu hình máy này thành cấu hình chung
    assert store.get_app_setting("shared")["games"]["l2m"]["nc_app_group"] == "l2msa"
    s["games"]["test"] = {**config.blank_game("Test Game"), "nc_app_group": "tstsa"}
    s["default_lang"] = "en"
    config.save_settings(s, by="huy")
    config.SETTINGS_PATH.unlink()  # như một máy khác: không có settings.json riêng
    store.clear_cache()
    s2 = config.load_settings()
    assert s2["games"]["test"]["nc_app_group"] == "tstsa" and s2["default_lang"] == "en"
    del s2["games"]["test"]
    config.save_settings(s2, by="huy")
    store.clear_cache()
    assert "test" not in config.load_settings()["games"], "game đã xoá không được quay lại"


def test_masters():
    first = store.add_master("l2m", "v1.xlsx", b"PK-v1", "huy")
    second = store.add_master("l2m", "v2.xlsx", b"PK-v2", "huy")
    versions = store.master_versions("l2m")
    assert [v["id"] for v in versions] == [second, first] and versions[0]["size"] == 5
    assert store.current_master("l2m")["name"] == "v2.xlsx" and store.master_content(first) == b"PK-v1"
    assert store.current_master("other") is None


def test_cache_sees_other_machines():
    """Máy khác ghi thẳng vào CSDL -> máy này thấy sau tối đa CACHE_TTL giây."""
    import psycopg

    store.CACHE_TTL = 60  # đủ dài để lượt đọc thứ hai chắc chắn còn trong cache, dù mạng tới CSDL chậm
    try:
        before = store.list_activities(include_deleted=True, game="l2m")
        with psycopg.connect(db.pooled_url(URL), prepare_threshold=None) as other:
            other.execute(f'SET LOCAL search_path TO "{SCHEMA}"')
            other.execute("INSERT INTO activities(kind, title, status, summary, created_by, created_at, updated_by, updated_at, game) "
                          "VALUES ('nc_setup', 'from other machine', 'done', '{}', 'bob', '2026-10-27 10:00:00', 'bob', '2026-10-27 10:00:00', 'l2m')")
        assert len(store.list_activities(include_deleted=True, game="l2m")) == len(before)  # còn trong cache
        store.CACHE_TTL = 0.5  # hết hạn -> đọc lại CSDL, thấy bản ghi của máy kia
        time.sleep(0.6)
        assert len(store.list_activities(include_deleted=True, game="l2m")) == len(before) + 1
    finally:
        store.CACHE_TTL = 15


def test_migration_script():
    """Chép dữ liệu một thư mục data/ kiểu SQLite lên schema mới."""
    from tools import migrate_to_shared_db as mig

    src = Path(tempfile.mkdtemp(prefix="l2m-migrate-src-"))
    conn = sqlite3.connect(src / "app.db")
    conn.executescript(store.SCHEMA)
    conn.execute("ALTER TABLE item_ids ADD COLUMN game_item_key TEXT NOT NULL DEFAULT ''")
    conn.execute("ALTER TABLE item_ids ADD COLUMN note TEXT NOT NULL DEFAULT ''")
    conn.execute("INSERT INTO users(id, username, display_name, password_hash, role, active, created_at) "
                 "VALUES (7, 'huy', 'Huy', ?, 'admin', 1, '2026-10-01 08:00:00')", (store.hash_password("password-123"),))
    conn.execute("INSERT INTO activities(id, kind, title, status, summary, note, source, created_by, created_at, updated_by, updated_at, deleted, game) "
                 "VALUES (42, 'nc_setup', '[Cowork] Setup 3 gói', 'done', '{}', '', 'cowork', 'huy', '2026-06-11 00:00:00', 'huy', '2026-06-11 00:00:00', 0, 'l2m')")
    conn.execute("INSERT INTO activity_files(id, activity_id, name, content) VALUES (3, 42, 'log.md', ?)", (b"# log",))
    conn.execute("INSERT INTO item_ids(game, item_id, name, aliases, updated_by, updated_at, game_item_key, note) "
                 "VALUES ('l2m', 25, 'Edited by user', '[]', 'huy', '2026-10-01 08:00:00', '', '')")
    conn.commit()
    conn.close()
    (src / "master" / "l2m" / "history").mkdir(parents=True)
    (src / "master" / "l2m" / "history" / "20261001-080000_old.xlsx").write_bytes(b"old")
    (src / "master" / "l2m" / "history" / "20261020-090000_new.xlsx").write_bytes(b"new")
    (src / "master" / "l2m" / "current.xlsx").write_bytes(b"new")
    (src / "master" / "l2m" / "current.json").write_text('{"name": "new.xlsx", "uploaded_at": "20/10/2026 09:00", "uploaded_by": "huy"}', encoding="utf-8")
    (src / "settings.json").write_text('{"default_lang": "en", "games": {"l2m": {"name": "Lineage2M SEA"}}}', encoding="utf-8")

    os.environ["L2M_DB_SCHEMA"] = SCHEMA + "_mig"
    store.clear_cache()
    try:
        counts = mig.migrate(src, log=lambda *_: None)
        assert counts["users"] == 1 and counts["activities"] == 1 and counts["files"] == 1 and counts["masters"] == 2
        assert store.authenticate("huy", "password-123")["id"] == 7
        assert store.get_activity(42)["files"][0]["name"] == "log.md"
        aid = store.add_activity("nc_setup", "after migrate", {}, "huy")
        assert aid > 42, "id mới phải nối sau id đã chép"
        assert next(r for r in store.item_rows("l2m") if r["item_id"] == 25)["name"] == "Edited by user"
        assert store.current_master("l2m")["name"] == "new.xlsx" and len(store.master_versions("l2m")) == 2
        assert store.get_app_setting("shared")["default_lang"] == "en"
        try:
            mig.migrate(src, log=lambda *_: None)
            raise AssertionError("chạy lần 2 phải dừng vì CSDL đích đã có dữ liệu")
        except SystemExit:
            pass
    finally:
        _drop(SCHEMA + "_mig")
        os.environ["L2M_DB_SCHEMA"] = SCHEMA
        store.clear_cache()


def _drop(schema: str) -> None:
    import psycopg

    db.close_all()
    with psycopg.connect(db.pooled_url(URL), prepare_threshold=None, autocommit=True) as conn:
        conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')


if __name__ == "__main__":
    if not URL:
        print("SKIP test_shared_db: chưa đặt L2M_TEST_DATABASE_URL")
        sys.exit(0)
    failed = 0
    try:
        for name, fn in list(globals().items()):
            if name.startswith("test_") and callable(fn):
                t0 = time.monotonic()
                try:
                    fn()
                    print(f"PASS {name} ({time.monotonic() - t0:.1f}s)")
                except Exception as e:  # noqa: BLE001
                    failed += 1
                    import traceback

                    print(f"FAIL {name}: {type(e).__name__}: {e}")
                    traceback.print_exc()
    finally:
        _drop(SCHEMA)
        print(f"(đã xoá schema tạm {SCHEMA})")
    sys.exit(1 if failed else 0)
