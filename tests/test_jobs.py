"""Kiểm tra hàng đợi lệnh website -> agent (core/jobs.py, automation/agent.py, ui/common.run_job).

    .venv\\Scripts\\python.exe tests\\test_jobs.py
    set L2M_TEST_DATABASE_URL=postgresql://...   -> chạy thêm phần website (cần CSDL chung) trên một schema tạm
    set L2M_TEST_BROWSER=1                       -> chạy thêm một lượt thật: agent + automation.runner + Edge ẩn
                                                    trên trang NC tool giả lập (tests/test_item_lookup_mock.py)

Không có L2M_TEST_DATABASE_URL thì chạy trên SQLite trong thư mục tạm (bỏ qua phần website).
"""
from __future__ import annotations

import io
import os
import secrets
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

URL = os.environ.get("L2M_TEST_DATABASE_URL", "").strip()
SCHEMA = f"l2m_jobs_{secrets.token_hex(4)}"
os.environ["L2M_DATA_DIR"] = tempfile.mkdtemp(prefix="l2m-jobs-test-")
os.environ.pop("DATABASE_URL", None)
if URL:
    os.environ.update(DATABASE_URL=URL, L2M_DB_SCHEMA=SCHEMA)

from automation import agent  # noqa: E402
from core import config, db, jobs, store  # noqa: E402

FAKE = "tests._fake_runner"
HOST = "test-pc"


def _wait(cond, timeout=30.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.2)
    return False


def test_agent_status():
    assert jobs.agent_status("alice", fresh=True) is None
    jobs.heartbeat("alice", HOST)
    assert jobs.agent_status("alice", fresh=True)["host"] == HOST
    jobs.agent_offline("alice")
    assert jobs.agent_status("alice", fresh=True) is None


def test_round_trip_with_file():
    jid = jobs.enqueue("files", {"game": "l2m", "word": "xin-chào", "_lang": "en"}, "alice")
    assert jobs.get(jid)["status"] == "queued"
    agent.serve("alice", HOST, runner=FAKE, once=True)
    row = jobs.get(jid)
    assert row["status"] == "done" and row["agent"] == HOST, row
    assert "lang=en game=l2m" in row["log"] and "step 2 xin-chào" in row["log"], row["log"]
    res = jobs.result(jid, config.WORK_DIR / "dl" / str(jid))
    path = Path(res["results"][0]["file"])
    assert path.read_bytes() == "PK fake xin-chào".encode(), path
    assert "_lang" not in res["echo"]  # agent bỏ khoá nội bộ trước khi chạy runner


def test_only_own_jobs_and_single_claim():
    jid = jobs.enqueue("echo", {"word": "bob's"}, "bob")
    assert jobs.claim("alice", HOST) is None  # lệnh của bob không chạy trên máy alice
    first = jobs.claim("bob", "pc-1")
    assert first and first["id"] == jid
    assert jobs.claim("bob", "pc-2") is None  # đã có máy nhận
    jobs.finish(jid, {"ok": True})
    assert jobs.get(jid)["status"] == "done"


def test_failure_result():
    jid = jobs.enqueue("fail", {}, "alice")
    agent.serve("alice", HOST, runner=FAKE, once=True)
    assert jobs.get(jid)["status"] == "error"
    assert jobs.result(jid, config.WORK_DIR)["error"] == "boom"


def test_stale_job_expires():
    jid = jobs.enqueue("echo", {}, "alice")
    with store.connect() as c:
        c.execute("UPDATE jobs SET created_at = ? WHERE id = ?", ("2020-01-01 00:00:00", jid))
    assert jobs.claim("alice", HOST) is None
    assert jobs.get(jid)["status"] == "expired"


def test_cancel_running_job():
    jid = jobs.enqueue("slow", {}, "alice")
    worker = threading.Thread(target=agent.serve, args=("alice", HOST), kwargs={"runner": FAKE, "once": True})
    worker.start()
    assert _wait(lambda: jobs.get(jid)["status"] == "running")
    assert _wait(lambda: "tick 2" in jobs.get(jid)["log"])  # log đẩy lên trong lúc chạy
    assert jobs.cancel(jid, only_queued=False)
    worker.join(20)
    assert not worker.is_alive(), "agent không dừng lệnh đã huỷ"
    assert jobs.get(jid)["status"] == "cancelled"


