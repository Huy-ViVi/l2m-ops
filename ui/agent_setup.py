"""Sau khi đăng nhập website: kiểm tra máy người dùng đã đủ điều kiện chạy NC tool / MyTool chưa.

Website (máy chủ ở Mỹ) không đọc được máy người dùng: mọi thông tin về máy do agent tự kiểm tra rồi ghi vào CSDL
(core/jobs.py, cột checks của bảng agents). Mỗi lần đăng nhập (hoặc bấm "Kiểm tra máy"):
- agent đang chạy và máy ổn (cùng bản code, có Edge, vào được NC tool) -> báo "máy đã đủ điều kiện";
- agent chạy nhưng còn thiếu (VPN tắt, bản cũ, thiếu Edge) -> hộp hướng dẫn sửa từng mục;
- tài khoản đã từng cài agent (bản có link l2mops-agent://) nhưng agent đang tắt -> website mở link
  l2mops-agent://start (trình duyệt hỏi mở L2M Ops Agent) rồi chờ agent báo về; quá 25 giây không thấy -> hộp hướng dẫn;
- agent bản cũ (chưa có link đó) đang tắt -> hộp hướng dẫn tải bản mới;
- chưa có agent -> hộp hướng dẫn cài đặt bằng hình (ui/guide_art.py) + nút tải agent.
Hộp thoại đang mở được vẽ lại ở mọi lượt chạy của trang (vd mất kết nối rồi nối lại khi vừa bật VPN) cho tới khi người
dùng đóng nó; nút "Kiểm tra lại" gửi lệnh ngay lúc bấm (on_click) rồi hiện dòng chờ và kết quả.
"""
from __future__ import annotations

import time
from html import escape

import streamlit as st

from core import bundle, config, jobs
from core.i18n import t
from ui import auth, guide_art

STATE = "machine_check"   # None: chưa kiểm tra · "guide": mở hướng dẫn · "starting": đang bật agent · "report"/"missing" ·
                          # "setup"/"fix": hộp thoại đang mở · "done"
DEADLINE = "machine_check_until"
NOTE = "machine_check_note"        # lời dẫn của hộp cài đặt: "" · "failed" (bật agent không được) · "old" (agent bản cũ)
HOST = "machine_check_host"        # máy ghi trên tiêu đề hộp sửa / trong lời dẫn
PENDING = "machine_check_pending"  # vừa bấm "Kiểm tra lại", đang chờ agent: {"mode", "before", "until", "sent"}
RESULT = "machine_check_result"    # lần "Kiểm tra lại" vừa xong: {"mode", "ok", "at"} — hiện trong hộp cho người dùng thấy
START_WAIT_SECONDS = 25
RECHECK_WAIT_SECONDS = 20
EDGE_URL = "https://www.microsoft.com/edge/download"


def recheck() -> None:
    """Nút "Kiểm tra máy": kiểm tra lại từ đầu ở lượt chạy sau."""
    st.session_state.pop(STATE, None)


def open_guide() -> None:
    """Nút "Hướng dẫn cài agent": mở thẳng hộp hướng dẫn."""
    st.session_state[STATE] = "guide"


def _close() -> None:
    """Đóng hộp thoại (nút Đóng / Để sau, dấu X, bấm ra ngoài): không mở lại cho tới lần đăng nhập / "Kiểm tra máy" sau."""
    ss = st.session_state
    ss[STATE] = "done"
    for key in (PENDING, RESULT):
        ss.pop(key, None)


def browser_on_windows() -> bool:
    try:
        ua = st.context.headers.get("User-Agent", "") or ""
    except Exception:  # noqa: BLE001
        ua = ""
    return not ua or "Windows" in ua  # không đọc được (vd chạy test) thì coi như Windows


def problems(agent: dict) -> list[str]:
    """Máy chạy agent còn thiếu gì (theo kết quả agent tự kiểm tra)."""
    issues = []
    if agent.get("version") != bundle.code_version():
        issues.append("outdated")
    checks = agent.get("checks") or {}
    if checks.get("edge") is False:
        issues.append("edge")
    if checks.get("nc_tool") is False:
        issues.append("vpn")
    return issues


