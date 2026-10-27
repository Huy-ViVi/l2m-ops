"""Agent: chạy trên máy bạn các thao tác NC tool / MyTool mà bạn bấm trên website.

    agent.bat      (hoặc: .venv\\Scripts\\python.exe -m automation.agent [--logout])

Website không vào được NC tool / MyTool (cần VPN công ty + SSO). Agent dùng VPN, Edge và phiên SSO trên máy này:
nhận lệnh của chính tài khoản bạn từ CSDL chung, chạy automation.runner như bản local, đẩy log + kết quả lên CSDL.
Cần: máy đã nối CSDL chung (trang Cài đặt của bản local). Giữ cửa sổ mở trong lúc dùng website.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import queue
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import config, db, jobs, store  # noqa: E402
from core.i18n import t  # noqa: E402

RUNNER = "automation.runner"
VERSION = "1"
POLL_SECONDS = 2
FLUSH_SECONDS = 1
CANCEL_CHECK_SECONDS = 3


def say(text: str) -> None:
    print(f"[{config.now():%H:%M:%S}] {text}", flush=True)


def _short(e: Exception) -> str:
    text = str(e).strip().splitlines()
    return text[0][:200] if text else type(e).__name__


def login(ask=input, ask_password=getpass.getpass) -> str:
    """Tài khoản L2M Ops của người ngồi máy này: hỏi một lần, nhớ trong data/local.json."""
    saved = config.load_local().get("agent_user")
    user = store.get_user(saved) if saved else None
    if user and user["active"] and user["role"] in ("member", "admin"):
        return user["username"]
    say(t("Đăng nhập một lần bằng tài khoản L2M Ops của bạn — lệnh bạn bấm trên website sẽ chạy trên máy này."))
    for _ in range(3):
        user = store.authenticate(ask("Username: ").strip(), ask_password(t("Mật khẩu: ")))
        if not user:
            say(t("Sai username hoặc mật khẩu."))
        elif user["role"] not in ("member", "admin"):
            say(t("Quyền Chỉ xem không chạy được thao tác tự động."))
        else:
            config.save_local({**config.load_local(), "agent_user": user["username"]})
            return user["username"]
    raise SystemExit(1)


class Heartbeat(threading.Thread):
    """Báo cho website biết agent còn chạy (kể cả khi đang chạy một lệnh dài)."""

    def __init__(self, username: str, host: str):
        super().__init__(daemon=True)
        self.username, self.host = username, host
        self.stopped = threading.Event()
        self.connected = True

    def run(self) -> None:
        while not self.stopped.is_set():
            try:
                jobs.heartbeat(self.username, self.host, VERSION)
                if not self.connected:
                    say(t("✓ Đã kết nối lại CSDL chung."))
                self.connected = True
            except Exception as e:  # noqa: BLE001 — mất mạng tạm thời: thử lại ở nhịp sau
                if self.connected:
                    say(t("⚠ Mất kết nối CSDL chung: {error} — đang thử lại…", error=_short(e)))
                self.connected = False
            self.stopped.wait(jobs.HEARTBEAT_SECONDS)


def run_job(row: dict, runner: str = RUNNER) -> dict:
    """Chạy một lệnh bằng automation.runner (như bản local), đẩy log lên CSDL mỗi giây."""
    jid, job = row["id"], row["job"]
    payload = json.loads(row["payload"])
    lang = payload.pop("_lang", None)
    work = config.WORK_DIR / "agent"
    work.mkdir(parents=True, exist_ok=True)
    inp, out = work / f"{job}-{jid}-in.json", work / f"{job}-{jid}-out.json"
    out.unlink(missing_ok=True)
    inp.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8")
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1", **({"L2M_LANG": lang} if lang else {})}
    proc = subprocess.Popen([sys.executable, "-m", runner, job, "--input", str(inp), "--output", str(out)],
                            cwd=config.APP_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace", env=env)
    lines: queue.Queue[str] = queue.Queue()
    reader = threading.Thread(target=lambda: [lines.put(line) for line in proc.stdout], daemon=True)
    reader.start()
    pending: list[str] = []
    last_flush = last_cancel_check = time.monotonic()
    cancelled = False
    while True:
        try:
            pending.append(lines.get(timeout=0.2))
        except queue.Empty:
            pass
        finished = proc.poll() is not None and not reader.is_alive() and lines.empty()
        if pending and (finished or time.monotonic() - last_flush >= FLUSH_SECONDS):
            text = "".join(pending)
            pending.clear()
            print(text, end="", flush=True)
            try:
                jobs.append_log(jid, text)
            except Exception:  # noqa: BLE001 — mất mạng: log vẫn in ở cửa sổ này, kết quả gửi sau
                pass
            last_flush = time.monotonic()
        if not finished and time.monotonic() - last_cancel_check >= CANCEL_CHECK_SECONDS:
            last_cancel_check = time.monotonic()
            try:
                if jobs.status(jid) == "cancelled":
                    proc.kill()
                    cancelled = True
            except Exception:  # noqa: BLE001
                pass
        if finished:
            break
    if cancelled:
        return {"ok": False, "error": t("Lệnh đã bị huỷ trên website.")}
    if out.exists():
        return json.loads(out.read_text(encoding="utf-8"))
    return {"ok": False, "error": t("Tiến trình automation không trả kết quả — xem log phía trên.")}


def serve(username: str, host: str, runner: str = RUNNER, once: bool = False, stop: threading.Event | None = None) -> None:
    """Vòng chính: nhận lệnh của username, chạy lần lượt từng lệnh. once=True: chạy tối đa một lệnh rồi dừng (test)."""
    beat = Heartbeat(username, host)
    beat.start()
    say(t("✅ Agent đang chạy cho tài khoản {user} trên máy {host}. Giữ cửa sổ này mở trong lúc dùng website; Ctrl+C để tắt.",
          user=username, host=host))
    try:
        while not (stop and stop.is_set()):
            try:
                row = jobs.claim(username, host)
            except Exception as e:  # noqa: BLE001
                say(t("⚠ Không đọc được lệnh từ CSDL chung: {error}", error=_short(e)))
                time.sleep(5)
                continue
            if not row:
                if once:
                    return
                time.sleep(POLL_SECONDS)
                continue
            say(t("▶ Lệnh #{id}: {job}", id=row["id"], job=row["job"]))
            try:
                result = run_job(row, runner)
            except Exception as e:  # noqa: BLE001
                result = {"ok": False, "error": f"{type(e).__name__}: {_short(e)}"}
            for attempt in range(5):
                try:
                    jobs.finish(row["id"], result)
                    break
                except Exception as e:  # noqa: BLE001
                    say(t("⚠ Chưa gửi được kết quả lệnh #{id}: {error} — thử lại…", id=row["id"], error=_short(e)))
                    time.sleep(3 * (attempt + 1))
            say(t("■ Lệnh #{id}: xong", id=row["id"]) if result.get("ok")
                else t("■ Lệnh #{id}: lỗi — {error}", id=row["id"], error=str(result.get("error", ""))[:200]))
            if once:
                return
    finally:
        beat.stopped.set()
        try:
            jobs.agent_offline(username)
        except Exception:  # noqa: BLE001
            pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--logout", action="store_true", help="quên tài khoản đã lưu, đăng nhập lại")
    args = ap.parse_args()
    os.environ.setdefault("L2M_LANG", config.load_settings().get("default_lang", "vi"))
    if not db.is_remote():
        say(t("Máy này chưa nối CSDL chung. Mở bản local (run.bat) → Cài đặt → Nối máy này vào CSDL chung, rồi chạy lại agent.bat."))
        return 1
    if not config.automation_enabled():
        say(t("Thao tác tự động đang bị tắt trên máy này (L2M_NO_AUTOMATION=1)."))
        return 1
    if args.logout:
        local = config.load_local()
        local.pop("agent_user", None)
        config.save_local(local)
    host = socket.gethostname()
    try:
        username = login()
        other = jobs.agent_status(username, fresh=True)
        if other and other["host"] != host:
            say(t("⚠ Tài khoản {user} đang có agent khác chạy trên máy {host}; lệnh sẽ chạy ở máy nào nhận trước.",
                  user=username, host=other["host"]))
        serve(username, host)
    except (KeyboardInterrupt, EOFError):
        say(t("Đã tắt agent."))
    finally:
        db.close_all()
    return 0


if __name__ == "__main__":
    sys.exit(main())
