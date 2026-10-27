from pathlib import Path

import streamlit as st

from core import config, cowork_import, store
from core.i18n import t
from ui import auth, common

common.page_header(t("🕘 Lịch sử hoạt động"), t("Mọi đợt xử lý đã lưu: ai làm, lúc nào, kết quả và file đi kèm. Thêm ghi chú, sửa trạng thái, xoá bản ghi."))
g = common.game()
game_names = {gid: p["name"] for gid, p in config.load_settings()["games"].items()}


def kind_label(k: str) -> str:
    return t(store.KINDS.get(k, k))


def status_label(s: str) -> str:
    return t(store.STATUSES.get(s, s))


if auth.can_run() and auth.is_host_request():  # đọc thư mục trên máy chạy app
    with st.expander(t("📥 Nhập lịch sử từ Claude Cowork (skill package-creation)")):
        st.caption(t("Đọc bảng Setup History, counter.md và các file log trong thư mục 07_Package-Creation; "
                     "bổ sung Item ID mới. Bản ghi đã nhập sẽ được bỏ qua, chạy lại không tạo trùng."))
        folder = st.text_input(t("Thư mục"), value=str(cowork_import.DEFAULT_DIR), key="cw_dir")
        if st.button(t("Nhập / cập nhật lịch sử"), key="cw_import"):
            path = Path(folder)
            if not (path / "SKILL.md").exists():
                st.error(t("Không thấy SKILL.md trong {path}", path=path))
            else:
                res = common.guarded(t("Nhập lịch sử Cowork"), cowork_import.import_folder, path, auth.username(), g["id"])
                common.flash(t("Đã nhập {records} đợt mới (bỏ qua {skipped} đợt đã có), thêm {items} Item ID.",
                               records=res["records"], skipped=res["skipped"], items=res["items"]))
                st.rerun()

tab_list, tab_log = st.tabs([t("Hoạt động"), t("Nhật ký thay đổi")])

with tab_log:
    st.caption(t("Ghi lại mọi thao tác thay đổi dữ liệu: tạo/sửa/xoá bản ghi, Item ID, thành viên, cài đặt, đăng nhập."))
    st.dataframe(common.df([{"Lúc": r["at"], "Người": r["username"], "Thao tác": r["action"], "Đối tượng": r["target"],
                             "Chi tiết": r["detail"]} for r in store.changelog()]), hide_index=True, width="stretch")

