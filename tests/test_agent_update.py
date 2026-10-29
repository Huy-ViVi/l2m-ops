"""Agent tự cập nhật (automation/updater.py, automation/agent.py).

    .venv\\Scripts\\python.exe tests\\test_agent_update.py
    set L2M_TEST_DATABASE_URL=postgresql://...   -> chạy thêm một lượt thật: agent chạy ngầm từ một bản sao app trong thư mục
                                                    tạm; website báo bản mới; agent tự tải (máy chủ HTTP tạm đóng vai GitHub),
                                                    chép đè rồi tự bật lại bằng code mới.
Không đụng thư mục app thật: mọi lần chép đè đều vào bản sao trong thư mục tạm.
"""
from __future__ import annotations

import io
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

URL = os.environ.get("L2M_TEST_DATABASE_URL", "").strip()
SCHEMA = f"l2m_upd_{secrets.token_hex(4)}"
WORK = Path(tempfile.mkdtemp(prefix="l2m-agent-update-"))
DATA = WORK / "data"
SCHEME = f"l2mops-agent-test-{secrets.token_hex(3)}"
TEST_KEY = rf"Software\L2M-Ops-test\Run-{secrets.token_hex(4)}"
USER = "updtest"
DATA.mkdir()
os.environ.pop("DATABASE_URL", None)
os.environ.update(L2M_DATA_DIR=str(DATA), L2M_DB_SCHEMA=SCHEMA, L2M_PROTOCOL=SCHEME, L2M_AUTOSTART_KEY=TEST_KEY)

from automation import agent, updater  # noqa: E402
from core import bundle, config  # noqa: E402


def _copy_app(dest: Path) -> Path:
    for p in bundle.code_files(ROOT):
        target = dest / p.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
    return dest


