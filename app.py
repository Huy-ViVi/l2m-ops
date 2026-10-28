"""L2M Ops Toolkit — gom các workflow vận hành Lineage2M SEA thành một app chạy độc lập.

Chạy cá nhân:  run.bat        (streamlit run app.py)
Chạy cho team: run-team.bat   (L2M_APP_MODE=team, mở trong mạng LAN, có đăng nhập + lịch sử chung)
"""
import os

import streamlit as st

from core import api_server, config, db, store
from core.i18n import t
from ui import agent_setup, auth, common

st.set_page_config(page_title="L2M Ops Toolkit", page_icon="🛠️", layout="wide")
config.ensure_dirs()
store.init()


@st.cache_resource
def _start_api():
    """API để bản local của thành viên đẩy kết quả lên (chỉ chạy ở chế độ team, một lần cho cả server)."""
    port = int(config.load_settings()["team"].get("api_port", 8502))
    try:
        api_server.start(os.environ.get("L2M_BIND", "0.0.0.0"), port)
        return {"ok": True, "port": port}
    except OSError as e:
        return {"ok": False, "port": port, "error": str(e)}


if config.team_mode() and not db.is_remote():  # CSDL chung thì bản local ghi thẳng vào CSDL, không cần API đồng bộ
    st.session_state["api_status"] = _start_api()

common.language_selector()
auth.require_login()
common.game_selector()
auth.sidebar_user()
agent_setup.machine_check()  # website: máy người đăng nhập đã đủ điều kiện chạy NC tool / MyTool chưa (agent)

pages = {
    "": [st.Page("views/home.py", title=t("Trang chủ"), icon=":material/home:", default=True)],
    t("Chức năng"): [
        st.Page("views/nc_setup.py", title=t("Tạo gói nạp NC"), icon=":material/add_shopping_cart:"),
        st.Page("views/payment_errors.py", title=t("Case nạp lỗi"), icon=":material/report:"),
        st.Page("views/webshop_audit.py", title=t("Kiểm tra webshop VNG"), icon=":material/fact_check:"),
    ],
    "Team": [
        st.Page("views/history.py", title=t("Lịch sử hoạt động"), icon=":material/history:"),
        st.Page("views/shared_data.py", title=t("Dữ liệu dùng chung"), icon=":material/database:"),
    ],
}
system = []
if config.team_mode() and auth.is_admin():
    system.append(st.Page("views/users.py", title=t("Quản lý thành viên"), icon=":material/group:"))
if auth.is_admin():
    system.append(st.Page("views/settings.py", title=t("Cài đặt"), icon=":material/settings:"))
if system:
    pages[t("Hệ thống")] = system
st.navigation(pages).run()