with tab_list:
    c1, c2, c3, c4 = st.columns([2, 2, 1, 1], vertical_alignment="bottom")
    kinds = c1.multiselect(t("Loại"), list(store.KINDS), format_func=kind_label, key="hist_kinds")
    search = c2.text_input(t("Tìm theo tiêu đề, ghi chú, người tạo, nội dung"), key="hist_search")
    all_games = c3.toggle(t("Mọi game"), key="hist_all_games", help=t("Tắt: chỉ hiện lịch sử của {game}", game=g["name"]))
    show_deleted = c4.toggle(t("Hiện bản đã xoá"), key="hist_deleted") if auth.is_admin() else False
    rows = store.list_activities(kinds, search.strip(), show_deleted, game=None if all_games else g["id"])
    if not rows:
        st.info((t("Chưa có bản ghi nào.") if all_games else t("Chưa có bản ghi nào của {game}.", game=g["name"])) + " "
                + t("Ở mỗi function, sau khi có kết quả, bấm **Lưu vào lịch sử**."))
        st.stop()
    st.dataframe(common.df([{
        "ID": r["id"], "Game": game_names.get(r["game"], r["game"]), "Loại": kind_label(r["kind"]), "Tiêu đề": r["title"],
        "Trạng thái": status_label(r["status"]), "Người tạo": r["created_by"], "Lúc tạo": r["created_at"],
        "Sửa lần cuối": f"{r['updated_by']} · {r['updated_at']}", "Nguồn": r["source"],
        "Đồng bộ": r["sync_status"] or "", "Đã xoá": "🗑" if r["deleted"] else "",
    } for r in rows]), hide_index=True, width="stretch")

    aid = st.selectbox(t("Xem chi tiết bản ghi"), [r["id"] for r in rows], key="hist_pick",
                       format_func=lambda i: next(f"#{r['id']} — {r['title']}" for r in rows if r["id"] == i))
    rec = store.get_activity(aid)
    st.divider()
    st.subheader(f"#{rec['id']} · {rec['title']}")
    st.caption(f"🎮 {game_names.get(rec['game'], rec['game'])} · {kind_label(rec['kind'])} · {status_label(rec['status'])} · "
               + t("tạo bởi **{created_by}** lúc {created_at} · sửa lần cuối {updated_by} lúc {updated_at} · nguồn {source}",
                   created_by=rec["created_by"], created_at=rec["created_at"], updated_by=rec["updated_by"],
                   updated_at=rec["updated_at"], source=rec["source"])
               + (" · " + t("🗑 đã xoá") if rec["deleted"] else ""))
    if rec["note"]:
        st.info(t(rec["note"]))  # ghi chú tự động (vd bản nhập từ Cowork) có bản dịch; ghi chú người dùng giữ nguyên

    summary = rec["summary"]
    metrics = summary.get("metrics") or {}
    if metrics:
        cols = st.columns(min(len(metrics), 5))
        for i, (label, value) in enumerate(metrics.items()):
            cols[i % len(cols)].metric(t(label), t(value) if isinstance(value, str) else value)
    if summary.get("text"):
        st.markdown(summary["text"])
    tables = summary.get("tables") or {}
    if tables:
        for name, tab in zip(tables, st.tabs([t(n) for n in tables])):
            with tab:
                st.dataframe(common.df(tables[name]), hide_index=True, width="stretch")
    if rec["files"]:
        st.markdown(t("**File đính kèm**"))
        cols = st.columns(min(len(rec["files"]), 4))
        for i, f in enumerate(rec["files"]):
            name, content = store.get_file(f["id"])
            cols[i % len(cols)].download_button(f"⬇ {name} ({f['size'] // 1024 + 1} KB)", data=content, file_name=name,
                                                key=f"dl_{f['id']}")
    with st.expander(t("Dữ liệu gốc (JSON)")):
        st.json(summary, expanded=False)

    if auth.can_edit(rec):
        st.markdown(t("**Sửa bản ghi**"))
        with st.form(f"edit_{aid}"):
            title = st.text_input(t("Tiêu đề"), value=rec["title"])
            status = st.selectbox(t("Trạng thái"), list(store.STATUSES), index=list(store.STATUSES).index(rec["status"])
                                  if rec["status"] in store.STATUSES else 0, format_func=status_label)
            note = st.text_area(t("Ghi chú"), value=rec["note"] or "")
            if st.form_submit_button(t("💾 Lưu thay đổi"), type="primary"):
                store.update_activity(aid, auth.username(),
                                      title=title if title != rec["title"] else None,
                                      status=status if status != rec["status"] else None,
                                      note=note if note != (rec["note"] or "") else None)
                common.flash(t("Đã lưu thay đổi bản ghi #{aid}.", aid=aid))
                st.rerun()
        c1, c2 = st.columns(2)
        if not rec["deleted"]:
            sure = c1.checkbox(t("Xác nhận xoá bản ghi #{aid}", aid=aid), key=f"sure_{aid}")
            if c1.button(t("🗑 Xoá"), disabled=not sure, key=f"del_{aid}"):
                store.delete_activity(aid, auth.username())
                st.rerun()
        elif auth.is_admin() and c1.button(t("↩ Khôi phục"), key=f"restore_{aid}"):
            store.delete_activity(aid, auth.username(), restore=True)
            st.rerun()
    elif auth.can_run():
        st.caption(t("Chỉ người tạo hoặc admin mới sửa/xoá được bản ghi này."))