def test_queued_cancel_only_before_pickup():
    jid = jobs.enqueue("echo", {}, "alice")
    assert jobs.cancel(jid)
    assert not jobs.cancel(jid)
    assert jobs.claim("alice", HOST) is None


def test_control_job_not_given_to_runner():
    """Nút "Hiện cửa sổ agent": vòng nhận lệnh bỏ qua, chỉ luồng heartbeat nhận (kể cả khi đang chạy lệnh dài)."""
    jid = jobs.request_show("alice")
    jobs.request_check("alice")
    assert jobs.claim("alice", HOST) is None
    assert jobs.claim_controls("alice", HOST) == {jobs.SHOW_WINDOW, jobs.CHECK_MACHINE}
    assert jobs.get(jid)["status"] == "done"
    assert not jobs.claim_controls("alice", HOST)


def test_heartbeat_opens_window_on_request():
    class FakeUI:
        shown = 0
        connected = site = None

        def show(self):
            self.shown += 1

        def set_connected(self, ok):
            self.connected = ok

        def site_version(self, version):
            self.site = version

    ui = FakeUI()
    jobs.publish_site_version("site-v1")
    beat = agent.Heartbeat("alice", HOST, ui)
    beat.start()
    try:
        jobs.request_show("alice")
        assert _wait(lambda: ui.shown == 1, 15), "agent không mở cửa sổ khi website yêu cầu"
        assert _wait(lambda: ui.site == "site-v1", 15) and ui.connected is True, (ui.site, ui.connected)
        # agent tự kiểm tra máy rồi báo lên; "Kiểm tra lại" trên website -> kiểm tra lại ngay (mốc giờ mới)
        assert _wait(lambda: "at" in jobs.agent_status("alice", fresh=True)["checks"], 20), jobs.agent_status("alice", fresh=True)
        checks = jobs.agent_status("alice", fresh=True)["checks"]
        assert {"nc_tool", "mytool", "browser", "browser_ok", "edge", "autostart", "protocol"} <= set(checks), checks
        time.sleep(1.1)
        jobs.request_check("alice")
        assert _wait(lambda: jobs.agent_status("alice", fresh=True)["checks"]["at"] != checks["at"], 20), "không kiểm tra lại"
    finally:
        beat.stop()
        beat.join(10)


def test_agent_zip_has_code_and_settings():
    import json
    import zipfile

    from core import bundle

    data = bundle.agent_zip("alice", "postgresql://u:pw@db.example/x")
    dest = Path(tempfile.mkdtemp(prefix="l2m-agent-zip-"))
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = set(z.namelist())
        z.extractall(dest)
    for need in ("agent.bat", "run.bat", "requirements.txt", "tools/setup.ps1", "automation/agent.py", "core/jobs.py", "CHAY-AGENT.txt"):
        assert need in names, need
    assert not [n for n in names if n.startswith("data/") and n != "data/local.json"], names  # không kèm dữ liệu của máy tải
    assert not [n for n in names if n.startswith(("tests/", ".streamlit/")) or "__pycache__" in n], names
    local = json.loads((dest / "data" / "local.json").read_text(encoding="utf-8"))
    assert local == {"database_url": "postgresql://u:pw@db.example/x", "agent_user": "alice", "auto_update": True}
    assert bundle.code_version(dest) == bundle.code_version(ROOT)  # website nhận ra agent tải từ nó là cùng bản


# ---- website (cần CSDL chung) --------------------------------------------------------
SCRIPT = """
import streamlit as st
from ui import common
st.session_state["res"] = common.run_job(st.session_state["job"], st.session_state["payload"], "Test job")
"""


def _website(job: str, payload: dict, username: str = "alice", timeout: int = 240):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_string(SCRIPT, default_timeout=timeout)
    at.session_state["auth_user"] = store.get_user(username)
    at.session_state["job"] = job
    at.session_state["payload"] = payload
    at.run()
    assert not at.exception, at.exception
    return at


def _website_env():
    os.environ.update(L2M_APP_MODE="team", L2M_PUBLIC="1", L2M_NO_AUTOMATION="1")
    if not store.get_user("alice"):
        store.create_user("alice", "Alice", "test-password-123", "member", by="test")
    store.clear_cache()


def test_website_without_agent_explains():
    _website_env()
    jobs.agent_offline("alice")
    at = _website("echo", {"word": "x"})
    assert at.session_state["res"] is None
    assert any("agent.bat" in e.value for e in at.error), [e.value for e in at.error]