def _github_zip(app: Path, top: str = "l2m-ops-0a1b2c3") -> bytes:
    """Giống zip GitHub tạo cho kho: mọi file nằm trong một thư mục gốc, có cả file không phải code."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(app.rglob("*")):
            if p.is_file():
                z.write(p, f"{top}/{p.relative_to(app).as_posix()}")
        z.writestr(f"{top}/.gitignore", "data/\n")
        z.writestr(f"{top}/tests/test_x.py", "# không phải code agent\n")
    return buf.getvalue()


class _Server:
    """Máy chủ HTTP tạm đóng vai GitHub: trả một file zip."""

    def __init__(self, payload: bytes):
        outer = self
        self.payload, self.hits = payload, 0

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                outer.hits += 1
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Length", str(len(outer.payload)))
                self.end_headers()
                self.wfile.write(outer.payload)

            def log_message(self, *args):
                pass

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}/archive/HEAD.zip"

    def close(self) -> None:
        self.srv.shutdown()


def _new_version(base: Path, dest: Path) -> str:
    """Bản "mới" = bản cũ + README đổi một dòng + một file thêm; bản cũ có một file bản mới đã bỏ."""
    shutil.copytree(base, dest)
    (dest / "README.md").write_bytes((dest / "README.md").read_bytes() + b"\nauto-update test line\n")
    (dest / "core" / "added_by_update.py").write_text("ADDED = True\n", encoding="utf-8")
    return bundle.version_of(dest)


def test_fetch_only_matching_version_and_apply():
    old = _copy_app(WORK / "unit-old")
    (old / "core" / "obsolete_module.py").write_text("OLD = True\n", encoding="utf-8")
    (old / "data").mkdir()
    (old / "data" / "local.json").write_text('{"agent_user": "x"}', encoding="utf-8")
    (old / ".venv").mkdir()
    (old / ".venv" / "marker").write_text("keep", encoding="utf-8")
    target = _new_version(_copy_app(WORK / "unit-base"), WORK / "unit-new")
    assert bundle.version_of(old) != target
    srv = _Server(_github_zip(WORK / "unit-new"))
    try:
        assert updater.fetch("000000000000", srv.url) is None, "GitHub chưa có đúng bản website thì không dùng"
        root = updater.fetch(target, srv.url)
        assert root and bundle.version_of(root) == target
    finally:
        srv.close()
    updater.apply(root, old)
    assert bundle.version_of(old) == target, "chép xong phải đúng bản website"
    assert b"auto-update test line" in (old / "README.md").read_bytes()
    assert (old / "core" / "added_by_update.py").is_file() and not (old / "core" / "obsolete_module.py").exists()
    assert (old / "data" / "local.json").read_text(encoding="utf-8") == '{"agent_user": "x"}', "không đụng data/"
    assert (old / ".venv" / "marker").is_file() and not (old / "tests").exists(), "chỉ chép file code của agent"
    assert not list(old.rglob("*.update")), "còn file tạm"


def test_zip_with_bad_paths_is_rejected():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("l2m-ops-x/app.py", "")
        z.writestr("../evil.txt", "x")
    srv = _Server(buf.getvalue())
    try:
        updater.fetch("whatever", srv.url)
        raise AssertionError("zip có đường dẫn thoát ra ngoài phải bị từ chối")
    except ValueError:
        pass
    finally:
        srv.close()
    assert not (config.DATA_DIR / "evil.txt").exists() and not (config.DATA_DIR.parent / "evil.txt").exists()


def test_relaunch_script_parses_with_odd_paths():
    """Thư mục agent có dấu cách, ngoặc, dấu nháy (vd "D:\\New folder (2)") — PowerShell vẫn đọc đúng lệnh bật lại."""
    app = Path(r"D:\New folder (2)\it's agent")
    script = updater.relaunch_script(4242, app, r"C:\Py 3\pythonw.exe", app / "automation" / "agent.py", setup=True)
    assert "Wait-Process -Id 4242" in script
    assert r"& 'D:\New folder (2)\it''s agent\tools\setup.ps1'" in script
    assert r"""-ArgumentList '-X utf8 "D:\New folder (2)\it''s agent\automation\agent.py" --background'""" in script
    path = WORK / "relaunch.ps1"
    path.write_text(script, encoding="utf-8-sig")
    check = ("$e = $null; [void][System.Management.Automation.Language.Parser]::ParseFile("
             f"'{path}', [ref]$null, [ref]$e); $e.Count")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", check], capture_output=True, text=True, timeout=60)
    assert out.stdout.strip() == "0", out.stdout + out.stderr
    assert "setup.ps1" not in updater.relaunch_script(1, app, "pythonw.exe", app / "automation" / "agent.py", setup=False)


def _wait(cond, timeout=30.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.5)
    return False


def _log() -> str:
    return agent.LOG_PATH.read_text(encoding="utf-8", errors="replace") if agent.LOG_PATH.exists() else ""


def test_background_agent_updates_itself():
    """Lượt thật: agent chạy ngầm (pythonw) từ bản sao app; website báo bản mới -> agent tải, chép đè, tự bật lại bằng code
    mới, báo website đúng bản mới — người dùng không làm gì."""
    from core import jobs, store

    app = _copy_app(WORK / "agent-app")
    target = _new_version(_copy_app(WORK / "agent-base"), WORK / "agent-new")
    config.save_local({"database_url": URL, "agent_user": USER, "auto_update": True})
    store.create_user(USER, "Update Test", "test-password-123", "member", by="test")
    jobs.publish_site_version(target)
    srv = _Server(_github_zip(WORK / "agent-new"))
    env = {**os.environ, "PYTHONUTF8": "1", "L2M_UPDATE_URL": srv.url, "L2M_AGENT_TOKEN": "upd-test"}
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    try:
        subprocess.Popen([agent._python(windowless=True), "-X", "utf8", str(app / "automation" / "agent.py"), "--background"],
                         cwd=app, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=flags)
        assert _wait(lambda: agent.read_state().get("state") == "ready" and agent.read_state().get("version") == target, 120), \
            (agent.read_state(), _log()[-3000:])
        assert srv.hits == 1
        assert bundle.version_of(app) == target and (app / "core" / "added_by_update.py").is_file()
        assert agent.read_state().get("token") == "upd-test", "agent.bat vẫn chờ được agent bật lại (cùng mã lần bật)"
        assert _wait(lambda: (jobs.agent_status(USER, fresh=True) or {}).get("version") == target, 30), "website không thấy bản mới"
        log = _log()
        assert "Đang tải bản code" in log and "Agent đã tự cập nhật lên bản" in log, log[-3000:]
    finally:
        srv.close()
        agent.stop_running()


def _cleanup() -> None:
    import winreg

    from automation import desktop

    if agent.running():
        agent.stop_running()
    desktop.protocol_remove(SCHEME)
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, TEST_KEY)
    except OSError:
        pass
    if URL:
        import psycopg

        from core import db

        db.close_all()
        with psycopg.connect(db.pooled_url(URL), prepare_threshold=None, autocommit=True) as conn:
            conn.execute(f'DROP SCHEMA IF EXISTS "{SCHEMA}" CASCADE')
    shutil.rmtree(WORK, ignore_errors=True)  # có địa chỉ CSDL trong local.json


if __name__ == "__main__":
    failed = 0
    try:
        for name, fn in list(globals().items()):
            if not (name.startswith("test_") and callable(fn)):
                continue
            if name == "test_background_agent_updates_itself" and not URL:
                print(f"SKIP {name}: cần L2M_TEST_DATABASE_URL")
                continue
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
        _cleanup()
        print(f"(đã xoá thư mục tạm, schema tạm {SCHEMA}, link thử và khoá registry tạm)")
    sys.exit(1 if failed else 0)
