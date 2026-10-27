"""Thành phần UI dùng chung giữa các trang."""
from __future__ import annotations

import functools
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from core import config, db, i18n, jobs, netcheck, store, sync
from core.ai import AIClient, AIError
from core.i18n import t
from core.master import Master
from ui import auth

# ---------------------------------------------------------------------------
# Ngôn ngữ giao diện — chọn ở đầu thanh bên, nhớ bằng cookie; core.i18n.t() đọc st.session_state["lang"]
# ---------------------------------------------------------------------------
LANG_COOKIE = "l2m_lang"


def _remember_lang() -> None:
    st.session_state["_save_lang_cookie"] = True


def language_selector() -> None:
    """Gọi đầu tiên mỗi lượt chạy (trước mọi chữ hiển thị, kể cả trang đăng nhập)."""
    if st.session_state.get("lang") not in i18n.LANGS:
        remembered = st.context.cookies.get(LANG_COOKIE)
        st.session_state["lang"] = remembered if remembered in i18n.LANGS else config.load_settings().get("default_lang", i18n.DEFAULT)
    with st.sidebar:
        st.selectbox("🌐 Language", list(i18n.LANGS), key="lang", format_func=i18n.LANGS.get, on_change=_remember_lang)
        if st.session_state.pop("_save_lang_cookie", False):
            st.html(f"<script>document.cookie = '{LANG_COOKIE}={st.session_state['lang']}; path=/; max-age=31536000; SameSite=Strict';</script>",
                    unsafe_allow_javascript=True)


# ---------------------------------------------------------------------------
# Game đang chọn — mọi thông số phía sau (app group, master, Item ID, URL MyTool, lịch sử) đi theo game này
# ---------------------------------------------------------------------------
def game() -> dict:
    settings = config.load_settings()
    return config.game(settings, st.session_state.get("game"))


GAME_COOKIE = "l2m_game"


def _remember_game() -> None:
    st.session_state["_save_game_cookie"] = True


def game_selector() -> None:
    settings = config.load_settings()
    games = settings["games"]
    if st.session_state.get("game") not in games:
        # Tải lại trang / mở tab mới: lấy game chọn lần trước (cookie), không có thì game mặc định.
        remembered = st.context.cookies.get(GAME_COOKIE)
        st.session_state["game"] = remembered if remembered in games else settings["default_game"]
    with st.sidebar:
        st.selectbox("🎮 Game", list(games), key="game", format_func=lambda g: games[g]["name"] or g, on_change=_remember_game,
                     help=t("Mọi thông số phía sau (app group NC tool, master, bảng Item ID, URL MyTool, lịch sử) đi theo game này."))
        if st.session_state.pop("_save_game_cookie", False):
            st.html(f"<script>document.cookie = '{GAME_COOKIE}={st.session_state['game']}; path=/; max-age=31536000; SameSite=Strict';</script>",
                    unsafe_allow_javascript=True)


def page_header(title: str, caption: str | None = None) -> None:
    g = game()
    st.title(title)
    st.caption(f"🎮 **{g['name']}**" + (f" · app group `{g['nc_app_group']}`" if g["nc_app_group"] else "")
               + (f" — {caption}" if caption else ""))
    if config.team_mode() and not auth.can_run():
        st.info(t("Bạn đang ở quyền **Chỉ xem**: xem được kết quả và lịch sử, nhưng không chạy hay lưu được."))
    if st.session_state.get("flash"):
        st.success(st.session_state.pop("flash"))


def flash(message: str) -> None:
    """Thông báo hiện sau st.rerun() (st.success thường bị mất khi trang chạy lại)."""
    st.session_state["flash"] = message


