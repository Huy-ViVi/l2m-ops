import re

import streamlit as st

from core import bundle, config, plugins, store
from core.i18n import t
from ui import auth, common

common.page_header(t("🧩 Plugin của team"),
                   t("Mỗi tính năng của thành viên là một plugin trên nền tảng này — cùng đăng nhập, cùng dữ liệu, cùng menu."))


def _plain(text: str) -> str:
    """Giữ nguyên chữ ':material/…:' (st.markdown tự đổi chuỗi này thành icon)."""
    return text.replace(":material/", ":material\\/")


st.info(t("**Thông báo cho cả team** — nền tảng đã nhận plugin (phase 1: đưa app của mọi người lên).  \n"
          "1. Trước khi build / chuyển app của bạn: tải **Bộ khởi đầu** ở tab *Đưa plugin lên*.  \n"
          "2. Đưa AI của bạn đọc **AGENTS.md** và **PLUGIN_GUIDE.md** trong bộ đó, để nó tự làm theo quy định.  \n"
          "3. Chạy thử trên máy, tự kiểm tra, rồi gửi. Quy định đầy đủ ở tab *Quy định*, các bước tiếp theo ở tab *Lộ trình*."),
        icon=":material/campaign:")

tab_list, tab_submit, tab_rules, tab_road = st.tabs(
    [t("Danh sách plugin"), t("Đưa plugin lên"), t("Quy định (PLUGIN_GUIDE.md)"), t("Lộ trình")])

with tab_list:
    found = plugins.discover(check_code=True)
    counts: dict[str, int] = {}
    for r in store.plugin_stats():
        counts[r["plugin"]] = counts.get(r["plugin"], 0) + r["n"]
    if not found:
        st.caption(t("Chưa có plugin nào. Plugin đầu tiên sẽ hiện ở đây và ở menu bên trái."))
    else:
        st.dataframe(common.df([{
            "Plugin": p.label, "Mã": p.id, "Phụ trách": ", ".join(p.owners), "Phiên bản": p.version,
            "Nhóm menu": p.section, "Bản ghi đã lưu": counts.get(p.id, 0),
            "Trạng thái": t("✅ Đang chạy") if p.ok else t("⚠️ {n} lỗi — chưa lên menu", n=len(p.problems)),
            "Mô tả": p.description,
        } for p in found]), hide_index=True, width="stretch")
        for p in found:
            if p.problems:
                with st.expander(t("⚠️ {name} — {n} lỗi cần sửa", name=p.label, n=len(p.problems))):
                    for problem in p.problems:
                        st.markdown("- " + _plain(problem))
    st.caption(t("Plugin lỗi khai báo (plugin.toml) hoặc vi phạm quy định không được đưa lên menu cho tới khi sửa xong; "
                 "plugin lỗi khi chạy chỉ báo lỗi ở trang của nó, phần còn lại vẫn dùng bình thường."))


@st.cache_data(show_spinner=False, max_entries=2)
def _starter(_version: str) -> bytes:
    return bundle.starter_zip()


with tab_submit:
    st.markdown(t("**1. Tải bộ khởi đầu** — code nền tảng chạy được trên máy bạn, plugin mẫu, quy định và hướng dẫn cho AI. "
                  "Không chứa địa chỉ CSDL hay dữ liệu của team."))
    st.download_button(t("⬇ Tải bộ khởi đầu làm plugin (.zip)"), data=_starter(bundle.code_version()),
                       file_name="l2m-ops-plugin-starter.zip", mime="application/zip", key="plugins_starter")
    st.markdown(t("**2. Làm plugin** theo file BAT-DAU-LAM-PLUGIN.txt trong bộ đó (chép plugin mẫu, nhờ AI viết, chạy thử bằng run.bat)."))
    st.markdown(t("**3. Tự kiểm tra** — nén thư mục plugin của bạn (thư mục có plugin.toml) thành .zip rồi tải lên đây. "
                  "App chỉ đọc code, không chạy."))
    up = st.file_uploader(t("File .zip của plugin"), type=["zip"], key="plugins_check_zip")
    if up is not None:
        marker = f"{up.name}:{up.size}"
        if st.session_state.get("plugins_checked", {}).get("marker") != marker:
            data = up.getvalue()
            st.session_state["plugins_checked"] = {"marker": marker, "data": data, "result": plugins.validate_zip(data)}
        checked = st.session_state["plugins_checked"]
        result: plugins.Plugin = checked["result"]
        if result.ok:
            st.success(t("✅ Plugin **{name}** (`{id}` v{version}) đạt quy định — {n} trang.",
                         name=result.label, id=result.id, version=result.version, n=len(result.pages)))
            st.markdown(t("**4. Gửi** — đưa thư mục lên GitHub vào đúng chỗ `plugins/{id}/` (nếu bạn đã được thêm vào kho), "
                          "hoặc gửi zip cho admin ngay dưới đây.", id=result.id))
            if auth.can_run():
                note = st.text_area(t("Ghi chú cho admin (đổi gì, cần thêm thư viện / secret gì)"), key="plugins_submit_note")
                if st.button(t("📤 Gửi plugin cho admin"), type="primary", key="plugins_submit"):
                    aid, _ = common.record(
                        "plugin_submit", t("Gửi plugin {id} v{version}", id=result.id, version=result.version),
                        {"plugin": result.id, "version": result.version, "owners": result.owners, "pages": len(result.pages)},
                        {f"{result.id}-{result.version}.zip": checked["data"]}, note=note, status="need_check")
                    st.success(t("Đã gửi (bản ghi #{aid} ở trang Lịch sử hoạt động, loại Gửi plugin). Admin sẽ đưa lên.", aid=aid))
        else:
            st.error(t("Plugin chưa đạt — {n} điểm cần sửa:", n=len(result.problems)))
            for problem in result.problems:
                st.markdown("- " + _plain(problem))
    if auth.is_admin():
        st.caption(t("Admin: plugin gửi lên nằm ở trang Lịch sử hoạt động (loại Gửi plugin) — tải zip, kiểm tra, rồi đưa thư mục "
                     "vào plugins/<id>/ trên GitHub."))


def _doc(name: str) -> None:
    path = config.APP_ROOT / name
    if not path.is_file():
        st.warning(t("Chưa có file {file}.", file=name))
        return
    if st.session_state.get("lang", "vi") != "vi":
        st.caption(t("Tài liệu này viết bằng tiếng Việt."))
    # Khối ``` hiện bằng st.code (chép được nguyên văn); phần chữ bằng st.markdown.
    parts = re.split(r"^```(\w*)\n(.*?)^```[ \t]*$", path.read_text(encoding="utf-8"), flags=re.M | re.S)
    for i in range(0, len(parts), 3):
        if parts[i].strip():
            st.markdown(_plain(parts[i]))
        if i + 2 < len(parts):
            st.code(parts[i + 2].rstrip("\n"), language=parts[i + 1] or None)


with tab_rules:
    _doc("PLUGIN_GUIDE.md")
with tab_road:
    _doc("ROADMAP.md")
