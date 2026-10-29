"""Kiểm tra agent chạy ngầm trên Windows (automation/agent.py --background, automation/desktop.py).

    set L2M_TEST_DATABASE_URL=postgresql://...
    .venv\\Scripts\\python.exe tests\\test_agent_background.py

Bật một agent pythonw thật trên schema tạm của CSDL chung + thư mục dữ liệu tạm, rồi kiểm tra: báo sẵn sàng, chỉ chạy
một bản, chạy lệnh (runner giả, không mở Edge), mở cửa sổ log khi website / biểu tượng khay yêu cầu, bật/tắt tự chạy
cùng Windows (khoá registry tạm, không đụng khoá Run thật), báo có bản mới, tắt từ agent.bat --stop.
Trong lúc chạy sẽ thấy chấm tròn ở khay, một thông báo và cửa sổ log hiện lên rồi tự đóng.
"""
from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import tempfile
import time
import winreg
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

URL = os.environ.get("L2M_TEST_DATABASE_URL", "").strip()
SCHEMA = f"l2m_bg_{secrets.token_hex(4)}"
DATA = Path(tempfile.mkdtemp(prefix="l2m-agent-bg-"))
TEST_KEY = rf"Software\L2M-Ops-test\Run-{secrets.token_hex(4)}"
SCHEME = f"l2mops-agent-test-{secrets.token_hex(3)}"  # link thử, đăng ký thật trong HKCU\Software\Classes rồi xoá khi xong
USER = "bgtest"
(DATA / "local.json").write_text(json.dumps({"database_url": URL, "agent_user": USER, "site_url": "https://example.test"}),
                                 encoding="utf-8")
os.environ.pop("DATABASE_URL", None)
os.environ.update(L2M_DATA_DIR=str(DATA), L2M_DB_SCHEMA=SCHEMA, L2M_AUTOSTART_KEY=TEST_KEY, L2M_AGENT_RUNNER="tests._fake_runner",
                  L2M_PROTOCOL=SCHEME)

from automation import agent, desktop  # noqa: E402
from core import bundle, config, db, jobs, store  # noqa: E402

VIEWER_TITLE = "L2M Ops Agent — log"


def _wait(cond, timeout=30.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.3)
    return False


def _log() -> str:
    return agent.LOG_PATH.read_text(encoding="utf-8", errors="replace") if agent.LOG_PATH.exists() else ""


def _viewer() -> int:
    return desktop.FindWindowW("ConsoleWindowClass", VIEWER_TITLE) or 0


def test_background_agent_end_to_end():
    store.create_user(USER, "BG Test", "test-password-123", "member", by="test")
    jobs.publish_site_version("newer-site")  # website đã lên bản khác -> agent báo có bản mới
    token = agent.start_background()
    state = agent._wait_ready(token, 0)
    assert state.get("state") == "ready", (state, _log()[-2000:])
    assert agent.running() and state["version"] == bundle.code_version()
    assert desktop.FindWindowW(agent.tray_class(), None), "không thấy biểu tượng khay"
    assert _wait(lambda: jobs.agent_status(USER, fresh=True) is not None), "website không thấy agent"
    assert _wait(lambda: "newer-site" in _log(), 15), "agent không báo có bản mới"

    # chỉ một bản: bật thêm lần nữa thì tiến trình mới tự thoát, agent cũ vẫn chạy
    second = agent.start_background()
    time.sleep(4)
    assert agent.read_state().get("token") == token and agent.running()
    assert second != token

    # chạy lệnh từ website (runner giả chạy console ẩn), file kết quả về tới website
    jid = jobs.enqueue("files", {"game": "l2m", "word": "ngam"}, USER)
    assert _wait(lambda: jobs.get(jid)["status"] in jobs.FINISHED, 60), jobs.get(jid)
    res = jobs.result(jid, config.WORK_DIR / "dl")
    assert res["ok"] and Path(res["results"][0]["file"]).read_bytes() == b"PK fake ngam", res

    # nút "Hiện cửa sổ agent" trên website -> cửa sổ log mở trên máy agent
    assert not _viewer()
    jobs.request_show(USER)
    assert _wait(lambda: _viewer() != 0, 20), "website bấm hiện cửa sổ mà không thấy cửa sổ log"
    first = _viewer()
    # bấm biểu tượng khay khi cửa sổ đang mở: mở lại cho nổi lên trên (vẫn chỉ một cửa sổ)
    time.sleep(1.2)
    assert desktop.post_command(agent.tray_class(), agent.CMD_SHOW)
    assert _wait(lambda: _viewer() not in (0, first), 15), "biểu tượng khay không mở lại cửa sổ log"

    # menu khay: bật / tắt tự chạy cùng Windows (khoá registry tạm)
    name = agent._autostart_name(USER)
    assert desktop.autostart_get(name) is None
    assert desktop.post_command(agent.tray_class(), agent.CMD_AUTOSTART)
    assert _wait(lambda: desktop.autostart_get(name) == agent.autostart_command(), 10)
    assert "--background" in desktop.autostart_get(name) and "pythonw.exe" in desktop.autostart_get(name)
    assert desktop.post_command(agent.tray_class(), agent.CMD_AUTOSTART)
    assert _wait(lambda: desktop.autostart_get(name) is None, 10)

    # agent.bat --stop: tắt hẳn, báo website, đóng cửa sổ log và biểu tượng
    rc = subprocess.run([sys.executable, str(ROOT / "automation" / "agent.py"), "--stop"], cwd=ROOT, capture_output=True,
                        text=True, encoding="utf-8", errors="replace", timeout=60, env={**os.environ, "PYTHONUTF8": "1"})
    assert rc.returncode == 0, rc.stdout + rc.stderr
    assert not agent.running()
    assert jobs.agent_status(USER, fresh=True) is None
    assert agent.read_state().get("state") == "stopped"
    assert _wait(lambda: not _viewer(), 10), "cửa sổ log còn mở sau khi tắt agent"
    assert not desktop.FindWindowW(agent.tray_class(), None)


