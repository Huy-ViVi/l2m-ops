"""Đăng nhập và phân quyền. Chế độ local: không cần đăng nhập (một người dùng 'local' quyền admin)."""
from __future__ import annotations

import re
import time
from urllib.parse import urlsplit

import streamlit as st

from core import bundle, config, db, jobs, store
from core.i18n import t

LOCAL_USER = {"username": "local", "display_name": "Máy này", "role": "admin", "active": 1}
RANK = {"viewer": 0, "member": 1, "admin": 2}
LOOPBACK = {None, "", "127.0.0.1", "::1", "localhost"}


def user() -> dict | None:
    if not config.team_mode():
        return LOCAL_USER
    return st.session_state.get("auth_user")


def username() -> str:
    return (user() or {}).get("username", "?")


def has_role(role: str) -> bool:
    u = user()
    return bool(u) and RANK.get(u["role"], -1) >= RANK[role]


def can_run() -> bool:
    """Được chạy function, lưu lịch sử, sửa dữ liệu dùng chung."""
    return has_role("member")


def is_admin() -> bool:
    return has_role("admin")


def own_browser() -> str:
    """Trình duyệt người đang đăng nhập đã chọn (kênh, config.TEAM_BROWSER, hoặc '' = chưa chọn -> theo mặc định của team)."""
    return (user() or {}).get("browser") or ""


def channel_from_user_agent(ua: str) -> str:
    """Kênh Playwright của trình duyệt đang mở website: Edge / Chrome trên Windows; '' nếu không nhận ra.
    Máy khác Windows (Mac, điện thoại) không nói lên trình duyệt trên máy chạy agent. Cốc Cốc, Opera, ứng dụng Electron…
    cũng ghi "Chrome/" trong User-Agent nhưng không phải Chrome."""
    if "Windows" not in ua:
        return ""
    if "Edg/" in ua:
        return "msedge"
    if "Chrome/" in ua and not re.search(r"OPR/|coc_coc|CocCoc|YaBrowser|Vivaldi|SamsungBrowser|Electron/", ua):
        return "chrome"
    return ""


def browser_in_use() -> str:
    try:
        return channel_from_user_agent(st.context.headers.get("User-Agent", "") or "")
    except Exception:  # noqa: BLE001 — không đọc được header (vd chạy test)
        return ""


def can_edit(record: dict) -> bool:
    return is_admin() or (can_run() and record.get("created_by") == username())


def is_host_request() -> bool:
    """Người dùng đang ngồi tại máy chạy app (truy cập qua localhost). Website công khai (L2M_PUBLIC=1, vd Streamlit Cloud)
    thì không ai là 'máy chủ': không tạo admin đầu tiên, không đọc thư mục trên máy, không chạy automation."""
    if config.env("L2M_PUBLIC") == "1":
        return False
    if not config.team_mode():
        return True
    return st.context.ip_address in LOOPBACK


def automation_local() -> bool:
    """Chạy automation ngay trong app này: điều khiển trình duyệt dùng phiên SSO của máy chạy app,
    nên chỉ người ngồi tại máy đó mới được bấm."""
    return config.automation_enabled() and can_run() and is_host_request()


def automation_via_agent() -> bool:
    """Website / mở app từ máy khác (CSDL chung): lệnh gửi tới agent trên máy của chính người bấm (core/jobs.py)."""
    return not automation_local() and can_run() and db.is_remote()


def automation_allowed() -> bool:
    return automation_local() or (automation_via_agent() and jobs.agent_status(username()) is not None)


def site_url() -> str:
    """Gốc địa chỉ website đang mở (vd https://….streamlit.app) — cho mục "Mở website" ở biểu tượng khay của agent."""
    try:
        parts = urlsplit(st.context.url or "")
    except Exception:  # noqa: BLE001
        return ""
    return f"{parts.scheme}://{parts.netloc}" if parts.scheme in ("http", "https") and parts.netloc else ""


_published: set[str] = set()


def _publish_site_version() -> None:
    """Website ghi bản code của nó vào CSDL (một lần mỗi tiến trình): agent chạy ngầm so để báo có bản mới."""
    version = bundle.code_version()
    if version not in _published:
        try:
            jobs.publish_site_version(version)
            _published.add(version)
        except Exception:  # noqa: BLE001 — chỉ là thông báo, lần tải trang sau thử lại
            pass