def _checked(agent: dict | None) -> bool:
    """Agent đã gửi kết quả tự kiểm tra (agent bản cũ không gửi: coi như xong để báo "bản cũ")."""
    return bool(agent) and ("at" in (agent.get("checks") or {}) or agent.get("version") != bundle.code_version())


def machine_check() -> None:
    """Gọi ở mỗi lượt chạy app, sau khi đăng nhập (app.py). Mở tối đa một hộp thoại mỗi lượt."""
    if not auth.automation_via_agent():
        return
    ss = st.session_state
    state = ss.get(STATE)
    if state == "done":
        return
    if state == "starting":
        with st.sidebar:
            _wait_for_agent()
        return
    if state == "fix":  # hộp đang mở: vẽ lại (trang vừa chạy lại cả trang thì hộp không biến mất)
        _open_fix()
        return
    if state == "setup":
        _open_setup()
        return
    ss[STATE] = "done"
    user = auth.username()
    if state == "guide":
        _open_setup("")
        return
    agent = jobs.agent_status(user, fresh=True)
    if agent:
        _report(agent)
        return
    if state is None and not browser_on_windows():
        st.toast(t("Bạn đang mở website trên máy không phải Windows: xem và sửa dữ liệu bình thường; các nút NC tool / MyTool "
                   "cần một máy Windows đã cài agent."), icon=":material/info:", duration="long")
        return
    known = jobs.agent_known(user) if state is None else None
    if known and (known.get("checks") or {}).get("protocol"):  # đã cài agent có link l2mops-agent://: thử bật trên máy này
        ss[STATE], ss[DEADLINE] = "starting", time.time() + START_WAIT_SECONDS
        with st.sidebar:
            st.html(_launch_script(), unsafe_allow_javascript=True)
            _wait_for_agent()
    elif known:  # agent bản cũ chưa đăng ký link: trình duyệt không có gì để mở -> hướng dẫn tải bản mới
        _open_setup("old", known["host"])
    else:
        _open_setup("failed" if state in ("report", "missing") else "")


def _report(agent: dict) -> None:
    if problems(agent):
        _open_fix(agent["host"])
    else:
        st.toast(t("Máy **{host}** đã đủ điều kiện: agent đang chạy, có Microsoft Edge và vào được NC tool. Các nút NC tool / "
                   "MyTool đã dùng được.", host=agent["host"]), icon=":material/check_circle:", duration="long")


@st.fragment(run_every=2)
def _wait_for_agent() -> None:
    ss = st.session_state
    agent = jobs.agent_status(auth.username(), fresh=True)
    if _checked(agent) or time.time() > ss.get(DEADLINE, 0):
        ss[STATE] = "report" if agent else "missing"
        st.rerun(scope="app")
    st.caption(t("⏳ Đang bật agent trên máy bạn… Trình duyệt hỏi mở **L2M Ops Agent** thì tick **Always allow** rồi bấm "
                 "**Open**. Không thấy trình duyệt hỏi: bấm nút dưới đây."))
    _launch_link(t("▶ Bật agent"))  # trình duyệt có thể chặn tự mở link khi người dùng chưa bấm gì


def _launch_script() -> str:
    """Bấm hộ link l2mops-agent://start một lần. Chỉ Chrome / Edge: Firefox gặp link lạ thì hiện trang lỗi thay cho app."""
    url = f"{jobs.PROTOCOL}://start"
    return ("<script>(function(){if(!/Chrome\\//.test(navigator.userAgent))return;var a=document.createElement('a');"
            f"a.href='{url}';a.style.display='none';document.body.appendChild(a);a.click();a.remove();}})();</script>")


def _launch_link(label: str) -> None:
    """Nút bật agent đã cài trên máy này (link l2mops-agent://start; trình duyệt hỏi trước khi mở)."""
    st.html(f'<a href="{jobs.PROTOCOL}://start" style="display:inline-block;padding:0.4rem 0.85rem;border-radius:0.5rem;'
            'border:1px solid rgba(128,128,128,0.45);color:inherit;text-decoration:none;font-size:0.95rem;white-space:nowrap">'
            f'{escape(label)}</a>', width="content")


def _wait(cond, seconds: float) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end and not cond():
        time.sleep(1)