def df(records: list[dict] | None, translate: bool = True) -> pd.DataFrame:
    """DataFrame để hiển thị. Cột lẫn kiểu (số + chữ, hay gặp với dữ liệu thật) -> chuyển hết sang chữ,
    tránh lỗi chuyển đổi Arrow của st.dataframe.
    translate: dịch tên cột và các ô có chữ đúng bằng một chuỗi gốc có bản dịch (dữ liệu lưu vẫn giữ tiếng Việt).
    Bảng đưa vào st.data_editor rồi đọc lại theo tên cột phải để translate=False (đặt nhãn cột bằng column_config)."""
    frame = pd.DataFrame(records or [])

    def is_text(col) -> bool:  # pandas 3 để cột chữ ở StringDtype, không còn là object
        return frame[col].dtype == object or isinstance(frame[col].dtype, pd.StringDtype)

    for col in frame.columns:
        if frame[col].dtype == object:
            kinds = {type(v) for v in frame[col] if v is not None and v == v}
            if len(kinds) > 1:
                frame[col] = frame[col].map(lambda v: "" if v is None or v != v else str(v))
    if translate and i18n.get_lang() != i18n.DEFAULT:
        frame = frame.rename(columns=i18n.tr_value)
        for col in frame.columns:
            if is_text(col):
                frame[col] = frame[col].map(i18n.tr_value)
    return frame


def guarded(label: str, fn, *args, **kwargs):
    """Chạy một bước xử lý; lỗi thì hiện thông báo rõ + chi tiết kỹ thuật để gửi hỗ trợ, rồi dừng trang."""
    try:
        return fn(*args, **kwargs)
    except Exception as e:  # noqa: BLE001 — hiện lỗi có ngữ cảnh thay vì vỡ cả trang
        import traceback

        st.error(t("**{label}** bị lỗi: {error}", label=label, error=f"{type(e).__name__}: {e}"))
        with st.expander(t("Chi tiết lỗi (chụp màn hình phần này gửi người hỗ trợ)")):
            st.code(traceback.format_exc(), language=None)
        st.stop()


def records(frame: pd.DataFrame) -> list[dict]:
    """DataFrame (từ data_editor) -> list dict, NaN thành None."""
    obj = frame.astype(object)
    return obj.where(frame.notna(), None).to_dict("records")


VPN_HINTS = ("pangp", "globalprotect", "vpn", "virtual", "tap-", "wintun", "wireguard", "anyconnect", "fortinet", "zscaler")


@st.cache_data(ttl=60, show_spinner=False)
def network_addresses() -> list[dict]:
    """Các IPv4 của máy kèm tên card mạng; đánh dấu card VPN (máy khác thường KHÔNG vào được qua IP VPN)."""
    rows = []
    if sys.platform == "win32":
        ps = ("Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254*' } | "
              "ForEach-Object { $a = Get-NetAdapter -InterfaceIndex $_.InterfaceIndex -ErrorAction SilentlyContinue; "
              "[pscustomobject]@{ip=$_.IPAddress; name=$_.InterfaceAlias; desc=$a.InterfaceDescription} } | ConvertTo-Json -Compress")
        try:
            out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=15,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout.strip()
            data = json.loads(out) if out else []
            rows = [data] if isinstance(data, dict) else data
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
            rows = []
    if not rows:
        ips = {i[4][0] for i in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)}
        rows = [{"ip": ip, "name": "", "desc": ""} for ip in sorted(ips) if not ip.startswith("127.")]
    for r in rows:
        text = f"{r.get('name', '')} {r.get('desc', '')}".lower()
        r["vpn"] = any(h in text for h in VPN_HINTS)
    return sorted(rows, key=lambda r: (r["vpn"], "wi-fi" in (r.get("name") or "").lower()))


def lan_ip() -> str:
    """IP nên gửi cho thành viên: ưu tiên card mạng thật (Ethernet), không lấy IP VPN."""
    rows = network_addresses()
    return rows[0]["ip"] if rows else "127.0.0.1"


