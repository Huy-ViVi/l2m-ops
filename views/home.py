import streamlit as st

from core import config, store
from core.ai import is_configured
from core.i18n import t
from ui import auth, common

common.page_header("🛠️ L2M Ops Toolkit", t("các workflow vận hành game NCV trước đây làm qua Claude Chat, giờ chạy độc lập. Đổi game ở thanh bên trái."))

settings = config.load_settings()
ai_ok, ai_msg = is_configured(settings)
g = common.game()
meta = common.master_meta()

c1, c2, c3 = st.columns(3)
c1.metric("AI", settings["ai"][settings["ai"]["provider"]].get("model") or ai_msg if ai_ok else t("Chưa cấu hình"))
c2.metric(t("Chế độ"), t("Team · {n} thành viên", n=len(store.list_users())) if config.team_mode() else t("Cá nhân (local)"))
c3.metric(t("Master {game}", game=g["name"]), meta["name"] if meta else t("Chưa có"))
if not ai_ok:
    st.warning(t("{reason}. Các bước dùng AI sẽ bị tắt cho đến khi admin cấu hình.", reason=ai_msg))
    if auth.is_admin():
        st.page_link("views/settings.py", label=t("Mở Cài đặt"), icon=":material/settings:")

recent = store.list_activities(limit=5, game=g["id"])
if recent:
    st.markdown(t("**Hoạt động gần đây — {game}**", game=g["name"]))
    for r in recent:
        st.write(f"#{r['id']} · {r['created_at'][:16]} · **{r['created_by']}** · {t(store.KINDS.get(r['kind'], r['kind']))} — {r['title']}")
    st.page_link("views/history.py", label=t("Xem toàn bộ lịch sử"), icon=":material/history:")

st.divider()
cols = st.columns(3)
cards = [
    ("views/nc_setup.py", t("Tạo gói nạp NC"), ":material/add_shopping_cart:",
     t("Đọc Item Mapping → dựng plan setup Goods Admin + Limit Admin theo convention → điền form trên NC tool "
       "(bạn duyệt và bấm Register) → audit lại từng trường.")),
    ("views/payment_errors.py", t("Case nạp lỗi"), ":material/report:",
     t("Sheet CS → tra MyTool Search Order (Export Excel) → lọc DELIVERY_SERVER_ERROR → lấy Diamonds từ master → "
       "xuất `Payment Error Case <MMDD>.xlsx` + CSV từng user.")),
    ("views/webshop_audit.py", t("Kiểm tra webshop VNG"), ":material/fact_check:",
     t("So gói đang bán trên MyTool (6 shop) với master: giá, thời gian bán, tên, trạng thái → báo cáo ✅/❌.")),
]
for col, (page, title, icon, desc) in zip(cols, cards):
    with col.container(border=True, height=230):
        st.page_link(page, label=f"**{title}**", icon=icon)
        st.write(desc)

st.divider()
st.markdown(t(
    "**Nguyên tắc an toàn**\n"
    "- App không bao giờ tự nhập mật khẩu. Bạn tự đăng nhập SSO trong cửa sổ trình duyệt của app (lưu ở `data/browser-profile`).\n"
    "- Trước mọi thao tác tạo/sửa trên tool, app luôn cho xem plan và chờ bạn xác nhận. Mặc định app chỉ điền form, bạn tự bấm Register.\n"
    "- AI chỉ dùng cho phần cần hiểu ngữ cảnh (map tên item, đọc Timeline Selling, viết tóm tắt). Kết quả AI luôn hiển thị để bạn duyệt."
))