def test_website_offers_agent_download():
    """Chưa có agent: thanh bên + trang có nút tải agent; có agent cùng bản thì ẩn nút; agent bản khác thì báo + hiện lại."""
    from streamlit.testing.v1 import AppTest

    from core import bundle

    _website_env()
    sid = store.create_session("alice")

    def page():
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
        at.session_state["auth_user"] = store.get_user("alice")
        at.session_state["sid"] = sid  # app.py kiểm tra phiên đăng nhập
        at.session_state["machine_check"] = "done"  # test này chỉ xem thanh bên, không mở hộp kiểm tra máy
        at.run()
        at.switch_page("views/payment_errors.py").run()
        assert not at.exception, at.exception
        labels = [b.proto.label for b in at.get("download_button")]
        return at, labels

    jobs.agent_offline("alice")
    at, labels = page()
    assert labels.count("⬇ Tải agent cho máy này") == 2, labels  # thanh bên + trang
    assert any("⚪" in c.value for c in at.sidebar.caption)
    jobs.heartbeat("alice", "pc-alice", bundle.code_version())
    jobs.agent_status("alice", fresh=True)
    at, labels = page()
    assert "⬇ Tải agent cho máy này" not in labels, labels
    assert any("pc-alice" in c.value for c in at.sidebar.caption)
    assert jobs.site_version() == bundle.code_version()  # website báo bản code của nó cho agent chạy ngầm
    at.button(key="agent_show").click().run()  # "Hiện cửa sổ agent" -> lệnh điều khiển cho agent của alice
    assert not at.exception, at.exception
    assert jobs.SHOW_WINDOW in jobs.claim_controls("alice", "pc-alice")
    jobs.heartbeat("alice", "pc-alice", "old-version")
    jobs.agent_status("alice", fresh=True)
    at, labels = page()
    assert labels.count("⬇ Tải agent cho máy này") == 1 and any("🟠" in c.value for c in at.sidebar.caption), labels
    jobs.agent_offline("alice")


def _after_login(username: str):
    """Trang đầu tiên sau khi đăng nhập website (app.py chạy kiểm tra máy — ui/agent_setup.py)."""
    from streamlit.testing.v1 import AppTest

    if not store.get_user(username):
        store.create_user(username, username.title(), "test-password-123", "member", by="test")
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
    at.session_state["auth_user"] = store.get_user(username)
    at.session_state["sid"] = store.create_session(username)
    at.run()
    assert not at.exception, at.exception
    return at


def _texts(at) -> str:
    return "\n".join(e.value for kind in ("markdown", "caption", "info", "warning", "success", "toast") for e in at.get(kind))


GOOD = {"edge": True, "nc_tool": True, "mytool": True, "autostart": True, "protocol": True, "at": "2026-10-28 09:00:00"}


def test_website_check_machine_ready():
    """Agent đang chạy, máy ổn -> báo đủ điều kiện, không mở hộp thoại."""
    from core import bundle

    _website_env()
    jobs.heartbeat("ready1", "pc-ready", bundle.code_version(), GOOD)
    at = _after_login("ready1")
    toasts = [e.value for e in at.get("toast")]
    assert any("pc-ready" in v and "đủ điều kiện" in v for v in toasts), toasts
    assert not at.get("dialog")
    at.run()  # lượt sau (bấm gì đó trên trang): không báo lại
    assert not at.get("toast")
    at.button(key="machine_recheck").click().run()  # "Kiểm tra máy" ở thanh bên -> kiểm tra lại
    assert any("đủ điều kiện" in e.value for e in at.get("toast"))
    jobs.agent_offline("ready1")


def _dialog_title(at) -> str:
    return at.get("dialog")[0].proto.dialog.title