# ---------------------------------------------------------------------------
# Lịch sử hoạt động
# ---------------------------------------------------------------------------
def record(kind: str, title: str, summary: dict, files: dict[str, bytes] | None = None,
           note: str = "", status: str = "done") -> tuple[int, str]:
    """Lưu vào lịch sử (gắn game đang chọn). Ở bản local có cấu hình server team thì đẩy luôn lên server.
    Trả về (id bản ghi, thông báo đồng bộ)."""
    gid = game()["id"]
    aid = store.add_activity(kind, title, summary, auth.username(), files, note=note, status=status,
                             source="web" if config.team_mode() else "local", game=gid)
    msg = ""
    settings = config.load_settings()
    if not config.team_mode() and sync.configured(settings):
        ok, info = sync.push(settings, kind, title, summary, files, note, status, game=gid)
        store.update_activity(aid, auth.username(), sync_status=f"đã đồng bộ {info}" if ok else f"lỗi: {info}")
        msg = t("Đã đẩy lên server team ({info}).", info=info) if ok else t("Chưa đẩy được lên server team: {info}", info=info)
    return aid, msg


def record_button(label: str, kind: str, title: str, summary: dict, files: dict[str, bytes] | None, key: str) -> None:
    """Ô ghi chú + nút lưu vào lịch sử, dùng ở cuối mỗi function."""
    if not auth.can_run():
        return
    with st.container(border=True):
        st.markdown(t("**📌 Lưu vào lịch sử của team**") if config.team_mode() else t("**📌 Lưu vào lịch sử**"))
        note = st.text_area(t("Ghi chú (không bắt buộc)"), key=f"{key}_note", height=68)
        if st.button(label, key=f"{key}_btn"):
            aid, msg = record(kind, title, summary, files, note)
            st.success(t("Đã lưu bản ghi #{aid}. {msg}", aid=aid, msg=msg))
            st.page_link("views/history.py", label=t("Xem trong Lịch sử"), icon=":material/history:")


# ---------------------------------------------------------------------------
# Master dùng chung cho cả 3 function
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def _load_master(path: str, mtime: float, timeline_row: int, lang: str) -> Master:
    """lang nằm trong khoá cache vì cảnh báo khi đọc master được viết theo ngôn ngữ giao diện."""
    return Master(Path(path).read_bytes(), timeline_start_row=timeline_row)


def _master(path: Path, timeline_row: int) -> Master:
    with st.spinner(t("Đang đọc file master...")):
        return _load_master(str(path), path.stat().st_mtime, timeline_row, i18n.get_lang())


def load_master_path(path: Path, timeline_row: int = 121) -> Master:
    return _master(path, timeline_row)


def master_paths(gid: str | None = None) -> tuple[Path, Path, Path]:
    """(file master hiện hành, file thông tin, thư mục các phiên bản) của một game.
    Dùng CSDL chung: tải bản hiện hành từ CSDL về thư mục tạm nếu máy này chưa có đúng bản đó."""
    gid = gid or game()["id"]
    d = config.master_dir(gid)
    paths = d / "current.xlsx", d / "current.json", d / "history"
    if db.is_remote():
        _sync_master(gid, paths[0], paths[1])
    return paths


