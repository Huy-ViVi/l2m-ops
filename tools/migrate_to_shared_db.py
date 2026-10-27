"""Chuyển dữ liệu của máy này (data/app.db, master, cài đặt chung) lên CSDL chung (Postgres / Supabase).

    .venv\\Scripts\\python.exe tools\\migrate_to_shared_db.py --url "postgresql://..."
    (hoặc đặt biến môi trường DATABASE_URL; --url bỏ trống thì lấy từ data/local.json)

Chép: tài khoản, lịch sử hoạt động + file đính kèm, bảng Item ID, danh sách item tải từ NC tool, nhật ký thay đổi,
mọi phiên bản master (đánh dấu bản hiện hành) và cài đặt chung (game, AI...). Không chép phiên đăng nhập.
CSDL đích đã có lịch sử / tài khoản thì dừng lại (tránh nhân đôi), trừ khi thêm --force.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _source_rows(conn: sqlite3.Connection, table: str) -> list[dict]:
    try:
        return [dict(r) for r in conn.execute(f"SELECT * FROM {table}")]
    except sqlite3.OperationalError:  # bảng chưa có ở CSDL bản cũ
        return []


def _stamp_to_ts(stamp: str) -> str:
    try:
        return datetime.strptime(stamp, "%Y%m%d-%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _meta_to_ts(text: str) -> str:
    try:
        return datetime.strptime(text, "%d/%m/%Y %H:%M").strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def migrate(source_dir: Path, force: bool = False, log=print) -> dict:
    """Chép dữ liệu từ source_dir (thư mục data/ kiểu SQLite) sang CSDL ở DATABASE_URL hiện tại."""
    from core import config, db, store

    if not db.is_remote():
        raise SystemExit("Chưa có địa chỉ CSDL chung (--url hoặc DATABASE_URL).")
    store.init()
    with store.connect() as c:
        n_act = c.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
        n_users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if (n_act or n_users) and not force:
        raise SystemExit(f"CSDL đích đã có {n_users} tài khoản, {n_act} bản ghi lịch sử. Thêm --force nếu vẫn muốn chép thêm.")

    src_db = source_dir / "app.db"
    counts: dict[str, int] = {}
    if src_db.exists():
        src = sqlite3.connect(src_db)
        src.row_factory = sqlite3.Row
        users = _source_rows(src, "users")
        acts = _source_rows(src, "activities")
        files = _source_rows(src, "activity_files")
        items = _source_rows(src, "item_ids")
        tools = _source_rows(src, "tool_items")
        logs = _source_rows(src, "changelog")
        src.close()
        with store.connect() as c:
            c.executemany("INSERT INTO users(id, username, display_name, password_hash, role, active, token_hash, created_at) "
                          "VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(username) DO NOTHING",
                          [(u["id"], u["username"], u["display_name"], u["password_hash"], u["role"], u["active"],
                            u.get("token_hash"), u["created_at"]) for u in users])
            c.executemany("INSERT INTO activities(id, kind, title, status, summary, note, source, sync_status, created_by, created_at, "
                          "updated_by, updated_at, deleted, game) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          [(a["id"], a["kind"], a["title"], a["status"], a["summary"], a["note"], a["source"], a.get("sync_status"),
                            a["created_by"], a["created_at"], a["updated_by"], a["updated_at"], a["deleted"], a.get("game") or "l2m")
                           for a in acts])
            c.executemany("INSERT INTO activity_files(id, activity_id, name, content) VALUES (?,?,?,?)",
                          [(f["id"], f["activity_id"], f["name"], bytes(f["content"])) for f in files])
            c.executemany(store.ITEM_UPSERT,
                          [(i.get("game") or "l2m", i["item_id"], i["name"], i["aliases"], i["updated_by"], i["updated_at"],
                            i.get("game_item_key") or "", i.get("note") or "") for i in items])
            c.executemany("INSERT INTO tool_items(game, item_id, name, updated_at) VALUES (?,?,?,?) "
                          "ON CONFLICT(game, item_id) DO UPDATE SET name = excluded.name, updated_at = excluded.updated_at",
                          [(r["game"], r["item_id"], r["name"], r["updated_at"]) for r in tools])
            c.executemany("INSERT INTO changelog(at, username, action, target, detail) VALUES (?,?,?,?,?)",
                          [(r["at"], r["username"], r["action"], r["target"], r["detail"]) for r in logs])
            for table in ("users", "activities", "activity_files"):  # id tiếp theo nối sau id đã chép
                c.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)")
        counts.update(users=len(users), activities=len(acts), files=len(files), item_ids=len(items), tool_items=len(tools),
                      changelog=len(logs))
        log(f"CSDL: {len(users)} tài khoản, {len(acts)} bản ghi, {len(files)} file, {len(items)} Item ID, {len(tools)} item tool, "
            f"{len(logs)} dòng nhật ký")
    else:
        log(f"Không thấy {src_db} — bỏ qua phần CSDL.")

    masters = 0
    master_root = source_dir / "master"
    for game_dir in sorted(p for p in master_root.iterdir() if p.is_dir()) if master_root.exists() else []:
        gid = game_dir.name
        versions = sorted((game_dir / "history").glob("*.xlsx")) if (game_dir / "history").exists() else []
        current = game_dir / "current.xlsx"
        meta = json.loads((game_dir / "current.json").read_text(encoding="utf-8-sig")) if (game_dir / "current.json").exists() else {}
        current_bytes = current.read_bytes() if current.exists() else None
        current_done = False
        for i, p in enumerate(versions):
            stamp, _, name = p.name.partition("_")
            data = p.read_bytes()
            is_current = current_bytes is not None and i == len(versions) - 1 and data == current_bytes
            store.add_master(gid, name, data, meta.get("uploaded_by", "") if is_current else "", _stamp_to_ts(stamp), current=is_current)
            current_done = current_done or is_current
            masters += 1
        if current_bytes is not None and not current_done:
            store.add_master(gid, meta.get("name", "current.xlsx"), current_bytes, meta.get("uploaded_by", ""),
                             _meta_to_ts(meta.get("uploaded_at")), current=True)
            masters += 1
    counts["masters"] = masters
    log(f"Master: {masters} phiên bản")

    settings_path = source_dir / "settings.json"
    if settings_path.exists():
        stored = config._migrate(json.loads(settings_path.read_text(encoding="utf-8-sig")))
        merged = config._merge(config.DEFAULTS, stored)
        store.set_app_setting("shared", {k: merged[k] for k in config.SHARED_KEYS}, "migrate")
        counts["settings"] = 1
        log("Cài đặt chung: đã chép (game, AI, NC tool, ngôn ngữ mặc định)")
    store.clear_cache()
    return counts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", help="Postgres URI của CSDL chung")
    ap.add_argument("--source", default=str(ROOT / "data"), help="thư mục data/ nguồn (mặc định data/ của app)")
    ap.add_argument("--force", action="store_true", help="vẫn chép khi CSDL đích đã có dữ liệu")
    args = ap.parse_args()
    if args.url:
        os.environ["DATABASE_URL"] = args.url
    from core import db

    try:
        migrate(Path(args.source), force=args.force)
    finally:
        db.close_all()  # đóng pool trước khi Python thoát
    print("Xong.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
