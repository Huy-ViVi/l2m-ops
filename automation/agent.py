"""Agent: chạy trên máy bạn các thao tác NC tool / MyTool mà bạn bấm trên website.

    agent.bat               bật agent chạy ngầm (chấm tròn ở khay hệ thống); agent đã chạy thì hiện cửa sổ log
    agent.bat --stop        tắt agent đang chạy ngầm
    agent.bat --logout      tắt agent, quên tài khoản đã lưu, đăng nhập lại
    agent.bat --foreground  chạy ngay trong cửa sổ này như bản cũ (không chạy ngầm, không có biểu tượng khay)

Website không vào được NC tool / MyTool (cần VPN công ty + SSO). Agent dùng VPN, Edge và phiên SSO trên máy này:
nhận lệnh của chính tài khoản bạn từ CSDL chung, chạy automation.runner như bản local, đẩy log + kết quả lên CSDL.

Chạy ngầm: tiến trình pythonw (không có cửa sổ) ghi log vào data/agent.log, trạng thái ở data/agent.json.
Cửa sổ log hiện lại được bằng: bấm biểu tượng ở khay, nút "Hiện cửa sổ agent" trên website, hoặc mở lại agent.bat.
Tự bật cùng Windows (khoá Run của người dùng — tắt ở menu chuột phải của biểu tượng).
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import queue
import secrets
import signal
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if sys.path and sys.path[0] and Path(sys.path[0]).resolve() == ROOT / "automation":
    sys.path[0] = str(ROOT)  # chạy bằng đường dẫn file (khởi động cùng Windows): import như -m automation.agent
else:
    sys.path.insert(0, str(ROOT))

from core import bundle, config, db, jobs, store  # noqa: E402
from core.i18n import t  # noqa: E402

RUNNER = os.environ.get("L2M_AGENT_RUNNER") or "automation.runner"  # test: tests._fake_runner
POLL_SECONDS = 2
FLUSH_SECONDS = 1
CANCEL_CHECK_SECONDS = 3
CONTROL_SECONDS = 2        # nhịp kiểm tra lệnh điều khiển từ website (vd hiện cửa sổ)
SITE_CHECK_SECONDS = 60    # nhịp xem website có bản code mới không
MACHINE_CHECK_SECONDS = 60  # nhịp tự kiểm tra máy (trình duyệt, VPN, …) báo lên website
UNREACHABLE_CHECK_SECONDS = 10  # chưa vào được NC tool: thử lại dày hơn để vừa bật VPN là website thấy ngay
REACH_TIMEOUT = 3
LOG_MAX_BYTES = 2_000_000
READY_TIMEOUT = 120
CLOSE_AFTER_SECONDS = 10
CMD_SHOW, CMD_SITE, CMD_AUTOSTART, CMD_QUIT, CMD_QUIT_NOW = 1001, 1002, 1003, 1004, 1005

AGENT_PY = Path(__file__).resolve()
LOG_PATH = config.DATA_DIR / "agent.log"
STATE_PATH = config.DATA_DIR / "agent.json"
_hidden = False  # đang chạy ngầm: tiến trình con không được mở cửa sổ console


def say(text: str) -> None:
    print(f"[{config.now():%H:%M:%S}] {text}", flush=True)


def _short(e: Exception) -> str:
    text = str(e).strip().splitlines()
    return text[0][:200] if text else type(e).__name__


def _python(windowless: bool = False) -> str:
    """python.exe / pythonw.exe cùng thư mục với trình đang chạy (.venv\\Scripts)."""
    exe = Path(sys.executable)
    want = exe.with_name("pythonw.exe" if windowless else "python.exe")
    return str(want if want.exists() else exe)


# ---- một agent cho mỗi thư mục dữ liệu ----------------------------------------------------
def _instance_id() -> str:
    return hashlib.sha1(str(config.DATA_DIR.resolve()).lower().encode("utf-8")).hexdigest()[:12]


def mutex_name() -> str:
    return f"Local\\L2MOpsAgent-{_instance_id()}"


def tray_class() -> str:
    return f"L2MOpsAgentTray-{_instance_id()}"


def read_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


_state: dict = {}


def _set_state(**fields) -> None:
    _state.update(fields)
    try:
        STATE_PATH.write_text(json.dumps(_state, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def running() -> bool:
    from automation import desktop

    return desktop.instance_running(mutex_name())


def stop_running(timeout: float = 30) -> bool:
    """Tắt agent đang chạy ngầm (đợi nó báo website là đã tắt). True nếu đã tắt."""
    from automation import desktop

    if not running():
        return True
    if not desktop.post_command(tray_class(), CMD_QUIT_NOW):
        _kill(read_state().get("pid"))
    end = time.monotonic() + timeout
    while running() and time.monotonic() < end:
        time.sleep(0.3)
    if running():
        _kill(read_state().get("pid"))
        time.sleep(1)
    return not running()


def _kill(pid) -> None:
    if pid:
        try:
            os.kill(int(pid), signal.SIGTERM)  # Windows: TerminateProcess
        except OSError:
            pass


# ---- tự bật cùng Windows --------------------------------------------------------------
def _autostart_name(username: str) -> str:
    return f"L2M Ops Agent ({username})"


def autostart_command() -> str:
    return f'"{_python(windowless=True)}" -X utf8 "{AGENT_PY}" --background'  # lúc mở máy không có PYTHONUTF8 của agent.bat


def autostart_on(username: str) -> bool:
    from automation import desktop

    return bool(desktop.autostart_get(_autostart_name(username)))


def set_autostart(username: str, on: bool) -> None:
    from automation import desktop

    desktop.autostart_set(_autostart_name(username), autostart_command() if on else None)
    config.save_local({**config.load_local(), "autostart": on})


# ---- link l2mops-agent:// : website bật agent trên máy này -----------------------------------
def protocol_scheme() -> str:
    return os.environ.get("L2M_PROTOCOL") or jobs.PROTOCOL  # test dùng tên riêng, không đè bản thật


def protocol_command() -> str:
    return f'"{_python(windowless=True)}" -X utf8 "{AGENT_PY}" --url "%1"'


def protocol_ok() -> bool:
    from automation import desktop

    return desktop.protocol_get(protocol_scheme()) == protocol_command()


def ensure_protocol() -> None:
    """Đăng ký (hoặc trỏ lại về thư mục này) link l2mops-agent:// — trình duyệt sẽ hỏi một lần trước khi mở."""
    from automation import desktop

    if not protocol_ok():
        desktop.protocol_set(protocol_scheme(), protocol_command(), "L2M Ops Agent")