def agent_download_button(key: str, primary: bool = False) -> None:
    """Zip agent riêng cho người đang đăng nhập (core/bundle.py): giải nén, nháy đúp agent.bat là chạy."""
    name, site = username(), site_url()
    st.download_button(t("⬇ Tải agent cho máy này"), data=lambda: bundle.agent_zip(name, config.database_url(), site_url=site),
                       file_name=f"L2M-Ops-agent-{name}.zip", mime="application/zip", key=key, on_click="ignore",
                       type="primary" if primary else "secondary",
                       help=t("Giải nén rồi nháy đúp agent.bat: lần đầu tự cài Python + thư viện; đã có sẵn địa chỉ CSDL chung "
                              "và tài khoản của bạn. Không gửi file này cho người khác."))


def _save_browser(channel: str) -> None:
    from ui import agent_setup  # agent_setup import module này

    store.set_browser(username(), channel)
    st.session_state["auth_user"] = store.get_user(username())
    agent_setup.browser_changed()  # agent kiểm tra lại máy với trình duyệt mới


def _pick_browser() -> None:
    _save_browser(st.session_state["own_browser"] or config.TEAM_BROWSER)


def _browser_picker(u: dict) -> None:
    """Mỗi người chọn trình duyệt mở NC tool / MyTool trên máy mình. Chưa chọn lần nào: lấy luôn trình duyệt đang mở
    website (Edge / Chrome); không nhận ra thì theo mặc định của team."""
    own = u.get("browser") or ""
    seen = "" if own else browser_in_use()
    if seen:
        _save_browser(seen)
        st.session_state.pop("own_browser", None)  # ô chọn hiện đúng giá trị vừa lưu
        own = seen
    team = config.browser_channel(config.load_settings())
    options = ["", *config.BROWSERS]
    st.selectbox(t("Trình duyệt"), options, index=options.index(own) if own in options else 0, key="own_browser",
                 on_change=_pick_browser,
                 format_func=lambda c: config.BROWSERS[c] if c else t("Theo team ({browser})", browser=config.BROWSERS.get(team, team)),
                 help=t("Trình duyệt mở NC tool / MyTool trên máy của bạn (chỉ áp dụng cho tài khoản của bạn). Lần đầu app tự "
                        "chọn theo trình duyệt bạn đang mở website (Edge / Chrome). Đổi trình duyệt thì đăng nhập SSO lại một "
                        "lần trong trình duyệt mới."))


COOKIE = "l2m_sid"


def _js_cookie(value: str, max_age: int) -> None:
    st.html(f"<script>document.cookie = '{COOKIE}={value}; path=/; max-age={max_age}; SameSite=Strict';</script>",
            unsafe_allow_javascript=True)


def _sign_in(u: dict) -> None:
    st.session_state["auth_user"] = u
    st.session_state.pop("machine_check", None)  # vừa đăng nhập: kiểm tra máy lại (ui/agent_setup.py)
    sid = store.create_session(u["username"])
    st.session_state["sid"] = sid
    st.session_state["set_cookie"] = sid


def require_login() -> None:
    if not config.team_mode():
        return
    current = st.session_state.get("auth_user")
    if current:
        fresh = store.get_user(current["username"])  # cập nhật nếu admin vừa đổi quyền / khoá tài khoản
        if fresh and fresh["active"] and store.session_user(st.session_state.get("sid")):
            st.session_state["auth_user"] = fresh
            return
        st.session_state.pop("auth_user", None)
    # Tải lại trang / mở tab mới: khôi phục phiên từ cookie.
    sid = st.context.cookies.get(COOKIE)
    u = store.session_user(sid)
    if u:
        st.session_state.update(auth_user=u, sid=sid)
        return
    _login_page()
    st.stop()


def logout() -> None:
    store.delete_session(st.session_state.pop("sid", None) or st.context.cookies.get(COOKIE))
    st.session_state.pop("auth_user", None)
    st.session_state["clear_cookie"] = True


