"""Test chế độ team: CSDL, đăng nhập, phân quyền dữ liệu, token và API đồng bộ (HTTP thật trên localhost).

    python tests/test_team.py
"""
from __future__ import annotations

import os
import socket
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["L2M_DATA_DIR"] = tempfile.mkdtemp(prefix="l2m-team-test-")

from core import api_server, nc_setup, store, sync  # noqa: E402


def test_users_and_auth():
    assert store.user_count() == 0
    store.create_user("Admin", "Chủ server", "matkhau-admin-1", "admin", by="admin")
    store.create_user("an", "An", "matkhau-an-12", "member", by="admin")
    store.create_user("viewer1", "", "matkhau-view-1", "viewer", by="admin")
    for bad in (("an", "x", "matkhau-an-12", "member"), ("b", "", "short", "member"), ("c", "", "matkhau-ccc-1", "boss")):
        try:
            store.create_user(*bad, by="admin")
            raise AssertionError(f"phải lỗi: {bad}")
        except ValueError:
            pass
    assert store.authenticate("ADMIN", "matkhau-admin-1")["role"] == "admin"  # username không phân biệt hoa thường
    assert store.authenticate("an", "sai-mat-khau") is None
    u = store.authenticate("an", "matkhau-an-12")
    assert "password_hash" not in u and u["has_token"] is False
    store.update_user("an", "admin", active=False)
    assert store.authenticate("an", "matkhau-an-12") is None  # bị khoá
    store.update_user("an", "admin", active=True)
    store.set_password("an", "matkhau-moi-99", "admin")
    assert store.authenticate("an", "matkhau-moi-99") and not store.authenticate("an", "matkhau-an-12")


def test_sessions():
    sid = store.create_session("an")
    assert store.session_user(sid)["username"] == "an" and store.session_user("sai") is None
    store.update_user("an", "admin", active=False)  # khoá -> mọi phiên mất hiệu lực
    assert store.session_user(sid) is None
    store.update_user("an", "admin", active=True)
    sid = store.create_session("an")
    store.set_password("an", "matkhau-moi-99", "admin")  # đổi mật khẩu -> đăng xuất mọi thiết bị
    assert store.session_user(sid) is None
    sid = store.create_session("an")
    store.delete_session(sid)
    assert store.session_user(sid) is None


def test_activities():
    aid = store.add_activity("payment_errors", "Case nạp lỗi 26/10", {"metrics": {"Order lỗi": 5}}, "an",
                             {"a.xlsx": b"excel", "b.csv": b"1,1\r\n"}, note="đợt sáng")
    rec = store.get_activity(aid)
    assert rec["summary"]["metrics"]["Order lỗi"] == 5 and [f["name"] for f in rec["files"]] == ["a.xlsx", "b.csv"]
    assert store.get_file(rec["files"][1]["id"]) == ("b.csv", b"1,1\r\n")
    store.update_activity(aid, "admin", note="đã gửi CS", status="need_check")
    rec = store.get_activity(aid)
    assert rec["note"] == "đã gửi CS" and rec["updated_by"] == "admin"
    assert [r["id"] for r in store.list_activities(search="gửi CS")] == [aid]
    store.delete_activity(aid, "an")
    assert store.list_activities() == [] and len(store.list_activities(include_deleted=True)) == 1
    store.delete_activity(aid, "admin", restore=True)
    assert len(store.list_activities(kinds=["payment_errors"])) == 1
    actions = [r["action"] for r in store.changelog()]
    assert {"tạo", "sửa", "xoá", "khôi phục", "tạo thành viên"} <= set(actions)


def test_shared_items():
    cat = nc_setup.ItemCatalog()
    assert cat.lookup("Eva Seal Chest")["id"] == 138  # nạp sẵn từ resources/item_ids.json
    assert cat.lookup("Brand New Item")["id"] is None
    cat.learn("Brand New Item", 999, "Brand New Item (Bound)", by="an")
    cat.learn("BNI", 999, by="an")
    cat = nc_setup.ItemCatalog()
    assert cat.lookup("Brand New Item")["id"] == 999 and cat.lookup("bni")["how"] == "alias"
    store.delete_item(999, "admin")
    assert nc_setup.ItemCatalog().lookup("Brand New Item")["id"] is None
    assert any(r["action"] == "thêm Item ID" and r["username"] == "an" for r in store.changelog())