# ---- nút "Kiểm tra lại" trong hộp thoại ------------------------------------------------------
def _ask_recheck() -> None:
    """Chạy ngay lúc bấm (on_click, trước khi vẽ lại): agent cùng bản -> nhờ nó kiểm tra máy ngay; agent bản cũ -> chờ
    bản mới báo về; chưa có agent -> chờ agent bật lên."""
    user = auth.username()
    agent = jobs.agent_status(user, fresh=True)
    if not agent:
        mode = "find"
    elif agent.get("version") != bundle.code_version():  # agent bản cũ không hiểu lệnh kiểm tra lại
        mode = "update"
    else:
        mode = "check"
        jobs.request_check(user)
    st.session_state[PENDING] = {"mode": mode, "before": ((agent or {}).get("checks") or {}).get("at"),
                                 "until": time.time() + RECHECK_WAIT_SECONDS, "sent": f"{config.now():%H:%M:%S}"}


def _answered(pending: dict, agent: dict | None) -> bool:
    if not agent:
        return False
    if pending["mode"] == "check":
        return (agent.get("checks") or {}).get("at") != pending["before"]
    if pending["mode"] == "update":
        return agent.get("version") == bundle.code_version()
    return True


def _await_recheck(user: str) -> None:
    """Vừa bấm "Kiểm tra lại": hiện dòng chờ trong hộp, chờ agent trả lời (tối đa RECHECK_WAIT_SECONDS) rồi ghi kết quả."""
    ss = st.session_state
    pending = ss.get(PENDING)
    if not pending:
        return
    note = st.empty()
    note.info(t("⏳ Đã gửi yêu cầu kiểm tra lúc {time} — đang chờ agent trả lời (tối đa {n} giây)…", time=pending["sent"],
                n=RECHECK_WAIT_SECONDS), icon=":material/hourglass_top:")
    _wait(lambda: _answered(pending, jobs.agent_status(user, fresh=True)), pending["until"] - time.time())
    note.empty()
    agent = jobs.agent_status(user, fresh=True)
    at = ((agent or {}).get("checks") or {}).get("at") or ""
    ss[RESULT] = {"mode": pending["mode"], "ok": _answered(pending, agent), "at": at[-8:]}
    ss.pop(PENDING, None)


def _show_result(host: str) -> None:
    """Kết quả lần "Kiểm tra lại" vừa xong (để người dùng thấy đã kiểm tra, kể cả khi máy vẫn còn thiếu)."""
    res = st.session_state.pop(RESULT, None)
    if not res:
        return
    if res["ok"] and res["mode"] == "check":
        st.info(t("Agent vừa kiểm tra lại máy {host} lúc {time}.", host=host, time=res["at"]), icon=":material/fact_check:")
    elif not res["ok"] and res["mode"] == "check":
        st.warning(t("Agent trên máy {host} chưa trả lời sau {n} giây. Bấm Kiểm tra lại lần nữa; vẫn vậy thì mở lại agent.bat "
                     "trên máy đó.", host=host, n=RECHECK_WAIT_SECONDS), icon=":material/timer_off:")
    elif not res["ok"] and res["mode"] == "update":
        st.warning(t("Chưa thấy agent bản mới báo về. Giải nén bản mới đè lên thư mục agent cũ rồi mở lại agent.bat."),
                   icon=":material/timer_off:")
    elif not res["ok"]:
        st.warning(t("Chưa thấy agent báo về sau {n} giây. Xem chấm tròn ở khay hệ thống (góc phải thanh tác vụ); chưa có thì "
                     "làm theo các bước bên dưới.", n=RECHECK_WAIT_SECONDS), icon=":material/timer_off:")


# ---- hộp hướng dẫn cài đặt --------------------------------------------------------------
def _open_setup(note: str | None = None, host: str = "") -> None:
    """note khác None: mở hộp lần đầu (ghi lời dẫn); None: vẽ lại hộp đang mở."""
    ss = st.session_state
    if note is not None:
        ss[STATE], ss[NOTE], ss[HOST] = "setup", note, host
        ss.pop(RESULT, None)
    st.dialog(t("Cài agent cho máy này"), width="large", icon=":material/download:", on_dismiss=_close)(_setup_body)()


def _to_fix(host: str) -> None:
    st.session_state[STATE], st.session_state[HOST] = "fix", host


