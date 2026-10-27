import streamlit as st

from core import db, store
from core.i18n import t
from ui import auth, common

common.page_header(t("👥 Quản lý thành viên"), t("Cấp tài khoản, phân quyền, khoá tài khoản và cấp token đồng bộ cho bản local."))
if not auth.is_admin():
    st.error(t("Chỉ admin mới vào được trang này."))
    st.stop()


def role_label(r: str) -> str:
    return t(store.ROLES.get(r, r))


st.markdown(t(
    "- **Admin**: toàn quyền, quản lý thành viên và cài đặt, sửa/xoá mọi bản ghi.\n"
    "- **Thành viên**: chạy function, lưu lịch sử, sửa dữ liệu dùng chung, sửa/xoá bản ghi của mình.\n"
    "- **Chỉ xem**: xem kết quả và lịch sử, tải file."
))
users = store.list_users()
st.dataframe(common.df([{
    "Username": u["username"], "Tên hiển thị": u["display_name"], "Vai trò": role_label(u["role"]),
    "Trạng thái": "Đang hoạt động" if u["active"] else "Đã khoá", "Token đồng bộ": "Có" if u["has_token"] else "—",
    "Tạo lúc": u["created_at"],
} for u in users]), hide_index=True, width="stretch")

c1, c2 = st.columns(2)
with c1, st.form("add_user", clear_on_submit=True):
    st.markdown(t("**Thêm thành viên**"))
    name = st.text_input("Username")
    display = st.text_input(t("Tên hiển thị"))
    pw = st.text_input(t("Mật khẩu ban đầu (tối thiểu 8 ký tự)"), type="password")
    role = st.selectbox(t("Vai trò"), list(store.ROLES), index=1, format_func=role_label)
    if st.form_submit_button(t("➕ Thêm"), type="primary"):
        try:
            store.create_user(name, display, pw, role, auth.username())
            common.flash(t("Đã tạo tài khoản {name}. Gửi username + mật khẩu cho thành viên qua kênh riêng.", name=name.strip().lower()))
            st.rerun()
        except ValueError as e:
            st.error(t(str(e)))

with c2:
    st.markdown(t("**Sửa thành viên**"))
    if not users:
        st.info(t("Chưa có thành viên nào."))
        st.stop()
    target = st.selectbox(t("Chọn thành viên"), [u["username"] for u in users], key="edit_user")
    u = next((x for x in users if x["username"] == target), users[0])
    active_admins = [x for x in users if x["role"] == "admin" and x["active"]]
    last_admin = u["role"] == "admin" and u["active"] and len(active_admins) == 1
    with st.form(f"edit_{target}"):
        display = st.text_input(t("Tên hiển thị"), value=u["display_name"] or "")
        role = st.selectbox(t("Vai trò"), list(store.ROLES), index=list(store.ROLES).index(u["role"]), format_func=role_label,
                            disabled=last_admin)
        active = st.checkbox(t("Đang hoạt động"), value=bool(u["active"]), disabled=last_admin)
        if last_admin:
            st.caption(t("Đây là admin duy nhất — không đổi vai trò/khoá được."))
        if st.form_submit_button(t("💾 Lưu")):
            store.update_user(target, auth.username(),
                              role=role if role != u["role"] else None,
                              active=active if active != bool(u["active"]) else None,
                              display_name=display if display != (u["display_name"] or "") else None)
            common.flash(t("Đã cập nhật {user}.", user=target))
            st.rerun()
    with st.form(f"pw_{target}", clear_on_submit=True):
        new_pw = st.text_input(t("Đặt lại mật khẩu"), type="password")
        if st.form_submit_button(t("🔑 Đặt lại mật khẩu")):
            try:
                store.set_password(target, new_pw, auth.username())
                st.success(t("Đã đặt lại mật khẩu."))
            except ValueError as e:
                st.error(t(str(e)))
    if db.is_remote():  # CSDL chung: bản local ghi thẳng vào CSDL, không cần token đồng bộ
        st.stop()
    if st.button(t("🔐 Cấp token đồng bộ mới"), key=f"tok_{target}",
                 help=t("Dùng cho bản local của thành viên đẩy kết quả lên server. Cấp mới sẽ vô hiệu token cũ.")):
        st.session_state["new_token"] = (target, store.issue_token(target, auth.username()))
    tok = st.session_state.get("new_token")
    if tok and tok[0] == target:
        st.warning(t("Token chỉ hiện một lần — copy ngay và gửi riêng cho thành viên. Họ dán vào Cài đặt → Server team ở bản local."))
        st.code(tok[1], language=None)