def open_url(url: str) -> int:
    """Website bấm l2mops-agent://start (bật agent) hoặc l2mops-agent://show (hiện cửa sổ log).
    Tiến trình này là pythonw: agent chưa chạy thì nó trở thành agent chạy ngầm."""
    from automation import desktop

    action = url.split(":", 1)[-1].strip("/").split("/")[0].split("?")[0].lower()
    if running():
        if action == "show":
            desktop.post_command(tray_class(), CMD_SHOW)
        return 0
    return background(show=action == "show", announce=True)


# ---- tự kiểm tra máy -----------------------------------------------------------------
def _reachable(url: str) -> bool | None:
    """Mở được kết nối tới máy chủ của url không (NC tool / MyTool chỉ vào được qua VPN công ty). None: chưa cấu hình."""
    from urllib.parse import urlsplit

    parts = urlsplit(url or "")
    if not parts.hostname:
        return None
    try:
        with socket.create_connection((parts.hostname, parts.port or (80 if parts.scheme == "http" else 443)), REACH_TIMEOUT):
            return True
    except OSError:
        return False


def machine_checks(username: str) -> dict:
    """Kết quả agent tự kiểm tra máy, báo lên website (bảng agents, cột checks) để website báo máy đủ điều kiện chưa."""
    settings = config.load_settings()
    mytool = next((u for g in settings.get("games", {}).values() for u in (g.get("mytool_search_order") or {}).values() if u), "")
    checks = {"nc_tool": _reachable(settings["automation"].get("nc_base_url", "")), "mytool": _reachable(mytool)}
    if os.name == "nt":
        from automation import desktop

        channel = config.browser_channel(settings, store.user_browser(username))
        checks.update(browser=channel, browser_ok=desktop.browser_installed(channel), edge=desktop.edge_installed(),
                      autostart=autostart_on(username), protocol=protocol_ok())
    return checks


# ---- đăng nhập ----------------------------------------------------------------------
class NeedLogin(Exception):
    """Chạy ngầm mà cần hỏi người dùng (chưa nối CSDL / chưa đăng nhập): phải mở agent.bat."""


def _no_prompt(*_args) -> str:
    raise NeedLogin


def connect_shared_db(ask=getpass.getpass) -> bool:
    """Máy mới chưa nối CSDL chung: hỏi địa chỉ ngay ở cửa sổ agent (như trang Cài đặt của bản local), lưu data/local.json."""
    say(t("Máy này chưa nối CSDL chung. Dán địa chỉ CSDL admin gửi cho bạn (postgresql://…) rồi bấm Enter "
          "— ký tự không hiện ra khi dán, đó là bình thường."))
    for _ in range(3):
        url = ask("> ").strip().strip('"')
        ok, message = db.test_connection(url)
        say(message)
        if ok:
            config.save_local({**config.load_local(), "database_url": url})
            return True
    return False


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


