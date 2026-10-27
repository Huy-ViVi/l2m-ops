import streamlit as st

from core import store
from core.i18n import t
from ui import auth, common

common.page_header(t("🗂 Dữ liệu dùng chung"), t("Một người sửa, cả team dùng bản mới: bảng Item ID và file master của game đang chọn."))
g = common.game()
gid = g["id"]

tab_items, tab_master = st.tabs([t("Bảng Item ID ({group})", group=g["nc_app_group"] or gid), t("File master")])

with tab_items:
    rows = store.item_rows(gid)
    q = st.text_input(t("Tìm item"), key=f"items_q_{gid}")
    shown = [r for r in rows if not q or q.lower() in (r["name"] + " " + " ".join(r["aliases"]) + f" {r['item_id']}").lower()]
    st.dataframe(common.df([{
        "Item ID": r["item_id"], "Tên trên tool": r["name"], "Tên khác trong Excel (alias)": ", ".join(r["aliases"]),
        "Sửa bởi": r["updated_by"], "Lúc": r["updated_at"],
    } for r in shown]), hide_index=True, width="stretch")
    st.caption(t("{n} item của {game}. Mỗi game có bộ Item ID riêng. Tra ID mới ở trang Tạo gói NC → Tra Item lookup.",
                 n=len(rows), game=g["name"]))

    if auth.can_run():
        c1, c2 = st.columns(2)
        with c1, st.form(f"item_upsert_{gid}", clear_on_submit=True):
            st.markdown(t("**Thêm / sửa item — {game}**", game=g["name"]))
            item_id = st.number_input(t("Item ID (trùng ID có sẵn = sửa)"), min_value=1, step=1, value=None)
            name = st.text_input(t("Tên trên tool (vd Eva's Seal Chest (Bound))"))
            aliases = st.text_input(t("Alias, cách nhau bởi dấu phẩy (tên viết tắt trong Excel)"))
            if st.form_submit_button(t("💾 Lưu item"), type="primary"):
                if not item_id or not name.strip():
                    st.error(t("Cần Item ID và tên."))
                else:
                    store.upsert_item(int(item_id), name, [a for a in aliases.split(",")], auth.username(), gid)
                    common.flash(t("Đã lưu item {item_id} cho {game}.", item_id=int(item_id), game=g["name"]))
                    st.rerun()
        with c2:
            st.markdown(t("**Xoá item**"))
            target = st.selectbox(t("Chọn item"), [r["item_id"] for r in rows], index=None, key=f"item_del_{gid}",
                                  format_func=lambda i: next(f"{r['item_id']} — {r['name']}" for r in rows if r["item_id"] == i))
            sure = st.checkbox(t("Xác nhận xoá"), key=f"item_del_sure_{gid}")
            if st.button(t("🗑 Xoá item"), disabled=not (target and sure)):
                store.delete_item(target, auth.username(), gid)
                st.rerun()

with tab_master:
    meta = common.master_meta(gid)
    if meta:
        st.markdown(t("**Đang dùng ({game}):** `{name}` — tải lên {at}", game=g["name"], name=meta["name"], at=meta["uploaded_at"])
                    + (" " + t("bởi {user}", user=meta["uploaded_by"]) if meta.get("uploaded_by") else ""))
    else:
        st.info(t("Chưa có master của {game}. Tải lên ở bất kỳ function nào.", game=g["name"]))
    versions = common.master_versions(gid)
    if versions:
        st.markdown(t("**Các phiên bản đã tải lên**"))
        for v in versions:
            c1, c2, c3 = st.columns([3, 1, 1], vertical_alignment="center")
            c1.write(f"`{v['name']}` — {v['when']}" + (f" · {v['by']}" if v["by"] else ""))
            c2.download_button(t("⬇ Tải"), data=v["load"], file_name=v["name"], key=f"mv_dl_{gid}_{v['key']}")
            if auth.can_run() and c3.button(t("Dùng lại"), key=f"mv_use_{gid}_{v['key']}"):
                common.save_master(v["name"], v["load"]())
                common.flash(t("Đã đặt {name} làm master hiện hành của {game}.", name=v["name"], game=g["name"]))
                st.rerun()