def _when(ts: str | None) -> str:
    """'2026-10-27 09:41:24' (CSDL) -> '27/10/2026 09:41' (cách hiển thị cũ)."""
    try:
        return datetime.strptime(ts or "", "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return ts or ""


def _write_master_cache(file: Path, meta: Path, version: dict, data: bytes) -> None:
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(data)
    meta.write_text(json.dumps({"name": version["name"], "uploaded_at": _when(version["uploaded_at"]),
                                "uploaded_by": version.get("uploaded_by") or "", "db_id": version["id"]},
                               ensure_ascii=False), encoding="utf-8")


def _sync_master(gid: str, file: Path, meta: Path) -> None:
    current = store.current_master(gid)
    if not current:
        file.unlink(missing_ok=True)
        meta.unlink(missing_ok=True)
        return
    local = json.loads(meta.read_text(encoding="utf-8-sig")) if meta.exists() else {}
    if local.get("db_id") != current["id"] or not file.exists():
        _write_master_cache(file, meta, current, store.master_content(current["id"]))


def master_meta(gid: str | None = None) -> dict | None:
    _, meta, _ = master_paths(gid)
    if meta.exists():
        return json.loads(meta.read_text(encoding="utf-8-sig"))
    return None


def master_versions(gid: str, limit: int = 30) -> list[dict]:
    """Các phiên bản master đã tải lên, mới nhất trước: [{key, name, when, by, load()}]."""
    if db.is_remote():
        return [{"key": f"db{v['id']}", "name": v["name"], "when": _when(v["uploaded_at"]), "by": v["uploaded_by"] or "",
                 "load": functools.partial(store.master_content, v["id"])} for v in store.master_versions(gid, limit)]
    _, _, history = master_paths(gid)
    out = []
    for p in sorted(history.glob("*.xlsx"), reverse=True)[:limit] if history.exists() else []:
        stamp, _, name = p.name.partition("_")
        out.append({"key": p.name, "name": name, "by": "", "load": p.read_bytes,
                    "when": f"{stamp[6:8]}/{stamp[4:6]}/{stamp[:4]} {stamp[9:11]}:{stamp[11:13]}"})
    return out


def save_master(name: str, data: bytes) -> None:
    file, meta, history = master_paths()
    if db.is_remote():
        gid = game()["id"]
        mid = store.add_master(gid, name, data, auth.username())
        _write_master_cache(file, meta, {"id": mid, "name": name, "uploaded_at": store.now(), "uploaded_by": auth.username()}, data)
        record("master", t("Cập nhật master: {name}", name=name), {"file": name, "size": len(data), "master_id": mid})
        return
    history.mkdir(parents=True, exist_ok=True)
    stamp = config.now().strftime("%Y%m%d-%H%M%S")
    file.write_bytes(data)
    shutil.copyfile(file, history / f"{stamp}_{Path(name).name}")
    meta.write_text(json.dumps({
        "name": name, "uploaded_at": config.now().strftime("%d/%m/%Y %H:%M"), "uploaded_by": auth.username(),
    }, ensure_ascii=False), encoding="utf-8")
    record("master", t("Cập nhật master: {name}", name=name), {"file": name, "size": len(data), "history_copy": f"{stamp}_{name}"})


def master_widget(key: str, timeline_row: int = 121) -> Master | None:
    g = game()
    file, _, _ = master_paths(g["id"])
    meta = master_meta(g["id"])
    with st.container(border=True):
        left, right = st.columns([3, 2], vertical_alignment="center")
        if meta and file.exists():
            left.markdown(f"**Master {g['name']}:** `{meta['name']}`  \n" + (
                t("Tải lên lúc {at} bởi {by} — dùng chung cho mọi function", at=meta["uploaded_at"], by=meta["uploaded_by"])
                if meta.get("uploaded_by") else t("Tải lên lúc {at} — dùng chung cho mọi function", at=meta["uploaded_at"])))
        else:
            left.warning(t("Chưa có file master **All Product Information** của {game} — tải lên bên phải.", game=g["name"])
                         if auth.can_run() else t("Chưa có file master **All Product Information** của {game}.", game=g["name"]))
        if auth.can_run():
            up = right.file_uploader(t("Tải master mới của {game} (.xlsx)", game=g["name"]), type=["xlsx"], key=f"master_up_{key}_{g['id']}")
            if up is not None:
                marker = f"{g['id']}:{up.name}:{up.size}"
                if st.session_state.get("master_marker") != marker:
                    save_master(up.name, up.getvalue())
                    st.session_state["master_marker"] = marker
                    st.rerun()
    if not file.exists():
        return None
    try:
        master = _master(file, timeline_row)
    except Exception as e:  # noqa: BLE001
        st.error(t("Không đọc được file master: {error}", error=e))
        return None
    if master.warnings:
        with st.expander(t("⚠ {n} cảnh báo khi đọc master", n=len(master.warnings))):
            for w in master.warnings:
                st.write("- " + w)
    return master


# ---------------------------------------------------------------------------
# AI
# ---------------------------------------------------------------------------
def ai_client() -> AIClient | None:
    if not auth.can_run():
        st.error(t("Quyền Chỉ xem không dùng được AI."))
        return None
    try:
        return AIClient()
    except AIError as e:
        st.error(str(e))
        if auth.is_admin():
            st.page_link("views/settings.py", label=t("Mở Cài đặt"), icon=":material/settings:")
        return None


# ---------------------------------------------------------------------------
# Browser automation (chạy tiến trình riêng, stream log lên UI)
# ---------------------------------------------------------------------------
AGENT_PICKUP_SECONDS = 40  # agent không nhận lệnh trong chừng này giây -> huỷ lệnh, báo người bấm
AGENT_MAX_SECONDS = 3 * 3600


def automation_reason() -> str:
    """Vì sao người dùng này không chạy được thao tác tự động ở đây ('' nếu chạy được)."""
    if auth.automation_allowed():
        return ""
    if not auth.can_run():
        return t("Quyền Chỉ xem không chạy được thao tác tự động.")
    if auth.automation_via_agent():  # website, hoặc mở app từ máy khác
        return t("Chưa thấy agent trên máy bạn. Thao tác NC tool / MyTool cần VPN công ty và phiên SSO của chính bạn, nên website "
                 "gửi lệnh về máy bạn chạy. Lần đầu: bấm **⬇ Tải agent cho máy này**, giải nén, nháy đúp **agent.bat** (tự cài "
                 "mọi thứ, có sẵn tài khoản của bạn), bật VPN và giữ cửa sổ đó mở. Tải lại trang này sau vài giây.")
    if config.team_mode():
        return t("Thao tác tự động dùng phiên đăng nhập MyTool/NC tool của chính bạn, nên phải chạy trên máy bạn: "
                 "mở bản local của app (run.bat), cấu hình server team ở trang Cài đặt — kết quả sẽ tự đẩy lên đây. "
                 "Hoặc tải file lên thủ công ở tab bên cạnh.")
    return t("Thao tác tự động đang bị tắt trên máy này (L2M_NO_AUTOMATION=1). Hãy tải file lên thủ công.")


def automation_notice() -> bool:
    reason = automation_reason()
    if reason:
        st.info(reason)
        if auth.automation_via_agent():
            auth.agent_download_button("agent_zip_notice")  # mỗi trang gọi automation_notice một lần
    elif not auth.automation_local():
        agent = jobs.agent_status(auth.username()) or {}
        st.caption(t("🟢 Thao tác tự động chạy trên máy **{host}** (agent của tài khoản **{user}**). Không phải máy của bạn? "
                     "Bạn đang dùng tài khoản của người khác: đăng xuất rồi đăng nhập bằng tài khoản riêng.",
                     host=agent.get("host", "?"), user=auth.username()))
    return not reason


def run_job(job: str, payload: dict, title: str) -> dict | None:
    payload = {"game": game()["id"], **payload}
    if auth.automation_local():
        return _run_local(job, payload, title)
    if auth.automation_via_agent():
        return _run_via_agent(job, payload, title)
    st.error(t("Bạn không chạy được thao tác tự động từ máy này."))
    return None


def _show_outcome(status, title: str, result: dict) -> dict:
    ok = bool(result.get("ok"))
    # Lỗi mạng đã có thông báo rõ ràng -> thu gọn log; lỗi khác mở log để xem chi tiết.
    status.update(label=f"{title} — {t('xong') if ok else t('lỗi (bấm để xem log)')}", state="complete" if ok else "error",
                  expanded=not ok and result.get("kind") not in ("network", "closed"))
    return result


def _run_via_agent(job: str, payload: dict, title: str) -> dict | None:
    """Gửi lệnh tới agent trên máy người bấm, chờ và hiện log trực tiếp (core/jobs.py)."""
    user = auth.username()
    agent = jobs.agent_status(user, fresh=True)
    if not agent:
        st.error(automation_reason() or t("Chưa thấy agent trên máy bạn."))
        return None
    jid = jobs.enqueue(job, {**payload, "_lang": i18n.get_lang()}, user)
    started = last_check = time.monotonic()
    shown = None
    with st.status(title, expanded=True) as status:
        st.caption(t("Chạy trên máy **{host}** (agent của {user}) — giữ trang này mở tới khi xong.", host=agent["host"], user=user))
        box = st.empty()
        while True:
            time.sleep(1)
            row = jobs.get(jid) or {"status": "error", "log": ""}
            if row["log"] != shown:
                shown = row["log"]
                box.code("\n".join(shown.splitlines()[-60:]) or t("Đang chờ agent nhận lệnh…"), language=None)
            elapsed = time.monotonic() - started
            if row["status"] in jobs.FINISHED:
                result = jobs.result(jid, config.WORK_DIR / "jobs" / str(jid)) or {
                    "ok": False, "error": t("Lệnh đã bị huỷ hoặc hết hạn trước khi agent chạy.") if row["status"] in ("expired", "cancelled")
                    else t("Tiến trình automation không trả kết quả — xem log phía trên.")}
                break
            if row["status"] == "queued" and elapsed > AGENT_PICKUP_SECONDS and jobs.cancel(jid):
                result = {"ok": False, "error": t("Agent trên máy {host} không nhận lệnh. Kiểm tra cửa sổ agent.bat còn mở và máy còn mạng, "
                                                  "rồi bấm lại.", host=agent["host"])}
                break
            if time.monotonic() - last_check > 15:
                last_check = time.monotonic()
                if not jobs.agent_status(user, fresh=True):
                    jobs.cancel(jid, only_queued=False)
                    result = {"ok": False, "error": t("Mất liên lạc với agent trên máy {host} (cửa sổ agent bị đóng hoặc máy mất mạng).",
                                                      host=agent["host"])}
                    break
            if elapsed > AGENT_MAX_SECONDS:
                jobs.cancel(jid, only_queued=False)
                result = {"ok": False, "error": t("Quá thời gian chờ agent.")}
                break
        _show_outcome(status, title, result)
    if not result.get("ok"):
        st.error(result.get("error", t("Lỗi không rõ")), icon="🌐" if result.get("kind") == "network" else None)
    return result


def _run_local(job: str, payload: dict, title: str) -> dict:
    config.ensure_dirs()
    stamp = config.now().strftime("%Y%m%d-%H%M%S")
    inp = config.WORK_DIR / f"{job}-{stamp}-in.json"
    out = config.WORK_DIR / f"{job}-{stamp}-out.json"
    inp.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8")
    cmd = [sys.executable, "-m", "automation.runner", job, "--input", str(inp), "--output", str(out)]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1", "L2M_LANG": i18n.get_lang()}
    lines: list[str] = []
    with st.status(title, expanded=True) as status:
        box = st.empty()
        proc = subprocess.Popen(
            cmd, cwd=config.APP_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace", env=env, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        for line in proc.stdout:
            lines.append(line.rstrip())
            box.code("\n".join(lines[-60:]), language=None)
        proc.wait()
        result = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {
            "ok": False, "error": t("Tiến trình automation không trả kết quả — xem log phía trên.")}
        _show_outcome(status, title, result)
    if not result.get("ok"):
        st.error(result.get("error", t("Lỗi không rõ")), icon="🌐" if result.get("kind") == "network" else None)
    return result


@st.cache_data(ttl=30, show_spinner=False)
def _reach(url: str, lang: str) -> dict:
    """lang trong khoá cache: thông báo lỗi mạng viết theo ngôn ngữ giao diện."""
    return netcheck.check(url, timeout=3)


def reachability_warning(url: str, label: str) -> bool:
    """Cảnh báo ngay trên trang nếu máy này chưa tới được tool (vd chưa bật VPN). Trả về True nếu tới được.
    Chạy qua agent thì máy này (website) không kiểm tra được — agent tự kiểm tra trước khi mở trình duyệt."""
    if not auth.automation_local() or not url:
        return True
    r = _reach(url, i18n.get_lang())
    if r["ok"] or (r["step"] == "dns" and netcheck.system_proxy_configured()):
        return True
    c1, c2 = st.columns([5, 1], vertical_alignment="center")
    c1.warning(f"**{label}:** {r['message']}", icon="🌐")
    if c2.button(t("Kiểm tra lại"), key=f"reach_{label}"):
        _reach.clear()
        st.rerun()
    return False
