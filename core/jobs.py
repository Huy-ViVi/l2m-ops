"""Hàng đợi thao tác tự động cho website (CSDL chung).

Website không vào được NC tool / MyTool (cần VPN công ty + SSO), nên khi bấm nút trên website:
1. website ghi lệnh vào bảng jobs (requested_by = tài khoản đang đăng nhập);
2. agent của chính tài khoản đó (automation/agent.py trên máy người đó, có VPN + phiên SSO của họ) nhận lệnh,
   chạy automation.runner như bản local, đẩy log lên từng giây;
3. xong thì agent ghi kết quả (file tải về nằm ở bảng job_files) — website đọc và chạy tiếp như bản local.
Lệnh đi theo tài khoản, nên mỗi người phải đăng nhập bằng tài khoản riêng.
Mốc giờ lấy theo đồng hồ của CSDL (db.now_sql) vì website và agent chạy trên các máy có thể lệch giờ.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from . import db, store

HEARTBEAT_SECONDS = 10     # agent báo "còn sống" mỗi chừng này giây
ONLINE_SECONDS = 45        # quá chừng này không thấy tín hiệu -> coi như agent đã tắt
QUEUE_EXPIRE_SECONDS = 120  # lệnh chờ quá lâu thì agent bỏ qua, tránh mở NC tool lúc người bấm không còn chờ
KEEP_DAYS = 7              # xoá lệnh cũ (kèm file) sau chừng này ngày
FILE_PREFIX = "jobfile://"
FINISHED = ("done", "error", "expired", "cancelled")
CONTROL_PREFIX = "agent:"  # lệnh điều khiển agent (không chạy automation.runner)
SHOW_WINDOW = "agent:show"  # nút "Hiện cửa sổ agent" trên website
CHECK_MACHINE = "agent:check"  # nút "Kiểm tra lại": agent tự kiểm tra máy ngay (không chờ nhịp 1 phút)
SITE_ROW = "~website"       # dòng trong bảng agents lưu bản code của website (agent so để báo có bản mới)
PROTOCOL = "l2mops-agent"   # agent.bat đăng ký l2mops-agent:// trên máy: website bấm link này để bật agent

_status_cache: dict[str, tuple[float, dict | None]] = {}


# ---- agent ------------------------------------------------------------------------
def heartbeat(username: str, host: str, version: str = "", checks: dict | None = None) -> None:
    """checks: kết quả agent tự kiểm tra máy (vd {'edge': True, 'nc_tool': False}) — website dùng để báo máy đủ điều kiện."""
    store.init()
    with store.connect() as c:
        c.execute(f"INSERT INTO agents(username, host, seen_at, version, checks) VALUES (?, ?, {db.now_sql()}, ?, ?) "
                  "ON CONFLICT(username) DO UPDATE SET host = excluded.host, seen_at = excluded.seen_at, version = excluded.version, "
                  "checks = excluded.checks", (username, host, version, json.dumps(checks or {})))


def agent_offline(username: str) -> None:
    store.init()
    with store.connect() as c:
        c.execute(f"UPDATE agents SET seen_at = {db.now_sql(ONLINE_SECONDS + 60)} WHERE username = ?", (username,))
    _status_cache.pop(username, None)


def _agent_row(row) -> dict:
    try:
        checks = json.loads(row["checks"] or "{}")
    except (TypeError, ValueError):
        checks = {}
    return {"host": row["host"], "seen_at": row["seen_at"], "version": row["version"] or "", "checks": checks}


def agent_status(username: str, fresh: bool = False) -> dict | None:
    """Agent của tài khoản này nếu đang chạy: {'host', 'seen_at', 'version', 'checks'}; None nếu chưa bật.
    Nhớ 10 giây cho trang khỏi chờ CSDL."""
    hit = _status_cache.get(username)
    if hit and not fresh and time.monotonic() - hit[0] < HEARTBEAT_SECONDS:
        return hit[1]
    store.init()
    with store.connect() as c:
        row = c.execute(f"SELECT host, seen_at, version, checks FROM agents WHERE username = ? "
                        f"AND seen_at >= {db.now_sql(ONLINE_SECONDS)}", (username,)).fetchone()
    value = _agent_row(row) if row else None
    _status_cache[username] = (time.monotonic(), value)
    return value


def agent_known(username: str) -> dict | None:
    """Lần cuối agent của tài khoản này báo về (kể cả khi đã tắt): tài khoản đã từng cài agent ở máy nào."""
    store.init()
    with store.connect() as c:
        row = c.execute("SELECT host, seen_at, version, checks FROM agents WHERE username = ?", (username,)).fetchone()
    return _agent_row(row) if row else None


def claim(username: str, host: str) -> dict | None:
    """Agent nhận lệnh cũ nhất đang chờ của tài khoản này (hai agent cùng tài khoản cũng chỉ một bên nhận được)."""
    store.init()
    with store.connect() as c:
        c.execute(f"UPDATE jobs SET status = 'expired', finished_at = {db.now_sql()} WHERE requested_by = ? AND status = 'queued' "
                  f"AND created_at < {db.now_sql(QUEUE_EXPIRE_SECONDS)}", (username,))
        row = c.execute(
            f"UPDATE jobs SET status = 'running', agent = ?, started_at = {db.now_sql()} WHERE id = (SELECT id FROM jobs "
            "WHERE requested_by = ? AND status = 'queued' AND job NOT LIKE ? ORDER BY id LIMIT 1) AND status = 'queued' "
            "RETURNING id, job, payload, created_at", (host, username, CONTROL_PREFIX + "%")).fetchone()
    return dict(row) if row else None


def claim_controls(username: str, host: str) -> set[str]:
    """Agent nhận mọi lệnh điều khiển đang chờ (vd hiện cửa sổ, kiểm tra máy) — đánh dấu xong luôn. Trả về tên các lệnh."""
    store.init()
    with store.connect() as c:
        rows = c.execute(
            f"UPDATE jobs SET status = 'done', agent = ?, started_at = {db.now_sql()}, finished_at = {db.now_sql()} "
            f"WHERE requested_by = ? AND job LIKE ? AND status = 'queued' AND created_at >= {db.now_sql(QUEUE_EXPIRE_SECONDS)} "
            "RETURNING job", (host, username, CONTROL_PREFIX + "%")).fetchall()
    return {r["job"] for r in rows}


def site_version() -> str:
    """Bản code website đang chạy ('' nếu website chưa báo)."""
    store.init()
    with store.connect() as c:
        row = c.execute("SELECT version FROM agents WHERE username = ?", (SITE_ROW,)).fetchone()
    return (row["version"] or "") if row else ""


def append_log(job_id: int, text: str) -> None:
    if text:
        with store.connect() as c:
            c.execute("UPDATE jobs SET log = log || ? WHERE id = ?", (text, job_id))


def finish(job_id: int, result: dict) -> None:
    """Agent ghi kết quả; mọi đường dẫn file (vd file tải từ MyTool) được chép lên job_files."""
    with store.connect() as c:
        def pack(value):
            if isinstance(value, dict):
                return {k: pack(v) for k, v in value.items()}
            if isinstance(value, list):
                return [pack(v) for v in value]
            if isinstance(value, str) and len(value) < 500 and Path(value).is_absolute() and Path(value).is_file():
                p = Path(value)
                fid = c.execute("INSERT INTO job_files(job_id, name, content) VALUES (?,?,?) RETURNING id",
                                (job_id, p.name, p.read_bytes())).fetchone()["id"]
                return f"{FILE_PREFIX}{fid}/{p.name}"
            return value

        packed = pack(result)
        c.execute(f"UPDATE jobs SET status = ?, result = ?, finished_at = {db.now_sql()} WHERE id = ? AND status = 'running'",
                  ("done" if result.get("ok") else "error", json.dumps(packed, ensure_ascii=False, default=str), job_id))


# ---- website ----------------------------------------------------------------------
def enqueue(job: str, payload: dict, username: str) -> int:
    store.init()
    with store.connect() as c:
        old = db.now_sql(KEEP_DAYS * 86400)
        c.execute(f"DELETE FROM job_files WHERE job_id IN (SELECT id FROM jobs WHERE created_at < {old})")
        c.execute(f"DELETE FROM jobs WHERE created_at < {old}")
        return c.execute(f"INSERT INTO jobs(job, payload, requested_by, created_at) VALUES (?, ?, ?, {db.now_sql()}) RETURNING id",
                         (job, json.dumps(payload, ensure_ascii=False, default=str), username)).fetchone()["id"]


def request_show(username: str) -> int:
    """Nút "Hiện cửa sổ agent": agent của tài khoản này mở cửa sổ log trên máy của nó."""
    return enqueue(SHOW_WINDOW, {}, username)


def request_check(username: str) -> int:
    """Nút "Kiểm tra lại": agent kiểm tra máy ngay (vd vừa bật VPN) rồi báo lên trong vài giây."""
    return enqueue(CHECK_MACHINE, {}, username)


def publish_site_version(version: str) -> None:
    heartbeat(SITE_ROW, "website", version)


def get(job_id: int) -> dict | None:
    """Đọc thẳng CSDL (không qua cache) — dùng khi đang chờ agent."""
    with store.connect() as c:
        row = c.execute("SELECT id, job, requested_by, status, agent, log, created_at, started_at, finished_at FROM jobs WHERE id = ?",
                        (job_id,)).fetchone()
    return dict(row) if row else None


def cancel(job_id: int, only_queued: bool = True) -> bool:
    """Huỷ lệnh; only_queued: chỉ huỷ khi agent chưa nhận (trả về True nếu huỷ được)."""
    states = "('queued')" if only_queued else "('queued', 'running')"
    with store.connect() as c:
        row = c.execute(f"UPDATE jobs SET status = 'cancelled', finished_at = {db.now_sql()} WHERE id = ? AND status IN {states} "
                        "RETURNING id", (job_id,)).fetchone()
    return row is not None


def status(job_id: int) -> str | None:
    with store.connect() as c:
        row = c.execute("SELECT status FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return row["status"] if row else None


def result(job_id: int, dest_dir: Path) -> dict | None:
    """Kết quả của lệnh; file đính kèm tải về dest_dir và thay bằng đường dẫn trên máy này."""
    with store.connect() as c:
        row = c.execute("SELECT result FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row or not row["result"]:
            return None

        def unpack(value):
            if isinstance(value, dict):
                return {k: unpack(v) for k, v in value.items()}
            if isinstance(value, list):
                return [unpack(v) for v in value]
            if isinstance(value, str) and value.startswith(FILE_PREFIX):
                fid, _, name = value[len(FILE_PREFIX):].partition("/")
                f = c.execute("SELECT content FROM job_files WHERE id = ? AND job_id = ?", (int(fid), job_id)).fetchone()
                if f is None:
                    return value
                dest_dir.mkdir(parents=True, exist_ok=True)
                path = dest_dir / Path(name).name
                path.write_bytes(bytes(f["content"]))
                return str(path)
            return value

        return unpack(json.loads(row["result"]))