def _agent_bat(*args: str, **kw):
    """Như agent.bat (sau bước cài đặt): python automation\\agent.py <args>."""
    return subprocess.Popen([sys.executable, str(ROOT / "automation" / "agent.py"), *args], cwd=ROOT, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                            env={**os.environ, "PYTHONUTF8": "1", "L2M_LANG": "vi"}, **kw)


def test_agent_bat_flow():
    """agent.bat lần đầu: bật chạy ngầm + tự chạy cùng Windows rồi tự đóng; mở lại khi đang chạy: thành cửa sổ log;
    code mới giải nén đè lên: bước --stop-if-outdated tắt agent cũ."""
    assert not agent.running()
    config.save_local({k: v for k, v in config.load_local().items() if k != "autostart"})  # chưa chọn gì -> mặc định bật
    first = _agent_bat()
    out = first.communicate(timeout=180)[0]
    assert first.returncode == 0, out
    assert "Agent đang chạy ngầm. Tìm chấm tròn" in out and "Tự bật cùng Windows: bật" in out, out
    assert agent.running()
    assert desktop.autostart_get(agent._autostart_name(USER)) == agent.autostart_command()
    assert desktop.protocol_get(SCHEME) == agent.protocol_command()  # website bật được agent qua link

    viewer = _agent_bat()  # agent đã chạy, cùng bản -> cửa sổ log
    time.sleep(4)
    assert viewer.poll() is None, viewer.communicate()[0]
    state = agent.read_state()
    agent.STATE_PATH.write_text(json.dumps({**state, "version": "old-version"}), encoding="utf-8")
    rc = _agent_bat("--stop-if-outdated").communicate(timeout=60)
    assert not agent.running(), rc
    out = viewer.communicate(timeout=20)[0]
    assert viewer.returncode == 0
    assert "Đây là cửa sổ log của nó" in out and "Agent đã tắt" in out, out


def test_website_link_starts_agent():
    """Website bấm l2mops-agent://start: Windows (như trình duyệt, qua ShellExecute) bật agent chạy ngầm; agent tự kiểm tra
    máy và báo lên; …://show mở cửa sổ log."""
    assert not agent.running() and desktop.protocol_get(SCHEME)
    os.startfile(f"{SCHEME}://start")
    assert _wait(lambda: agent.read_state().get("state") == "ready" and agent.running(), 60), _log()[-1500:]
    assert _wait(lambda: "at" in ((jobs.agent_status(USER, fresh=True) or {}).get("checks") or {}), 30), "agent không báo kết quả kiểm tra"
    checks = jobs.agent_status(USER, fresh=True)["checks"]
    assert checks["protocol"] is True and checks["edge"] is True, checks
    assert checks["autostart"] is True, checks  # test trước đã bật (khoá registry tạm)
    assert not _viewer()
    os.startfile(f"{SCHEME}://show")
    assert _wait(lambda: _viewer() != 0, 20), "link …://show không mở cửa sổ log"
    assert agent.stop_running()
    assert _wait(lambda: not _viewer(), 10)


def test_viewer_plain_text():
    assert agent._plain("✅ Agent ⚠️ lỗi ▶ Lệnh #1 🟢 xong") == "[OK] Agent [!] lỗi > Lệnh #1  xong"


def _cleanup() -> None:
    import shutil

    import psycopg

    if agent.running():
        agent.stop_running()
    desktop.protocol_remove(SCHEME)
    shutil.rmtree(DATA, ignore_errors=True)  # có địa chỉ CSDL trong local.json
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, TEST_KEY)
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\L2M-Ops-test")
    except OSError:
        pass
    db.close_all()
    with psycopg.connect(db.pooled_url(URL), prepare_threshold=None, autocommit=True) as conn:
        conn.execute(f'DROP SCHEMA IF EXISTS "{SCHEMA}" CASCADE')


if __name__ == "__main__":
    if not URL:
        print("SKIP: cần L2M_TEST_DATABASE_URL (agent chạy ngầm chỉ chạy với CSDL chung)")
        sys.exit(0)
    failed = 0
    try:
        for test_name, fn in list(globals().items()):
            if test_name.startswith("test_") and callable(fn):
                t0 = time.monotonic()
                try:
                    fn()
                    print(f"PASS {test_name} ({time.monotonic() - t0:.1f}s)")
                except Exception as e:  # noqa: BLE001
                    failed += 1
                    import traceback

                    print(f"FAIL {test_name}: {type(e).__name__}: {e}")
                    traceback.print_exc()
                    print("--- agent.log ---\n" + _log()[-3000:])
    finally:
        _cleanup()
        print(f"(đã xoá schema tạm {SCHEMA} và khoá registry tạm)")
    sys.exit(1 if failed else 0)