def test_website_check_machine_needs_vpn():
    """Agent chạy nhưng không vào được NC tool -> hộp hướng dẫn bật VPN. Hộp không mất khi cả trang chạy lại; bấm "Kiểm tra
    lại" thì dòng chờ hiện ngay, lệnh tới agent, agent trả lời thì hộp ghi rõ lúc kiểm tra (kể cả khi máy vẫn còn thiếu);
    agent tự thấy NC tool (vừa bật VPN) thì hộp tự chuyển sang đủ điều kiện, cả tiêu đề, không cần bấm."""
    from core import bundle
    from ui import agent_setup

    _website_env()
    jobs.heartbeat("vpn1", "pc-vpn", bundle.code_version(), {**GOOD, "nc_tool": False})
    at = _after_login("vpn1")
    assert at.get("dialog"), "không mở hộp hướng dẫn"
    assert "Chưa vào được NC tool" in _texts(at) and "Bật VPN công ty trên máy pc-vpn" in _texts(at), _texts(at)
    assert "tự thử lại mỗi 10 giây" in _texts(at) and _dialog_title(at) == "Máy pc-vpn cần thêm vài bước"
    at.run()  # cả trang chạy lại (vd bật VPN làm mất kết nối rồi nối lại): hộp vẫn mở
    assert at.get("dialog") and "Chưa vào được NC tool" in _texts(at)

    at.button(key="fix_recheck").click().run()
    assert not at.exception, at.exception
    assert "Đã gửi yêu cầu kiểm tra lúc" in _texts(at), _texts(at)  # dòng chờ hiện ngay ở lượt bấm
    assert at.button(key="fix_recheck").disabled
    assert jobs.CHECK_MACHINE in jobs.claim_controls("vpn1", "pc-vpn")  # website nhờ agent kiểm tra lại ngay
    jobs.heartbeat("vpn1", "pc-vpn", bundle.code_version(), {**GOOD, "nc_tool": False, "at": "2026-10-28 09:03:00"})
    at.run()  # _watch (2 giây/lần) thấy agent trả lời: VPN vẫn chưa vào được
    assert "Agent vừa kiểm tra lại máy pc-vpn lúc 09:03:00" in _texts(at), _texts(at)
    assert "Đã gửi yêu cầu" not in _texts(at) and not at.button(key="fix_recheck").disabled
    assert at.get("dialog") and "Chưa vào được NC tool" in _texts(at)

    at.button(key="fix_recheck").click().run()  # agent không trả lời -> quá giờ chờ thì báo
    pending = at.session_state[agent_setup.PENDING]
    at.session_state[agent_setup.PENDING] = {**pending, "until": 0}
    at.run()
    assert "chưa trả lời sau 20 giây" in _texts(at), _texts(at)

    jobs.heartbeat("vpn1", "pc-vpn", bundle.code_version(), {**GOOD, "at": "2026-10-28 09:05:00"})  # agent tự thấy NC tool
    at.run()  # không bấm gì: _watch thấy máy đổi trạng thái -> vẽ lại hộp
    assert "đủ điều kiện" in _texts(at) and "Microsoft Edge" in _texts(at), _texts(at)
    assert _dialog_title(at) == "Máy pc-vpn đã đủ điều kiện"
    at.button(key="fix_close").click().run()
    assert not at.get("dialog")
    at.run()
    assert not at.get("dialog"), "đóng rồi mà hộp mở lại"
    jobs.agent_offline("vpn1")


def test_website_check_machine_old_agent_offline():
    """Agent bản cũ (chưa đăng ký link l2mops-agent://) đang tắt -> không thử bật, mở ngay hướng dẫn tải bản mới."""
    _website_env()
    jobs.heartbeat("old1", "pc-old", "old-version")
    jobs.agent_offline("old1")
    at = _after_login("old1")
    assert at.session_state["machine_check"] == "setup" and at.get("dialog")
    assert "Agent trên máy **pc-old** là bản cũ" in _texts(at), _texts(at)
    assert not any(f"{jobs.PROTOCOL}://" in h.proto.body for h in at.get("html")), "agent bản cũ không có link để bật"


def test_website_check_machine_new_user():
    """Chưa từng cài agent -> hộp hướng dẫn cài đặt: 7 hình + nút tải zip + nút bật agent; cài xong bấm Kiểm tra lại."""
    from core import bundle

    _website_env()
    at = _after_login("new1")
    assert at.get("dialog"), "không mở hộp hướng dẫn"
    assert len(at.get("image")) == 7, len(at.get("image"))
    assert [b.proto.label for b in at.get("download_button")].count("⬇ Tải agent cho máy này") == 2  # thanh bên + hộp hướng dẫn
    assert any(f"{jobs.PROTOCOL}://start" in h.proto.body for h in at.get("html")), "thiếu nút bật agent"
    assert "Cài một lần" in _texts(at)
    at.button(key="setup_recheck").click().run()
    assert not at.exception, at.exception
    assert "Đã gửi yêu cầu kiểm tra lúc" in _texts(at), _texts(at)
    jobs.heartbeat("new1", "pc-new", bundle.code_version(), GOOD)  # agent.bat vừa chạy xong
    at.run()
    assert "Đã thấy agent trên máy **pc-new**" in _texts(at), _texts(at)
    jobs.agent_offline("new1")


