"""Đăng nhập và phân quyền. Chế độ local: không cần đăng nhập (một người dùng 'local' quyền admin)."""
from __future__ import annotations

import time

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


def agent_download_button(key: str) -> None:
    """Zip agent riêng cho người đang đăng nhập (core/bundle.py): giải nén, nháy đúp agent.bat là chạy."""
    name = username()
    st.download_button(t("⬇ Tải agent cho máy này"), data=lambda: bundle.agent_zip(name, config.database_url()),
                       file_name=f"L2M-Ops-agent-{name}.zip", mime="application/zip", key=key,
                       help=t("Giải nén rồi nháy đúp agent.bat: lần đầu tự cài Python + thư viện; đã có sẵn địa chỉ CSDL chung "
                              "và tài khoản của bạn. Không gửi file này cho người khác."))


COOKIE = "l2m_sid"


def _js_cookie(value: str, max_age: int) -> None:
    st.html(f"<script>document.cookie = '{COOKIE}={value}; path=/; max-age={max_age}; SameSite=Strict';</script>",
            unsafe_allow_javascript=True)


def _sign_in(u: dict) -> None:
    st.session_state["auth_user"] = u
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
                agent = jobs.agent_status(u["username"])
                st.caption(t("🟢 Agent: máy **{host}**", host=agent["host"]) if agent else t("⚪ Chưa bật agent (agent.bat)"),
                           help=t("Nút NC tool / MyTool trên website chạy trên máy đang mở agent.bat của tài khoản này. "
                                  "Mỗi người dùng tài khoản riêng, nếu không lệnh sẽ chạy trên máy người khác."))
                outdated = bool(agent) and agent.get("version") != bundle.code_version()
                if outdated:
                    st.caption(t("🟠 Agent đang chạy bản code khác website: tải agent bản mới, giải nén đè lên thư mục agent cũ "
                                 "rồi mở lại agent.bat."))
                if not agent or outdated:
                    agent_download_button("agent_zip_sidebar")
            if st.button(t("Đăng xuất"), key="logout"):
                logout()
                st.rerun()
        else:
            st.caption(t("Chế độ cá nhân (local)"))