def test_games_isolated():
    jom = nc_setup.ItemCatalog("jom")
    assert jom.entries == [] and jom.lookup("Eva Seal Chest")["id"] is None  # Item ID L2M không lẫn sang game khác
    jom.learn("Royal Chest", 5001, by="an")
    assert nc_setup.ItemCatalog("jom").lookup("Royal Chest")["id"] == 5001
    assert nc_setup.ItemCatalog("l2m").lookup("Royal Chest")["id"] is None
    a1 = store.add_activity("webshop_audit", "JoM audit", {}, "an", game="jom")
    store.add_activity("webshop_audit", "L2M audit", {}, "an")
    assert [r["id"] for r in store.list_activities(game="jom")] == [a1]
    assert {r["game"] for r in store.list_activities()} >= {"jom", "l2m"}


def test_migrate_old_db():
    """CSDL tạo bởi bản trước (chưa có cột game) -> nâng cấp, dữ liệu cũ gán 'l2m'."""
    import sqlite3

    from core import config

    old_dir, saved = Path(tempfile.mkdtemp(prefix="l2m-old-")), config.DATA_DIR
    conn = sqlite3.connect(old_dir / "app.db")
    conn.executescript("""
        CREATE TABLE activities (id INTEGER PRIMARY KEY, kind TEXT NOT NULL, title TEXT, status TEXT, summary TEXT, note TEXT,
            source TEXT, sync_status TEXT, created_by TEXT, created_at TEXT, updated_by TEXT, updated_at TEXT,
            deleted INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE item_ids (item_id INTEGER PRIMARY KEY, name TEXT NOT NULL, aliases TEXT NOT NULL DEFAULT '[]',
            updated_by TEXT, updated_at TEXT);
        INSERT INTO activities(kind, title, status, summary) VALUES ('payment_errors', 'đợt cũ', 'done', '{}');
        INSERT INTO item_ids(item_id, name, aliases) VALUES (777, 'Old Item', '["OI"]');
        INSERT INTO item_ids(item_id, name, aliases, updated_by) VALUES (25, 'Relic sửa tay', '[]', 'huy');
    """)
    conn.commit()
    conn.close()
    try:
        config.DATA_DIR = old_dir
        store._ready.clear()
        assert store.list_activities()[0]["game"] == "l2m"
        rows = store.item_rows("l2m")
        assert any(r["item_id"] == 777 and r["aliases"] == ["OI"] for r in rows)
        by_id = {r["item_id"]: r for r in rows}
        assert 217 in by_id and by_id[217]["game_item_key"] == "541001423"  # item mới trong resources được bổ sung
        assert by_id[186]["note"].startswith("Key đúng")  # kèm ghi chú cảnh báo
        assert 83 in store.blocked_items("l2m")
        assert by_id[25]["name"] == "Relic sửa tay"  # dòng người dùng đã sửa không bị seed ghi đè
        store.upsert_item(777, "JoM item cùng số", [], "an", "jom")  # cùng item_id, khác game -> không đụng nhau
        assert {r["name"] for r in store.item_rows("l2m") if r["item_id"] == 777} == {"Old Item"}
    finally:
        config.DATA_DIR = saved
        store._ready.clear()


def test_settings_and_master_migration():
    import json

    from core import config

    tmp = Path(tempfile.mkdtemp(prefix="l2m-cfg-"))
    saved = (config.SETTINGS_PATH, config.MASTER_DIR)
    try:
        config.SETTINGS_PATH = tmp / "settings.json"
        config.SETTINGS_PATH.write_text(json.dumps({"automation": {
            "nc_app_group": "l2msa", "browser_channel": "chrome",
            "mytool_sold_package": {"SG": "https://mytool/sg"}}}), encoding="utf-8")
        s = config.load_settings()
        assert s["games"]["l2m"]["mytool_sold_package"]["SG"] == "https://mytool/sg"
        assert s["games"]["l2m"]["store_key_prefix"] == "com.ncv.l2m." and "nc_app_group" not in s["automation"]
        assert s["automation"]["browser_channel"] == "chrome" and config.game(s)["id"] == "l2m"
        s["games"]["jom"] = {"name": "Journey of Monarch"}
        config.save_settings(s)
        s = config.load_settings()
        assert s["games"]["jom"]["mytool_search_order"] == {"SEA": "", "VN": ""}  # game mới vẫn đủ trường
        assert config.game(s, "khong-co")["id"] == "l2m"
        config.MASTER_DIR = tmp / "master"
        config.MASTER_DIR.mkdir()
        (config.MASTER_DIR / "current.xlsx").write_bytes(b"x")
        (config.MASTER_DIR / "current.json").write_text("{}", encoding="utf-8")
        config._migrate_master_layout()
        assert (config.MASTER_DIR / "l2m" / "current.xlsx").read_bytes() == b"x"
        assert not (config.MASTER_DIR / "current.xlsx").exists()
    finally:
        config.SETTINGS_PATH, config.MASTER_DIR = saved