def test_website_own_browser():
    """Mỗi người tự chọn trình duyệt ở thanh bên: lưu theo tài khoản, agent kiểm tra lại máy với trình duyệt đó; máy chưa
    có thì hộp hướng dẫn chỉ đúng trình duyệt + link tải. Lệnh gửi agent mang theo lựa chọn này."""
    from core import bundle

    _website_env()
    assert config.browser_channel(config.load_settings()) == "msedge"
    jobs.heartbeat("br1", "pc-br", bundle.code_version(), {**GOOD, "browser": "msedge", "browser_ok": True})
    at = _after_login("br1")
    assert not at.get("dialog")
    box = at.selectbox(key="own_browser")
    assert box.value == "" and "Theo team (Microsoft Edge)" in box.options, box.options
    box.set_value("chrome").run()
    assert not at.exception, at.exception
    assert store.user_browser("br1") == "chrome" and at.session_state["auth_user"]["browser"] == "chrome"
    assert jobs.CHECK_MACHINE in jobs.claim_controls("br1", "pc-br")  # agent kiểm tra lại với trình duyệt mới
    assert "Agent đang kiểm tra Google Chrome trên máy pc-br" in _texts(at), _texts(at)
    jobs.heartbeat("br1", "pc-br", bundle.code_version(), {**GOOD, "browser": "chrome", "browser_ok": False})
    at.run()
    assert at.get("dialog") and "Máy pc-br chưa có Google Chrome" in _texts(at), _texts(at)
    assert [b.proto.url for b in at.get("link_button")] == ["https://www.google.com/chrome/"]
    jobs.heartbeat("br1", "pc-br", bundle.code_version(), {**GOOD, "browser": "chrome", "browser_ok": True})
    at.run()  # cài Chrome xong: hộp tự chuyển
    assert "có Google Chrome" in _texts(at), _texts(at)
    assert config.browser_channel(config.load_settings(), store.user_browser("br1")) == "chrome"
    at.selectbox(key="own_browser").set_value("").run()  # chọn hẳn "Theo team"
    assert store.user_browser("br1") == config.TEAM_BROWSER
    assert config.browser_channel(config.load_settings(), store.user_browser("br1")) == "msedge"
    jobs.agent_offline("br1")