def _login_page() -> None:
    if st.session_state.pop("clear_cookie", False):
        _js_cookie("", 0)
    st.title("🛠️ L2M Ops Toolkit")
    if store.user_count() == 0:
        if not is_host_request():
            st.warning(t("Server chưa có tài khoản admin. Người quản trị cần mở app ngay trên máy server để tạo admin đầu tiên."))
            return
        st.subheader(t("Tạo tài khoản admin đầu tiên"))
        st.caption(t("Tài khoản này quản lý thành viên, phân quyền và cài đặt của server team."))
        with st.form("bootstrap"):
            name = st.text_input("Username")
            display = st.text_input(t("Tên hiển thị"))
            pw = st.text_input(t("Mật khẩu (tối thiểu 8 ký tự)"), type="password")
            pw2 = st.text_input(t("Nhập lại mật khẩu"), type="password")
            if st.form_submit_button(t("Tạo admin"), type="primary"):
                if pw != pw2:
                    st.error(t("Hai mật khẩu không khớp"))
                else:
                    try:
                        store.create_user(name, display, pw, "admin", by=name.strip().lower() or "?")
                        _sign_in(store.get_user(name.strip().lower()))
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
        return
    st.subheader(t("Đăng nhập"))
    with st.form("login"):
        name = st.text_input("Username")
        pw = st.text_input(t("Mật khẩu"), type="password")
        if st.form_submit_button(t("Đăng nhập"), type="primary"):
            fails = st.session_state.get("login_fails", 0)
            if fails >= 5:
                time.sleep(min(fails, 10))  # làm chậm dò mật khẩu
            u = store.authenticate(name, pw)
            if u:
                _sign_in(u)
                st.session_state["login_fails"] = 0
                store.log(u["username"], "đăng nhập", u["username"], f"IP {st.context.ip_address or 'localhost'}")
                st.rerun()
            else:
                st.session_state["login_fails"] = fails + 1
                st.error(t("Sai username/mật khẩu hoặc tài khoản đã bị khoá."))
    st.caption(t("Chưa có tài khoản? Liên hệ admin của team để được cấp."))


def sidebar_user() -> None:
    u = user()
    if not u:
        return
    with st.sidebar:
        if config.team_mode():
            if st.session_state.get("set_cookie"):
                _js_cookie(st.session_state.pop("set_cookie"), store.SESSION_DAYS * 86400)
            st.markdown(f"**{u.get('display_name') or u['username']}**  \n{t(store.ROLES.get(u['role'], u['role']))} · `{u['username']}`")
            if automation_via_agent():  # lệnh NC tool / MyTool đi theo tài khoản -> cho thấy rõ nó chạy trên máy nào
                if config.env("L2M_PUBLIC") == "1":
                    _publish_site_version()
                agent = jobs.agent_status(u["username"])
                st.caption(t("🟢 Agent: máy **{host}**", host=agent["host"]) if agent else t("⚪ Chưa bật agent (agent.bat)"),
                           help=t("Nút NC tool / MyTool trên website chạy trên máy đang chạy agent của tài khoản này. "
                                  "Mỗi người dùng tài khoản riêng, nếu không lệnh sẽ chạy trên máy người khác."))
                outdated = bool(agent) and agent.get("version") != bundle.code_version()
                if outdated:
                    st.caption(t("🟠 Agent đang chạy bản code khác website. Agent cài từ ngày 29/10/2026 trở đi tự cập nhật trong "
                                 "vài phút; bản cài trước đó: tải agent bản mới, giải nén đè lên thư mục agent cũ rồi mở lại "
                                 "agent.bat (một lần, từ đó tự cập nhật)."))
                if not agent or outdated:
                    agent_download_button("agent_zip_sidebar")
                elif st.button(t("Hiện cửa sổ agent"), key="agent_show", icon=":material/open_in_new:",
                               help=t("Agent chạy ngầm trên máy {host}. Bấm để mở cửa sổ log của nó trên máy đó "
                                      "(đóng cửa sổ log không tắt agent).", host=agent["host"])):
                    jobs.request_show(u["username"])
                    st.toast(t("Đã gửi — cửa sổ agent sẽ hiện trên máy {host} sau vài giây.", host=agent["host"]))
                st.button(t("Kiểm tra máy"), key="machine_recheck", icon=":material/fact_check:", type="tertiary",
                          on_click=lambda: st.session_state.pop("machine_check", None),  # ui/agent_setup.py chạy lại từ đầu
                          help=t("Kiểm tra máy bạn đã đủ điều kiện chạy NC tool / MyTool chưa; thiếu gì sẽ hiện hướng dẫn."))
                _browser_picker(u)
            if st.button(t("Đăng xuất"), key="logout"):
                logout()
                st.rerun()
        else:
            st.caption(t("Chế độ cá nhân (local)"))
