import hashlib
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


st.info(t("**Thông báo cho cả team** — nền tảng đã nhận plugin (phase 1: đưa app của mọi người lên), làm bằng **AI nào cũng được** "
          "(ChatGPT, Gemini, Copilot, Claude, Cursor…).  \n"
          "1. Tab **Bắt đầu**: tải **AI_PROMPT.md**, đưa cho AI của bạn kèm mô tả app.  \n"
          "2. Tab **Kiểm tra & gửi**: dán câu trả lời của AI để kiểm tra; đạt thì gửi cho admin.\n\n"
          "Quy định đầy đủ ở tab *Quy định*, các bước tiếp theo của cả team ở tab *Lộ trình*."),
        icon=":material/campaign:")

tab_start, tab_submit, tab_list, tab_rules, tab_road = st.tabs(
    [t("Bắt đầu"), t("Kiểm tra & gửi"), t("Danh sách plugin"), t("Quy định (PLUGIN_GUIDE.md)"), t("Lộ trình")])


@st.cache_data(show_spinner=False, max_entries=2)
def _prompt(_version: str) -> str:
    return bundle.ai_prompt()


@st.cache_data(show_spinner=False, max_entries=2)
def _starter(_version: str) -> bytes:
    return bundle.starter_zip()


def _doc(name: str) -> None:
    path = config.APP_ROOT / name
    if not path.is_file():
        st.warning(t("Chưa có file {file}.", file=name))
        return
    if st.session_state.get("lang", "vi") == "vi":
        st.caption(t("Tài liệu viết bằng tiếng Anh để cả team, kể cả thành viên nước ngoài, cùng đọc."))
    # Khối ``` hiện bằng st.code (có nút sao chép, giữ nguyên văn); phần chữ bằng st.markdown.
    parts = re.split(r"^```(\w*)\n(.*?)^```[ \t]*$", path.read_text(encoding="utf-8"), flags=re.M | re.S)
    for i in range(0, len(parts), 3):
        if parts[i].strip():
            st.markdown(_plain(parts[i]))
        if i + 2 < len(parts):
            st.code(parts[i + 2].rstrip("\n"), language=parts[i + 1] or None)


with tab_start:
    prompt = _prompt(bundle.code_version())
    c1, c2 = st.columns([2, 3], vertical_alignment="center")
    c1.download_button(t("⬇ Tải AI_PROMPT.md"), data=prompt.encode("utf-8"), file_name=bundle.PROMPT_FILE,
                       mime="text/markdown", type="primary", key="plugins_prompt_dl")
    c2.caption(t("Một file cho mọi AI: quy định, công cụ của nền tảng, plugin mẫu và cách trả lời để nền tảng tự tách file. "
                 "Đính kèm vào AI (hoặc dán toàn bộ nội dung), rồi mô tả app của bạn."))
    with st.expander(t("Xem / sao chép toàn bộ prompt ({n} ký tự)", n=f"{len(prompt):,}")):
        st.code(prompt, language="markdown")
    _doc("PLUGIN_QUICKSTART.md")


def _check(source: str, marker: str, build) -> dict:
    """Kiểm tra một lần cho mỗi nội dung (trang chạy lại không kiểm tra lại). source: 'text' | 'zip' — mỗi ô một kết quả."""
    key = f"plugins_checked_{source}"
    checked = st.session_state.get(key)
    if not checked or checked["marker"] != marker:
        data, extra, files = build()
        result = plugins.validate_zip(data) if data else None
        checked = {"marker": marker, "source": source, "data": data, "extra": extra, "files": files, "result": result}
        st.session_state[key] = checked
    return checked


