"""Hàng đợi thao tác tự động cho website (CSDL chung).

Website không vào được NC tool / MyTool (cần VPN công ty + SSO), nên khi bấm nút trên website:
1. website ghi lệnh vào bảng jobs (requested_by = người bấm);
2. agent trên máy của chính người đó (automation/agent.py, có VPN + phiên SSO của họ) nhận lệnh,
   chạy automation.runner như bản local, đẩy log lên từng giây;
3. xong thì agent ghi kết quả (file tải về nằm ở bảng job_files) — website đọc và chạy tiếp như bản local.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from pathlib import Path

from . import config, store

HEARTBEAT_SECONDS = 10     # agent báo "còn sống" mỗi chừng này giây
ONLINE_SECONDS = 45        # quá chừng này không thấy tín hiệu -> coi như agent đã tắt
QUEUE_EXPIRE_SECONDS = 120  # lệnh chờ quá lâu thì agent bỏ qua, tránh mở NC tool lúc người bấm không còn chờ
KEEP_DAYS = 7              # xoá lệnh cũ (kèm file) sau chừng này ngày
FILE_PREFIX = "jobfile://"
FINISHED = ("done", "error", "expired", "cancelled")

_status_cache: dict[str, tuple[float, dict | None]] = {}


def _ago(seconds: float) -> str:
    return (config.now() - timedelta(seconds=seconds)).strftime("%Y-%m-%d %H:%M:%S")


def _age(ts: str | None) -> float:
    try:
        return (config.now() - datetime.strptime(ts or "", "%Y-%m-%d %H:%M:%S")).total_seconds()
    except ValueError:
        return float("inf")


# ---- agent ------------------------------------------------------------------------
def heartbeat(username: str, host: str, version: str = "") -> None:
    store.init()
    with store.connect() as c:
        c.execute("INSERT INTO agents(username, host, seen_at, version) VALUES (?,?,?,?) ON CONFLICT(username) DO UPDATE SET "
                  "host = excluded.host, seen_at = excluded.seen_at, version = excluded.version",
                  (username, host, store.now(), version))


def agent_offline(username: str) -> None:
    store.init()
    with store.connect() as c:
        c.execute("UPDATE agents SET seen_at = ? WHERE username = ?", (_ago(ONLINE_SECONDS + 1), username))
    _status_cache.pop(username, None)


def agent_status(username: str, fresh: bool = False) -> dict | None:
    """Agent của người này nếu đang chạy: {'host', 'seen_at'}; None nếu chưa bật. Nhớ 10 giây cho trang khỏi chờ CSDL."""
    hit = _status_cache.get(username)
    if hit and not fresh and time.monotonic() - hit[0] < HEARTBEAT_SECONDS:
        return hit[1]
    store.init()
    with store.connect() as c:
        row = c.execute("SELECT host, seen_at FROM agents WHERE username = ?", (username,)).fetchone()
    value = {"host": row["host"], "seen_at": row["seen_at"]} if row and _age(row["seen_at"]) <= ONLINE_SECONDS else None
    _status_cache[username] = (time.monotonic(), value)
    return value


def claim(username: str, host: str) -> dict | None:
    """Agent nhận lệnh cũ nhất đang chờ của người này (hai agent cùng tài khoản cũng chỉ một bên nhận được)."""
    store.init()
    with store.connect() as c:
        c.execute("UPDATE jobs SET status = 'expired', finished_at = ? WHERE requested_by = ? AND status = 'queued' AND created_at < ?",
                  (store.now(), username, _ago(QUEUE_EXPIRE_SECONDS)))
        row = c.execute(
            "UPDATE jobs SET status = 'running', agent = ?, started_at = ? WHERE id = (SELECT id FROM jobs WHERE requested_by = ? "
            "AND status = 'queued' ORDER BY id LIMIT 1) AND status = 'queued' RETURNING id, job, payload, created_at",
            (host, store.now(), username)).fetchone()
    return dict(row) if row else None


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
        c.execute("UPDATE jobs SET status = ?, result = ?, finished_at = ? WHERE id = ? AND status = 'running'",
                  ("done" if result.get("ok") else "error", json.dumps(packed, ensure_ascii=False, default=str), store.now(), job_id))


# ---- website ----------------------------------------------------------------------
def enqueue(job: str, payload: dict, username: str) -> int:
    store.init()
    with store.connect() as c:
        old = _ago(KEEP_DAYS * 86400)
        c.execute("DELETE FROM job_files WHERE job_id IN (SELECT id FROM jobs WHERE created_at < ?)", (old,))
        c.execute("DELETE FROM jobs WHERE created_at < ?", (old,))
        return c.execute("INSERT INTO jobs(job, payload, requested_by, created_at) VALUES (?,?,?,?) RETURNING id",
                         (job, json.dumps(payload, ensure_ascii=False, default=str), username, store.now())).fetchone()["id"]


def get(job_id: int) -> dict | None:
    """Đọc thẳng CSDL (không qua cache) — dùng khi đang chờ agent."""
    with store.connect() as c:
        row = c.execute("SELECT id, job, requested_by, status, agent, log, created_at, started_at, finished_at FROM jobs WHERE id = ?",
                        (job_id,)).fetchone()
    return dict(row) if row else None


def cancel(job_id: int, only_queued: bool = True) -> bool:
    """Huỷ lệnh; only_queued: chỉ huỷ khi agent chưa nhận (trả về True nếu huỷ được)."""
    with store.connect() as c:
        row = c.execute("UPDATE jobs SET status = 'cancelled', finished_at = ? WHERE id = ? AND status " +
                        ("= 'queued'" if only_queued else "IN ('queued', 'running')") + " RETURNING id",
                        (store.now(), job_id)).fetchone()
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
