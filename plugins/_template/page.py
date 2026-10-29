"""Trang mẫu: ghi chú theo gói nạp — minh hoạ cách dùng sdk (dữ liệu, mã chung, lịch sử, dữ liệu dùng chung của nền tảng).
Chép thư mục _template thành plugins/<id>/ rồi thay bằng nghiệp vụ của bạn."""
import streamlit as st

from core import sdk

sdk.header(sdk.t("Ghi chú gói nạp"), sdk.t("Plugin mẫu — cách lưu và đọc dữ liệu qua sdk"))

master = sdk.master()  # file master hiện hành của game đang chọn (None nếu chưa tải lên)
notes = sdk.load("notes")  # bản ghi của game đang chọn, mới sửa trước

if sdk.can_edit():
    with st.form(sdk.key("add"), clear_on_submit=True):
        product_key = st.text_input(sdk.t("Product Key"), placeholder="web.item195", key=sdk.key("product_key"))
        text = st.text_area(sdk.t("Ghi chú"), key=sdk.key("text"))
        if st.form_submit_button(sdk.t("💾 Lưu ghi chú"), type="primary"):
            if not product_key.strip() or not text.strip():
                st.error(sdk.t("Cần Product Key và nội dung."))
            else:
                now = sdk.now()  # giờ Việt Nam
                pk = sdk.product_key(product_key)  # mã chung, chuẩn như master: web.item195
                sdk.save("notes", {
                    "id": f"{pk}-{now:%Y%m%d%H%M%S}",  # khoá ổn định của bản ghi
                    "product_key": pk,
                    "note": text.strip(),
                    "date": f"{now:%Y-%m-%d}",
                })
                st.rerun()

if not notes:
    st.caption(sdk.t("Chưa có ghi chú nào."))
else:
    st.dataframe([{
        sdk.t("Product Key"): n["product_key"],
        sdk.t("Tên gói (master)"): master.display_name(n["product_key"]) if master else "",
        sdk.t("Ghi chú"): n["note"],
        sdk.t("Người sửa"): n["_updated_by"],
        sdk.t("Lúc"): n["_updated_at"],
    } for n in notes], hide_index=True)
    picked = st.selectbox(sdk.t("Chọn ghi chú"), [n["_key"] for n in notes], key=sdk.key("picked"))
    with st.expander(sdk.t("Lịch sử sửa / xoá của ghi chú này")):
        for old in sdk.history("notes", picked):
            st.write(f"{old['changed_at']} · {old['changed_by']} · {old['action']}: {old['data'].get('note', '')}")
    if sdk.can_edit():
        c1, c2 = st.columns(2)
        if c1.button(sdk.t("🗑 Xoá ghi chú"), key=sdk.key("delete")):
            sdk.delete("notes", picked)
            st.rerun()
        if c2.button(sdk.t("📌 Ghi vào lịch sử team"), key=sdk.key("record")):
            aid = sdk.record(sdk.t("Tổng hợp {n} ghi chú", n=len(notes)), {"metrics": {"Ghi chú": len(notes)}})
            st.success(sdk.t("Đã ghi bản #{aid} ở trang Lịch sử hoạt động.", aid=aid))