def _show(checked: dict) -> None:
    k = checked["source"]
    result: plugins.Plugin | None = checked["result"]
    problems = checked["extra"] + (result.problems if result else [])
    if checked["files"]:
        st.caption(t("Đã đọc {n} file: {files}", n=len(checked["files"]), files=", ".join(f"`{f}`" for f in checked["files"])))
    if result and not problems:
        st.success(t("✅ Plugin **{name}** (`{id}` v{version}) đạt quy định — {n} trang.",
                     name=result.label, id=result.id, version=result.version, n=len(result.pages)))
        st.download_button(t("⬇ Tải plugin (.zip) để chạy thử trên máy"), data=checked["data"],
                           file_name=f"{result.id}-{result.version}.zip", mime="application/zip", key=f"plugins_result_dl_{k}")
        st.markdown(t("**Gửi** — gửi cho admin ngay dưới đây; hoặc nếu bạn đã được thêm vào kho code, đưa thư mục vào đúng chỗ "
                      "`plugins/{id}/`.", id=result.id))
        if auth.can_run():
            note = st.text_area(t("Ghi chú cho admin (đổi gì, cần thêm thư viện / secret gì)"), key=f"plugins_submit_note_{k}")
            if st.button(t("📤 Gửi plugin cho admin"), type="primary", key=f"plugins_submit_{k}"):
                aid, _ = common.record(
                    "plugin_submit", t("Gửi plugin {id} v{version}", id=result.id, version=result.version),
                    {"plugin": result.id, "version": result.version, "owners": result.owners, "pages": len(result.pages)},
                    {f"{result.id}-{result.version}.zip": checked["data"]}, note=note, status="need_check")
                st.success(t("Đã gửi (bản ghi #{aid} ở trang Lịch sử hoạt động, loại Gửi plugin). Admin sẽ đưa lên.", aid=aid))
    else:
        st.error(t("Plugin chưa đạt — {n} điểm cần sửa. Sao chép danh sách dưới, gửi lại cho AI: "
                   "\"Công cụ kiểm tra báo các lỗi sau, sửa hết và trả lại toàn bộ file:\"", n=len(problems)))
        st.code("\n".join(f"- {p}" for p in problems), language=None)


with tab_submit:
    st.markdown(t("**Dán câu trả lời của AI** (AI dạng chat) — dán toàn bộ, từ đầu tới dòng END OF FILES. App chỉ đọc code, không chạy."))
    text = st.text_area(t("Dán câu trả lời của AI"), height=240, key="plugins_ai_text", label_visibility="collapsed",
                        placeholder="FILE: plugins/<id>/plugin.toml\n```toml\n…\n```\nFILE: plugins/<id>/page.py\n```python\n…\n```")
    if st.button(t("🔍 Kiểm tra"), key="plugins_ai_check", disabled=not text.strip()):
        def _from_text():
            pid, files, extra = plugins.files_from_text(text)
            return (plugins.zip_plugin(pid, files) if files else None), extra, sorted(files)
        _check("text", hashlib.sha1(text.encode("utf-8")).hexdigest(), _from_text)
    if st.session_state.get("plugins_checked_text"):
        _show(st.session_state["plugins_checked_text"])

    st.divider()
    st.markdown(t("**Hoặc tải lên file .zip** của thư mục plugin (thư mục có plugin.toml) — khi làm bằng Bộ khởi đầu / AI làm việc trên thư mục."))
    up = st.file_uploader(t("File .zip của plugin"), type=["zip"], key="plugins_check_zip")
    if up is not None:
        _show(_check("zip", f"{up.name}:{up.size}", lambda: (up.getvalue(), [], [])))

    st.divider()
    st.markdown(t("**Bộ khởi đầu** — chạy thử plugin trên máy bạn (run.bat), tách câu trả lời của AI thành file (make-plugin.bat), "
                  "dùng với AI làm việc trên thư mục (Cursor, Claude Code, Copilot, Codex, Gemini CLI). "
                  "Không chứa địa chỉ CSDL hay dữ liệu của team."))
    st.download_button(t("⬇ Tải bộ khởi đầu làm plugin (.zip)"), data=_starter(bundle.code_version()),
                       file_name="l2m-ops-plugin-starter.zip", mime="application/zip", key="plugins_starter")
    if auth.is_admin():
        st.caption(t("Admin: plugin gửi lên nằm ở trang Lịch sử hoạt động (loại Gửi plugin) — tải zip, kiểm tra, rồi đưa thư mục "
                     "vào plugins/<id>/ trên GitHub."))

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

with tab_rules:
    _doc("PLUGIN_GUIDE.md")
with tab_road:
    _doc("ROADMAP.md")