def _requirements() -> None:
    windows = browser_on_windows()
    rows = [(":material/check_circle:" if windows else ":material/cancel:",
             t("Máy Windows 10/11") + ("" if windows else " — " + t("trình duyệt này không chạy trên Windows"))),
            (":material/public:", t("Microsoft Edge (có sẵn trên Windows)")),
            (":material/vpn_lock:", t("VPN công ty khi chạy NC tool / MyTool")),
            (":material/wifi:", t("Internet ở lần cài đầu (tự tải Python ~15 MB + thư viện)")),
            (":material/shield:", t("Không cần quyền admin, không cần cài Python trước"))]
    st.markdown("  \n".join(f"{icon} {text}" for icon, text in rows))


def _steps(site: str, user: str) -> list[tuple[str, str, str]]:
    """(chú thích, hình SVG, mô tả cho trình đọc màn hình) của từng bước."""
    return [
        (t("Bấm **⬇ Tải agent cho máy này** (nút ở trên hoặc ở thanh bên trái). File zip đã có sẵn tài khoản của bạn — "
           "không gửi cho người khác."), guide_art.download(site, user), t("Nút tải agent ở thanh bên trái website")),
        (t("Mở thư mục Downloads, chuột phải file zip → **Extract All…** (Giải nén tất cả) → **Extract**."),
         guide_art.extract(user), t("Giải nén file zip")),
        (t("Mở thư mục vừa giải nén, nháy đúp **agent.bat**."), guide_art.run_bat(user), t("Nháy đúp agent.bat")),
        (t("Nếu Windows hiện **Windows protected your PC**: bấm **More info** → **Run anyway**. Agent không có chữ ký số "
           "nên Windows hỏi lại một lần."), guide_art.smartscreen(), t("Hộp SmartScreen của Windows")),
        (t("Lần đầu agent tự tải Python + thư viện (vài phút, cần Internet). Xong thì cửa sổ tự đóng — không cần làm gì thêm."),
         guide_art.console(user), t("Cửa sổ cài đặt agent")),
        (t("Agent chạy ngầm: chấm tròn xanh ở khay hệ thống (bấm **^** nếu không thấy). Tự bật cùng Windows; bấm vào chấm "
           "tròn để xem cửa sổ log."), guide_art.tray(user), t("Chấm tròn của agent ở khay hệ thống")),
        (t("Lần sau, khi agent đang tắt, website tự bật nó: trình duyệt hỏi mở **L2M Ops Agent** → tick **Always allow** → "
           "**Open**."), guide_art.browser_prompt(site), t("Trình duyệt hỏi mở L2M Ops Agent")),
    ]


def _setup_body() -> None:
    ss = st.session_state
    user = auth.username()
    _await_recheck(user)
    agent = jobs.agent_status(user, fresh=True)
    if agent:
        ss.pop(RESULT, None)
        if problems(agent):
            st.warning(t("Đã thấy agent trên máy **{host}**, nhưng còn thiếu vài bước.", host=agent["host"]),
                       icon=":material/build:")
            if st.button(t("Xem các bước còn thiếu"), type="primary", key="setup_to_fix", on_click=_to_fix, args=(agent["host"],)):
                st.rerun()  # cả trang chạy lại -> machine_check mở hộp sửa
        else:
            st.success(t("Đã thấy agent trên máy **{host}**: máy đã đủ điều kiện chạy NC tool / MyTool.", host=agent["host"]),
                       icon=":material/check_circle:")
            if st.button(t("Đóng"), type="primary", key="setup_close", on_click=_close):
                st.rerun()
        return
    note = ss.get(NOTE, "")
    _show_result("")
    if note == "old":
        st.warning(t("Agent trên máy **{host}** là bản cũ: website chưa bật được và chưa kiểm tra được máy. Tải agent bản mới "
                     "bên dưới, giải nén đè lên thư mục agent cũ rồi mở **agent.bat** một lần — từ lần sau website tự bật agent.",
                     host=ss.get(HOST, "")), icon=":material/update:")
    elif note == "failed":
        st.warning(t("Chưa bật được agent trên máy này. Máy này đã cài agent: bấm **▶ Bật agent** bên dưới (trình duyệt hỏi thì "
                     "chọn Open). Chưa cài hoặc đây là máy khác: làm theo các bước bên dưới."), icon=":material/power_off:")
    else:
        st.info(t("Thao tác NC tool / MyTool chạy ngay trên máy bạn (cần VPN công ty và phiên SSO của bạn) qua một agent nhỏ. "
                  "Cài một lần, khoảng 3 phút."), icon=":material/info:")
    _requirements()
    with st.container(horizontal=True, vertical_alignment="center"):
        auth.agent_download_button("agent_zip_dialog", primary=True)
        if note != "old":  # agent bản cũ không có link này
            _launch_link(t("▶ Bật agent"))
        st.button(t("Kiểm tra lại"), key="setup_recheck", icon=":material/refresh:", on_click=_ask_recheck)
    st.divider()
    for i, (caption, svg, alt) in enumerate(_steps(auth.site_url(), user), 1):
        st.markdown(f"**{i}.** {caption}")
        st.image(svg, width="stretch", alt=alt)