def test_browser_from_user_agent():
    from ui import auth

    win = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    assert auth.channel_from_user_agent(win + "Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0") == "msedge"
    assert auth.channel_from_user_agent(win + "Chrome/141.0.0.0 Safari/537.36") == "chrome"
    assert auth.channel_from_user_agent(win + "coc_coc_browser/141.0.0 Chrome/135.0.0.0 Safari/537.36") == ""  # Cốc Cốc
    assert auth.channel_from_user_agent(win + "Chrome/140.0.0.0 Safari/537.36 OPR/124.0.0.0") == ""  # Opera
    assert auth.channel_from_user_agent(win + "Chrome/138.0.0.0 Electron/37.0.0 Safari/537.36") == ""  # ứng dụng Electron
    assert auth.channel_from_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0") == ""
    assert auth.channel_from_user_agent("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                                        "Chrome/141.0.0.0 Safari/537.36") == ""  # agent chỉ chạy trên Windows


def test_website_browser_defaults_to_one_in_use():
    """Chưa chọn trình duyệt lần nào -> lấy luôn trình duyệt đang mở website, agent kiểm tra lại máy với trình duyệt đó.
    Đã chọn (kể cả "Theo team") thì không tự đổi nữa."""
    from core import bundle
    from ui import auth

    _website_env()
    jobs.heartbeat("br2", "pc-br2", bundle.code_version(), {**GOOD, "browser": "msedge", "browser_ok": True})
    original = auth.browser_in_use
    auth.browser_in_use = lambda: "chrome"  # vd myly mở website bằng Chrome
    try:
        at = _after_login("br2")
        assert store.user_browser("br2") == "chrome" and at.selectbox(key="own_browser").value == "chrome"
        assert jobs.CHECK_MACHINE in jobs.claim_controls("br2", "pc-br2")
        assert at.session_state["machine_check"] == "browser"  # chờ agent kiểm tra Chrome rồi mới báo
        store.set_browser("br2", config.TEAM_BROWSER)
        at = _after_login("br2")
        assert store.user_browser("br2") == config.TEAM_BROWSER, "đã chọn Theo team thì không tự đổi"
    finally:
        auth.browser_in_use = original
        jobs.agent_offline("br2")


def test_website_check_machine_starts_installed_agent():
    """Đã cài agent nhưng đang tắt -> website bấm l2mops-agent://start rồi chờ; agent báo về -> báo đủ điều kiện."""
    from core import bundle

    _website_env()
    jobs.heartbeat("known1", "pc-known", bundle.code_version(), GOOD)
    jobs.agent_offline("known1")
    at = _after_login("known1")
    assert at.session_state["machine_check"] == "starting"
    assert any(f"{jobs.PROTOCOL}://start" in h.proto.body and "<script" in h.proto.body for h in at.get("html"))
    assert "Đang bật agent trên máy bạn" in _texts(at)
    assert sum(f"{jobs.PROTOCOL}://start" in h.proto.body for h in at.get("html")) == 2  # tự bấm + nút để người dùng bấm
    assert not at.get("dialog")
    jobs.heartbeat("known1", "pc-known", bundle.code_version(), GOOD)  # trình duyệt đã mở agent, agent báo về
    at.run()
    assert at.session_state["machine_check"] == "done"
    assert any("pc-known" in e.value and "đủ điều kiện" in e.value for e in at.get("toast")), _texts(at)
    jobs.agent_offline("known1")


def test_website_runs_via_agent():
    _website_env()
    stop = threading.Event()
    worker = threading.Thread(target=agent.serve, args=("alice", HOST), kwargs={"runner": FAKE, "stop": stop}, daemon=True)
    worker.start()
    try:
        assert _wait(lambda: jobs.agent_status("alice", fresh=True) is not None)
        at = _website("files", {"word": "web"})
        res = at.session_state["res"]
        assert res and res["ok"], res
        assert Path(res["results"][0]["file"]).read_bytes() == b"PK fake web"
        assert any("test-pc" in c.value for c in at.caption), [c.value for c in at.caption]
        from core import bundle

        assert jobs.agent_status("alice", fresh=True)["version"] == bundle.code_version()  # agent báo bản code của nó
    finally:
        stop.set()
        worker.join(15)


def test_website_real_runner_mock_nc_tool():
    """Lượt thật: website -> agent -> automation.runner -> Edge ẩn -> trang Item lookup giả lập."""
    from http.server import ThreadingHTTPServer

    from tests.test_item_lookup_mock import Handler

    _website_env()
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    settings = config.load_settings()
    settings["automation"]["nc_base_url"] = f"http://127.0.0.1:{srv.server_address[1]}"
    config.save_settings(settings, by="test")
    os.environ["L2M_HEADLESS"] = "1"
    stop = threading.Event()
    worker = threading.Thread(target=agent.serve, args=("alice", HOST), kwargs={"stop": stop}, daemon=True)
    worker.start()
    try:
        name = "Pa'agrio's Seal Chest (Bound)"
        at = _website("nc_item_lookup", {"names": [name]})
        res = at.session_state["res"]
        assert res and res["ok"], res
        from core import nc_setup

        assert nc_setup.lookup_candidates(res["results"][name]["rows"]) == [{"item_id": 195, "name": name}], res
    finally:
        stop.set()
        worker.join(15)
        srv.shutdown()
        os.environ.pop("L2M_HEADLESS", None)


def _drop() -> None:
    import psycopg

    db.close_all()
    with psycopg.connect(db.pooled_url(URL), prepare_threshold=None, autocommit=True) as conn:
        conn.execute(f'DROP SCHEMA IF EXISTS "{SCHEMA}" CASCADE')


if __name__ == "__main__":
    print("DB:", "postgres (schema tạm)" if URL else "sqlite (thư mục tạm)")
    failed = 0
    try:
        for name, fn in list(globals().items()):
            if not (name.startswith("test_") and callable(fn)):
                continue
            if name.startswith("test_website") and not URL:
                print(f"SKIP {name}: cần L2M_TEST_DATABASE_URL")
                continue
            if name == "test_website_real_runner_mock_nc_tool" and os.environ.get("L2M_TEST_BROWSER") != "1":
                print(f"SKIP {name}: đặt L2M_TEST_BROWSER=1 để chạy (mở Edge ẩn)")
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
        if URL:
            _drop()
            print(f"(đã xoá schema tạm {SCHEMA})")
        else:
            db.close_all()
    sys.exit(1 if failed else 0)