def test_tool_item_matching():
    tool = [{"item_id": 139, "name": "Fancy Soul Crystal Stone (11 Times) (Bound)"},
            {"item_id": 140, "name": "Fancy Soul Crystal Stone (1 Time) (Bound)"},
            {"item_id": 141, "name": "Fancy Soul Crystal Stone (11 Times)"},
            {"item_id": 300, "name": "Ink of Mana (Unique)(Bound)"},
            {"item_id": 301, "name": "Parchment of Mana (Bound)"}]
    top = nc_setup.rank_tool_items("Fancy Soul Crystal (11 Times) (Bound)", tool)
    assert top[0]["item_id"] == 139  # đúng số lần + đúng Bound đứng đầu
    assert nc_setup.rank_tool_items("Ink of Mana (Unique) (Khóa)", tool)[0]["item_id"] == 300

    class FakeAI:
        def json(self, system, prompt, schema, effort="low"):
            return {"picks": [{"excel_name": "X", "item_id": 139, "confidence": "high", "reason": "ok"},
                              {"excel_name": "Y", "item_id": 999, "confidence": "high", "reason": "bịa ID"}]}
    picks = nc_setup.ai_pick_items(FakeAI(), {"X": tool[:2], "Y": tool[3:]})
    assert set(picks) == {"X"}  # ID không thuộc ứng viên của tên đó bị loại

    store.save_tool_items("l2m", [{"item_id": 301, "name": "Parchment of Mana (Bound)"}])
    look = nc_setup.ItemCatalog("l2m").lookup("Parchment of Mana (Khóa)")
    assert look["id"] == 301 and look["confirmed"] and look["how"] == "trùng tên trên tool"
    assert store.tool_items_info("l2m")[0] == 1 and store.tool_items_info("jom")[0] == 0


def test_lookup_candidates():
    rows = [{"Item number": "195", "Item name(administrator)": "Pa'agrio's Seal Chest (Bound)", "App group": "NCV-Lineage2M"},
            {"No": "", "col2": "There are no item details."}]
    assert nc_setup.lookup_candidates(rows) == [{"item_id": 195, "name": "Pa'agrio's Seal Chest (Bound)"}]
    assert nc_setup.lookup_candidates([{"col1": "42", "col2": "Ink of Mana (Unique)(Bound)"}]) == \
        [{"item_id": 42, "name": "Ink of Mana (Unique)(Bound)"}]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_sync_api():
    port = _free_port()
    srv = api_server.start("127.0.0.1", port)
    try:
        token = store.issue_token("an", "admin")
        good = {"team": {"server_url": f"http://127.0.0.1:{port}", "token": token}}
        ok, msg = sync.ping(good)
        assert ok and "'an'" in msg, msg
        ok, info = sync.push(good, "webshop_audit", "Kiểm tra từ máy An", {"metrics": {"Sai": 1}},
                             {"report.md": "báo cáo".encode()}, note="local")
        assert ok, info
        rec = store.get_activity(int(info.lstrip("#")))
        assert rec["created_by"] == "an" and rec["source"] == "local:an" and rec["game"] == "l2m"
        ok, info = sync.push(good, "master", "JoM master", {}, game="jom")
        assert ok and store.get_activity(int(info.lstrip("#")))["game"] == "jom"
        assert store.get_file(rec["files"][0]["id"])[1].decode() == "báo cáo"
        assert sync.ping({"team": {"server_url": good["team"]["server_url"], "token": "sai"}})[0] is False
        ok, info = sync.push({"team": {"server_url": good["team"]["server_url"], "token": "sai"}}, "webshop_audit", "x", {})
        assert not ok and "401" in info
        viewer_token = store.issue_token("viewer1", "admin")
        ok, info = sync.push({"team": {"server_url": good["team"]["server_url"], "token": viewer_token}}, "webshop_audit", "x", {})
        assert not ok and "403" in info
        ok, info = sync.push(good, "hack", "x", {})
        assert not ok and "400" in info
        old = token
        store.issue_token("an", "admin")  # cấp mới -> token cũ hết hiệu lực
        assert sync.ping({"team": {"server_url": good["team"]["server_url"], "token": old}})[0] is False
        ok, info = sync.push({"team": {"server_url": f"http://127.0.0.1:{_free_port()}", "token": token}}, "master", "x", {})
        assert not ok and "Không kết nối" in info
    finally:
        srv.shutdown()


if __name__ == "__main__":
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