# ---- hộp sửa máy còn thiếu ----------------------------------------------------------------
def _open_fix(host: str | None = None) -> None:
    """host khác None: mở hộp lần đầu; None: vẽ lại hộp đang mở."""
    ss = st.session_state
    if host is not None:
        ss[STATE], ss[HOST] = "fix", host
        ss.pop(RESULT, None)
    st.dialog(t("Máy {host} cần thêm vài bước", host=ss.get(HOST, "")), width="medium", icon=":material/build:",
              on_dismiss=_close)(_fix_body)()


def _fix_body() -> None:
    user = auth.username()
    _await_recheck(user)
    agent = jobs.agent_status(user, fresh=True)
    if not agent:
        st.session_state.pop(RESULT, None)
        st.warning(t("Agent vừa tắt. Bấm **▶ Bật agent** (máy đã cài) hoặc mở lại agent.bat."), icon=":material/power_off:")
        with st.container(horizontal=True, vertical_alignment="center"):
            _launch_link(t("▶ Bật agent"))
            st.button(t("Kiểm tra lại"), key="fix_find", icon=":material/refresh:", on_click=_ask_recheck)
        return
    issues = problems(agent)
    host = agent["host"]
    if not issues:
        st.session_state.pop(RESULT, None)
        st.success(t("Máy **{host}** đã đủ điều kiện: agent đang chạy, có Microsoft Edge và vào được NC tool. Các nút NC tool / "
                     "MyTool đã dùng được.", host=host), icon=":material/check_circle:")
        if st.button(t("Đóng"), type="primary", key="fix_close", on_click=_close):
            st.rerun()
        return
    _show_result(host)
    st.markdown(t("Agent đang chạy trên máy **{host}**, nhưng còn thiếu:", host=host))
    if "outdated" in issues:
        with st.container(border=True):
            st.markdown(":material/update: **" + t("Agent đang chạy bản cũ") + "**  \n" +
                        t("Tải agent bản mới, giải nén đè lên thư mục agent cũ rồi mở lại agent.bat (agent cũ tự tắt)."))
            auth.agent_download_button("agent_zip_fix", primary=True)
    if "vpn" in issues:
        at = ((agent.get("checks") or {}).get("at") or "")[-8:]
        with st.container(border=True):
            st.markdown(":material/vpn_lock: **" + t("Chưa vào được NC tool") + "**  \n" +
                        t("Bật VPN công ty trên máy {host} rồi bấm Kiểm tra lại. Nếu VPN đã bật mà vẫn báo: kiểm tra địa chỉ NC "
                          "tool ở trang Cài đặt.", host=host))
            if at:
                st.caption(t("Agent thử kết nối NC tool lần cuối lúc {time} (tự thử lại mỗi phút).", time=at))
    if "edge" in issues:
        with st.container(border=True):
            st.markdown(":material/public: **" + t("Máy {host} chưa có Microsoft Edge", host=host) + "**  \n" +
                        t("Thao tác NC tool / MyTool mở Edge để dùng phiên SSO của bạn. Cài Edge rồi bấm Kiểm tra lại."))
            st.link_button(t("Tải Microsoft Edge"), EDGE_URL, icon=":material/open_in_new:")
    with st.container(horizontal=True):
        st.button(t("Kiểm tra lại"), type="primary", key="fix_recheck", icon=":material/refresh:", on_click=_ask_recheck)
        if st.button(t("Để sau"), key="fix_later", on_click=_close):
            st.rerun()