# ---- vòng nhận lệnh ------------------------------------------------------------------
class Heartbeat(threading.Thread):
    """Báo cho website biết agent còn chạy (kể cả khi đang chạy một lệnh dài), nhận lệnh điều khiển từ website."""

    def __init__(self, username: str, host: str, ui: "AgentTray | None" = None):
        super().__init__(daemon=True)
        self.username, self.host, self.ui = username, host, ui
        self.stopped = threading.Event()
        self.connected = True
        self.checks: dict = {}
        self.next_beat = 0.0
        self.recheck = threading.Event()

    def _check_loop(self) -> None:
        """Tự kiểm tra máy ở luồng riêng (thử kết nối NC tool / MyTool mất vài giây), xong thì báo ngay.
        Website bấm "Kiểm tra lại" -> kiểm tra ngay thay vì chờ hết phút; chưa vào được NC tool thì thử lại mỗi
        UNREACHABLE_CHECK_SECONDS (vừa bật VPN là website tự đổi sang "đủ điều kiện"). NC tool đổi trạng thái thì ghi log."""
        reach = None
        while not self.stopped.is_set():
            try:
                checks = machine_checks(self.username)
                self.checks = {**checks, "at": f"{config.now():%Y-%m-%d %H:%M:%S}"}
                self.next_beat = 0.0
                if checks.get("nc_tool") is not None and checks["nc_tool"] != reach:
                    reach = checks["nc_tool"]
                    say(t("✓ Vào được NC tool.") if reach else t("⚠ Chưa vào được NC tool — bật VPN công ty."))
            except Exception:  # noqa: BLE001 — mất mạng / CSDL: lần sau thử lại
                pass
            self.recheck.wait(UNREACHABLE_CHECK_SECONDS if reach is False else MACHINE_CHECK_SECONDS)
            self.recheck.clear()

    def stop(self) -> None:
        self.stopped.set()
        self.recheck.set()

    def run(self) -> None:
        threading.Thread(target=self._check_loop, daemon=True, name="machine-checks").start()
        next_site = 0.0
        while not self.stopped.is_set():
            now = time.monotonic()
            try:
                if now >= self.next_beat:
                    self.next_beat = now + jobs.HEARTBEAT_SECONDS
                    jobs.heartbeat(self.username, self.host, bundle.code_version(), self.checks)  # website so với bản của nó
                    if not self.connected:
                        say(t("✓ Đã kết nối lại CSDL chung."))
                    self.connected = True
                    if self.ui:
                        self.ui.set_connected(True)
                controls = jobs.claim_controls(self.username, self.host)
                if jobs.CHECK_MACHINE in controls:
                    say(t("Website yêu cầu kiểm tra lại máy."))
                    self.recheck.set()
                if jobs.SHOW_WINDOW in controls:
                    if self.ui:
                        say(t("Website yêu cầu hiện cửa sổ agent."))
                        self.ui.show()
                    else:
                        say(t("Website yêu cầu hiện cửa sổ agent — cửa sổ này đang mở."))
                if self.ui and now >= next_site:
                    next_site = now + SITE_CHECK_SECONDS
                    self.ui.site_version(jobs.site_version())
            except Exception as e:  # noqa: BLE001 — mất mạng tạm thời: thử lại ở nhịp sau
                if self.connected:
                    say(t("⚠ Mất kết nối CSDL chung: {error} — đang thử lại…", error=_short(e)))
                self.connected = False
                if self.ui:
                    self.ui.set_connected(False)
            self.stopped.wait(CONTROL_SECONDS)


def run_job(row: dict, runner: str = RUNNER, stop: threading.Event | None = None) -> dict:
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
    # Chạy ngầm: runner dùng console ẩn để Playwright / Edge không bật cửa sổ đen.
    flags = subprocess.CREATE_NO_WINDOW if _hidden and os.name == "nt" else 0
    proc = subprocess.Popen([_python(), "-m", runner, job, "--input", str(inp), "--output", str(out)],
                            cwd=config.APP_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace", env=env, creationflags=flags)
    lines: queue.Queue[str] = queue.Queue()
    reader = threading.Thread(target=lambda: [lines.put(line) for line in proc.stdout], daemon=True)
    reader.start()
    pending: list[str] = []
    last_flush = last_cancel_check = time.monotonic()
    ended = ""
    try:
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
            if not finished and not ended and stop is not None and stop.is_set():
                proc.kill()
                ended = "stopped"
            if not finished and not ended and time.monotonic() - last_cancel_check >= CANCEL_CHECK_SECONDS:
                last_cancel_check = time.monotonic()
                try:
                    if jobs.status(jid) == "cancelled":
                        proc.kill()
                        ended = "cancelled"
                except Exception:  # noqa: BLE001
                    pass
            if finished:
                break
    finally:
        if proc.poll() is None:  # Ctrl+C ở chế độ --foreground: không để Edge tự chạy tiếp
            proc.kill()
    if ended == "cancelled":
        return {"ok": False, "error": t("Lệnh đã bị huỷ trên website.")}
    if ended == "stopped":
        return {"ok": False, "error": t("Agent bị tắt giữa chừng.")}
    if out.exists():
        return json.loads(out.read_text(encoding="utf-8"))
    return {"ok": False, "error": t("Tiến trình automation không trả kết quả — xem log phía trên.")}


def serve(username: str, host: str, runner: str = RUNNER, once: bool = False, stop: threading.Event | None = None,
          ui: "AgentTray | None" = None) -> None:
    """Vòng chính: nhận lệnh của username, chạy lần lượt từng lệnh. once=True: chạy tối đa một lệnh rồi dừng (test)."""
    beat = Heartbeat(username, host, ui)
    beat.start()
    if ui:
        say(t("✅ Agent đang chạy ngầm cho tài khoản {user} trên máy {host}.", user=username, host=host))
    else:
        say(t("✅ Agent đang chạy cho tài khoản {user} trên máy {host}. Giữ cửa sổ này mở trong lúc dùng website; Ctrl+C để tắt.",
              user=username, host=host))
    try:
        while not (stop and stop.is_set()):
            try:
                row = jobs.claim(username, host)
            except Exception as e:  # noqa: BLE001
                say(t("⚠ Không đọc được lệnh từ CSDL chung: {error}", error=_short(e)))
                (stop.wait if stop else time.sleep)(5)
                continue
            if not row:
                if once:
                    return
                (stop.wait if stop else time.sleep)(POLL_SECONDS)
                continue
            say(t("▶ Lệnh #{id}: {job}", id=row["id"], job=row["job"]))
            if ui:
                ui.set_busy(f"#{row['id']} {row['job']}")
            try:
                result = run_job(row, runner, stop)
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
            if ui:
                ui.set_busy("")
            if once:
                return
    finally:
        beat.stop()
        try:
            jobs.agent_offline(username)
        except Exception:  # noqa: BLE001
            pass


# ---- chạy ngầm: biểu tượng khay + cửa sổ log --------------------------------------------
class AgentTray:
    """Biểu tượng khay của agent chạy ngầm: màu theo trạng thái, menu, mở cửa sổ log."""

    def __init__(self, username: str, host: str, stop: threading.Event):
        from automation import desktop

        self.desktop = desktop
        self.username, self.host, self.stop = username, host, stop
        self.site_url = config.load_local().get("site_url", "")
        self.busy = ""
        self.connected = True
        self.update = ""
        self.viewer: subprocess.Popen | None = None
        self._last_show = 0.0
        self.tray = desktop.Tray(tray_class(), self._tip(), self._items, self._command, self.show,
                                 default_command=CMD_SHOW, log=say)

    def start(self) -> bool:
        self.tray.start()
        self.tray.ready.wait(10)
        return self.tray.shown

    def close(self) -> None:
        self.close_viewer()
        self.tray.stop()

    # -- trạng thái --
    def _status(self) -> tuple[str, str]:
        if not self.connected:
            return "warn", t("Mất kết nối CSDL chung — đang thử lại")
        if self.busy:
            return "busy", t("Đang chạy lệnh {job}", job=self.busy)
        if self.update:
            return "warn", t("Có bản agent mới trên website")
        return "idle", t("Đang chờ lệnh từ website")

    def _tip(self) -> str:
        return f"L2M Ops Agent — {self.username}\n{self._status()[1]}"

    def _refresh(self) -> None:
        self.tray.set_status(self._status()[0], self._tip())

    def set_user(self, username: str) -> None:
        self.username = username
        self._refresh()

    def set_busy(self, job: str) -> None:
        self.busy = job
        self._refresh()

    def set_connected(self, ok: bool) -> None:
        if ok != self.connected:
            self.connected = ok
            self._refresh()

    def site_version(self, version: str) -> None:
        newer = version if version and version != bundle.code_version() else ""
        if newer and newer != self.update:
            say(t("Website đã có bản code mới ({version}). Tải agent bản mới ở thanh bên trái website, giải nén đè lên thư mục "
                  "này rồi mở lại agent.bat.", version=newer))
            self.tray.notify(t("Có bản agent mới"), t("Mở website, bấm ⬇ Tải agent cho máy này ở thanh bên trái, giải nén đè lên "
                                                       "thư mục agent rồi mở lại agent.bat."))
        if newer != self.update:
            self.update = newer
            self._refresh()

    def notify(self, title: str, text: str, warning: bool = False) -> None:
        self.tray.notify(title, text, warning)

    # -- menu --
    def _items(self) -> list:
        items = [(1, t("Tài khoản {user} · máy {host}", user=self.username, host=self.host), False, False),
                 (2, self._status()[1], False, False),
                 (None, "", False, False),
                 (CMD_SHOW, t("Hiện cửa sổ agent"), False, True)]
        if self.site_url:
            items.append((CMD_SITE, t("Mở website"), False, True))
        items += [(CMD_AUTOSTART, t("Tự bật cùng Windows"), autostart_on(self.username), True),
                  (None, "", False, False),
                  (CMD_QUIT, t("Tắt agent"), False, True)]
        return items

    def _command(self, command: int) -> None:
        if command == CMD_SHOW:
            self.show()
        elif command == CMD_SITE and self.site_url:
            webbrowser.open(self.site_url)
        elif command == CMD_AUTOSTART:
            on = not autostart_on(self.username)
            set_autostart(self.username, on)
            say(t("Tự bật cùng Windows: bật.") if on else t("Tự bật cùng Windows: tắt."))
        elif command in (CMD_QUIT, CMD_QUIT_NOW):
            if command == CMD_QUIT and self.busy and not self.desktop.ask_yes_no(
                    "L2M Ops Agent", t("Agent đang chạy lệnh {job}. Tắt agent sẽ huỷ lệnh này. Vẫn tắt?", job=self.busy)):
                return
            say(t("Đang tắt agent…"))
            self.stop.set()

    # -- cửa sổ log --
    def show(self) -> None:
        """Mở cửa sổ log (đã mở thì mở lại cho nó nổi lên trên)."""
        if time.monotonic() - self._last_show < 1:  # bấm đúp vào biểu tượng: chỉ mở một lần
            return
        self._last_show = time.monotonic()
        self.close_viewer()
        env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
        self.viewer = self.desktop.open_console([_python(), str(AGENT_PY), "--log"], config.APP_ROOT, env)

    def close_viewer(self) -> None:
        if self.viewer and self.viewer.poll() is None:
            self.viewer.terminate()
            try:
                self.viewer.wait(3)
            except subprocess.TimeoutExpired:
                pass
        self.viewer = None


def _log_to_file() -> None:
    """pythonw không có console: mọi thứ in ra (log agent + log runner) ghi vào data/agent.log."""
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        if LOG_PATH.stat().st_size > LOG_MAX_BYTES:
            LOG_PATH.replace(LOG_PATH.with_name("agent.log.1"))
    except OSError:
        pass
    f = open(LOG_PATH, "a", encoding="utf-8", errors="replace", buffering=1)  # noqa: SIM115 — mở suốt đời tiến trình
    sys.stdout = sys.stderr = f


def _wait_login(ui: AgentTray, stop: threading.Event) -> str | None:
    """Chạy ngầm: dùng tài khoản đã lưu. Mất mạng (vd vừa bật máy) thì chờ; cần hỏi người dùng thì báo mở agent.bat."""
    delay, warned = 5, False
    while not stop.is_set():
        try:
            if not db.is_remote():
                raise NeedLogin
            os.environ.setdefault("L2M_LANG", config.load_settings().get("default_lang", "vi"))
            username = login(ask=_no_prompt, ask_password=_no_prompt)
            ui.set_connected(True)
            return username
        except NeedLogin:
            message = t("Agent chưa đăng nhập trên máy này — mở agent.bat để đăng nhập.")
            say(message)
            _set_state(state="error", error=message)
            ui.notify("L2M Ops Agent", message, warning=True)
            stop.wait(10)  # cho kịp đọc thông báo
            return None
        except Exception as e:  # noqa: BLE001 — chưa có mạng / CSDL tạm lỗi
            if not warned:
                say(t("⚠ Chưa kết nối được CSDL chung: {error} — đang thử lại…", error=_short(e)))
                warned = True
            ui.set_connected(False)
            stop.wait(delay)
            delay = min(delay * 2, 60)
    return None


def background(show: bool = False, announce: bool = False) -> int:
    """Agent chạy ngầm (pythonw, do agent.bat, Windows hoặc link từ website bật lên).
    show: mở cửa sổ log khi sẵn sàng. announce: hiện thông báo chỗ biểu tượng (khi người dùng vừa chủ động bật)."""
    global _hidden
    from automation import desktop

    _hidden = True
    os.chdir(config.APP_ROOT)
    _log_to_file()
    lock = desktop.SingleInstance(mutex_name())
    if not lock.acquire():
        return 0  # agent khác (cùng thư mục dữ liệu) đang chạy
    host = socket.gethostname()
    stop = threading.Event()
    _set_state(pid=os.getpid(), token=os.environ.get("L2M_AGENT_TOKEN", ""), state="starting", error="", host=host,
               version=bundle.code_version(), started_at=f"{config.now():%Y-%m-%d %H:%M:%S}")
    say(t("Đang bật agent chạy ngầm (bản {version})…", version=bundle.code_version()))
    ui = AgentTray(config.load_local().get("agent_user") or "?", host, stop)
    try:
        if not ui.start():
            say(t("⚠ Không hiện được biểu tượng ở khay hệ thống — agent vẫn chạy; mở agent.bat để xem log."))
        username = _wait_login(ui, stop)
        if not username:
            return 1
        ui.set_user(username)
        try:
            ensure_protocol()  # máy cài từ bản cũ / thư mục agent vừa chuyển chỗ: website vẫn bật được agent
        except OSError as e:
            say(t("⚠ Không đăng ký được link để website bật agent: {error}", error=_short(e)))
        _set_state(state="ready", user=username)
        if announce or os.environ.get("L2M_AGENT_TOKEN"):  # người dùng vừa bật (không phải lúc mở máy): chỉ chỗ biểu tượng
            ui.notify("L2M Ops Agent", t("Agent đang chạy ngầm. Bấm vào chấm tròn này để xem cửa sổ log; chuột phải để tắt."))
        if show:
            ui.show()
        serve(username, host, stop=stop, ui=ui)
        say(t("Đã tắt agent."))
        return 0
    except Exception as e:  # noqa: BLE001
        say(t("⚠ Agent dừng vì lỗi: {error}", error=f"{type(e).__name__}: {_short(e)}"))
        _set_state(state="error", error=_short(e))
        return 1
    finally:
        if _state.get("state") != "error":
            _set_state(state="stopped")
        ui.close()
        lock.release()
        db.close_all()


# ---- cửa sổ log (agent.bat khi agent đã chạy; biểu tượng khay) --------------------------------
PLAIN = {"✅": "[OK]", "⚠️": "[!]", "⚠": "[!]", "▶": ">", "■": "#", "✓": "+", "✗": "x", "🔐": "[SSO]", "⬇": "v", "️": ""}


def _plain(text: str) -> str:
    """Cửa sổ conhost không vẽ được emoji: đổi sang ký tự thường."""
    for k, v in PLAIN.items():
        text = text.replace(k, v)
    return "".join(ch for ch in text if ord(ch) <= 0xFFFF)


def _read_from(pos: int) -> tuple[str, int]:
    """Phần log mới từ vị trí pos (chỉ tới hết dòng cuối cùng đã ghi xong)."""
    try:
        size = LOG_PATH.stat().st_size
    except OSError:
        return "", 0
    if size < pos:  # log vừa được xoay vòng
        pos = 0
    if size == pos:
        return "", pos
    with open(LOG_PATH, "rb") as f:
        f.seek(pos)
        data = f.read()
    cut = data.rfind(b"\n") + 1
    return data[:cut].decode("utf-8", errors="replace").replace("\r\n", "\n"), pos + cut


def _tail_start(lines: int = 200) -> int:
    try:
        size = LOG_PATH.stat().st_size
        with open(LOG_PATH, "rb") as f:
            f.seek(max(0, size - 64_000))
            data = f.read()
    except OSError:
        return 0
    keep = b"\n".join(data.split(b"\n")[-lines - 1:])
    return size - len(keep)


def _title(text: str) -> None:
    if os.name == "nt":
        import ctypes

        ctypes.windll.kernel32.SetConsoleTitleW(text)


def view_log(intro: str, plain: bool = False, wait_on_exit: bool = True) -> int:
    """In log của agent chạy ngầm và theo dõi tiếp. Đóng cửa sổ không tắt agent."""
    out = _plain if plain else (lambda s: s)
    _title("L2M Ops Agent — log")
    print(out(intro), flush=True)
    print(out(t("Đóng cửa sổ này chỉ ẩn log — agent vẫn chạy ngầm. Tắt agent: chuột phải chấm tròn ở khay hệ thống → Tắt agent.")),
          flush=True)
    print("-" * 80, flush=True)
    pos = _tail_start()
    try:
        while True:
            text, pos = _read_from(pos)
            if text:
                print(out(text), end="", flush=True)
            if not running():
                text, pos = _read_from(pos)
                print(out(text) + "-" * 80, flush=True)
                print(out(t("Agent đã tắt. Mở lại agent.bat để bật lại.")), flush=True)
                if wait_on_exit:
                    input(t("Nhấn Enter để đóng."))
                return 0
            time.sleep(0.5)
    except (KeyboardInterrupt, EOFError):
        return 0


# ---- agent.bat -----------------------------------------------------------------------
def start_background() -> str:
    """Bật agent chạy ngầm, tách khỏi cửa sổ này. Trả về mã nhận diện lần bật (ghi trong data/agent.json)."""
    token = secrets.token_hex(8)
    env = {**os.environ, "PYTHONUTF8": "1", "L2M_AGENT_TOKEN": token}
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    args = [_python(windowless=True), "-X", "utf8", str(AGENT_PY), "--background"]
    try:
        subprocess.Popen(args, cwd=config.APP_ROOT, env=env, close_fds=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB)
    except OSError:  # cửa sổ đang chạy trong job không cho tách: vẫn bật được, chỉ là gắn với job đó
        subprocess.Popen(args, cwd=config.APP_ROOT, env=env, close_fds=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, creationflags=flags)
    return token


def _wait_ready(token: str, pos: int) -> dict:
    """In log trong lúc agent ngầm khởi động; trả về data/agent.json khi nó sẵn sàng hoặc báo lỗi."""
    end = time.monotonic() + READY_TIMEOUT
    state: dict = {}
    while time.monotonic() < end:
        text, pos = _read_from(pos)
        if text:
            print(text, end="", flush=True)
        state = read_state()
        if state.get("token") == token and state.get("state") in ("ready", "error", "stopped"):
            break
        time.sleep(0.3)
    text, _ = _read_from(pos)
    print(text, end="", flush=True)
    return state if state.get("token") == token else {}


def _countdown(seconds: int) -> bool:
    """Đếm ngược rồi đóng cửa sổ; True nếu người dùng nhấn phím (muốn xem tiếp log)."""
    try:
        import msvcrt
    except ImportError:
        return False
    for left in range(seconds, 0, -1):
        message = t("Cửa sổ này tự đóng sau {n} giây — nhấn phím bất kỳ để tiếp tục xem log.", n=left)
        print(f"\r{message}  ", end="", flush=True)
        for _ in range(10):
            if msvcrt.kbhit():
                msvcrt.getwch()
                print(flush=True)
                return True
            time.sleep(0.1)
    print(flush=True)
    return False


def launch(logout: bool = False) -> int:
    """agent.bat: hỏi những gì cần hỏi ngay trong cửa sổ này, rồi bật agent chạy ngầm."""
    if running():  # đang chạy mà khác bản code (vừa giải nén đè) hoặc đổi tài khoản: tắt rồi bật lại
        say(t("Đang tắt agent đang chạy để đổi tài khoản…") if logout else t("Có bản code mới — đang tắt agent cũ để cập nhật…"))
        if not stop_running():
            say(t("⚠ Không tắt được agent đang chạy. Tắt nó ở biểu tượng khay hệ thống rồi mở lại agent.bat."))
            return 1
    if logout:
        local = config.load_local()
        local.pop("agent_user", None)
        config.save_local(local)
    host = socket.gethostname()
    if not db.is_remote() and not connect_shared_db():
        return 1
    username = login()
    other = jobs.agent_status(username, fresh=True)
    if other and other["host"] != host:
        say(t("⚠ Tài khoản {user} đang có agent khác chạy trên máy {host}; lệnh sẽ chạy ở máy nào nhận trước.",
              user=username, host=other["host"]))
    elif other:  # cùng máy mà không giữ khoá chạy-một-bản: cửa sổ agent.bat kiểu cũ còn mở
        say(t("⚠ Trên máy này còn một agent khác đang chạy (cửa sổ agent.bat cũ?). Đóng cửa sổ đó để lệnh không chạy hai lần."))
    autostart = config.load_local().get("autostart", True)
    try:
        set_autostart(username, autostart)  # ghi lại đường dẫn hiện tại (thư mục agent có thể đã chuyển chỗ)
    except OSError as e:
        say(t("⚠ Không bật được tự chạy cùng Windows: {error}", error=_short(e)))
        autostart = False
    try:
        ensure_protocol()
    except OSError as e:
        say(t("⚠ Không đăng ký được link để website bật agent: {error}", error=_short(e)))
    db.close_all()
    pos = LOG_PATH.stat().st_size if LOG_PATH.exists() else 0
    state = _wait_ready(start_background(), pos)
    if state.get("state") != "ready":
        say(state.get("error") or t("Agent chạy ngầm chưa báo sẵn sàng — xem log ở data\\agent.log."))
        return 1
    print(flush=True)
    say(t("✅ Agent đang chạy ngầm. Tìm chấm tròn màu xanh ở khay hệ thống (góc phải thanh tác vụ, có thể nằm trong nút ^): "
          "bấm vào để xem lại cửa sổ log, chuột phải để tắt agent. Trên website còn có nút Hiện cửa sổ agent."))
    say(t("Tự bật cùng Windows: bật (tắt ở menu chuột phải của chấm tròn).") if autostart
        else t("Tự bật cùng Windows: tắt (bật ở menu chuột phải của chấm tròn)."))
    if _countdown(CLOSE_AFTER_SECONDS):
        return view_log(t("Agent đang chạy ngầm trên máy này. Đây là cửa sổ log của nó."))
    return 0


def foreground(logout: bool = False) -> int:
    """Chạy agent ngay trong cửa sổ này (bản cũ): đóng cửa sổ là tắt agent."""
    lock = None
    if os.name == "nt":
        from automation import desktop

        lock = desktop.SingleInstance(mutex_name())
    if lock and not lock.acquire():
        say(t("Agent đang chạy ngầm trên máy này — tắt nó trước (agent.bat --stop)."))
        return 1
    try:
        if logout:
            local = config.load_local()
            local.pop("agent_user", None)
            config.save_local(local)
        host = socket.gethostname()
        if not db.is_remote() and not connect_shared_db():
            return 1
        username = login()
        other = jobs.agent_status(username, fresh=True)
        if other and other["host"] != host:
            say(t("⚠ Tài khoản {user} đang có agent khác chạy trên máy {host}; lệnh sẽ chạy ở máy nào nhận trước.",
                  user=username, host=other["host"]))
        serve(username, host)
    except (KeyboardInterrupt, EOFError):
        say(t("Đã tắt agent."))
    finally:
        if lock:
            lock.release()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--logout", action="store_true", help="quên tài khoản đã lưu, đăng nhập lại")
    ap.add_argument("--stop", action="store_true", help="tắt agent đang chạy ngầm")
    ap.add_argument("--foreground", action="store_true", help="chạy trong cửa sổ này, không chạy ngầm")
    ap.add_argument("--background", action="store_true", help=argparse.SUPPRESS)  # tiến trình chạy ngầm (pythonw)
    ap.add_argument("--log", action="store_true", help=argparse.SUPPRESS)  # cửa sổ log mở từ biểu tượng khay
    ap.add_argument("--stop-if-outdated", action="store_true", help=argparse.SUPPRESS)  # agent.bat, trước khi cài thư viện
    ap.add_argument("--url", help=argparse.SUPPRESS)  # link l2mops-agent://… website bấm (Windows gọi qua pythonw)
    args = ap.parse_args()
    if args.background:
        return background()
    if args.url is not None:
        return open_url(args.url)
    if args.log:
        return view_log(t("Agent đang chạy ngầm trên máy này. Đây là cửa sổ log của nó."), plain=True, wait_on_exit=False)
    if args.stop_if_outdated:
        if running() and read_state().get("version") != bundle.code_version():
            say(t("Có bản code mới — đang tắt agent cũ để cập nhật…"))
            stop_running()
        return 0
    if args.stop:
        if not running():
            say(t("Không có agent nào đang chạy ngầm."))
            return 0
        say(t("Đang tắt agent…"))
        ok = stop_running()
        say(t("Đã tắt agent.") if ok else t("⚠ Không tắt được agent đang chạy. Tắt nó ở biểu tượng khay hệ thống rồi mở lại agent.bat."))
        return 0 if ok else 1
    if not (args.foreground or args.logout) and running() and read_state().get("version") == bundle.code_version():
        return view_log(t("Agent đang chạy ngầm trên máy này. Đây là cửa sổ log của nó."))  # mở lại agent.bat: không cần CSDL
    try:
        os.environ.setdefault("L2M_LANG", config.load_settings().get("default_lang", "vi"))
        if not config.automation_enabled():
            say(t("Thao tác tự động đang bị tắt trên máy này (L2M_NO_AUTOMATION=1)."))
            return 1
        if args.foreground or os.name != "nt":
            return foreground(args.logout)
        return launch(args.logout)
    except (KeyboardInterrupt, EOFError):
        say(t("Đã huỷ."))
        return 1
    finally:
        db.close_all()


if __name__ == "__main__":
    sys.exit(main())
