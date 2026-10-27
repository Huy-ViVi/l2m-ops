import re
from datetime import date

import streamlit as st

from core import config
from core import webshop_audit as wa
from core.ai import AIError
from core.i18n import t
from core.master import MARKETS, short_key
from ui import common

common.page_header(t("🔎 Kiểm tra gói nạp trên webshop VNG"),
                   t("MyTool Sold Package (6 shop LIVE) so với master: giá, thời gian bán, tên, trạng thái"))
settings = config.load_settings()
g = common.game()

master = common.master_widget("wa")
if master is None:
    st.stop()

# Bảng nhập/sửa đọc lại theo tên cột tiếng Việt -> không dịch tên cột, chỉ đặt nhãn hiển thị.
EDITOR_LABELS = {
    "Tên gói": st.column_config.TextColumn(t("Tên gói")),
    "Giá": st.column_config.NumberColumn(t("Giá"), format="%.2f"),
    "Từ": st.column_config.TextColumn(t("Từ"), help="HH:MM DD/MM/YYYY"),
    "Đến": st.column_config.TextColumn(t("Đến"), help="HH:MM DD/MM/YYYY"),
    "Trạng thái": st.column_config.SelectboxColumn(t("Trạng thái"), options=["", "on", "off"]),
}
CHECK_TYPES = {"new": "Gói mới được thêm", "retime": "Gói cũ đổi thời gian bán"}

# ---- 1. Gói cần check ------------------------------------------------------------
st.subheader(t("1. Gói cần check"))
c1, c2 = st.columns([2, 1])
raw = c1.text_area(t("Package ID / Product Key (mỗi dòng 1 ID)"), height=120, key="wa_ids",
                   help=t("web.itemXXX → check cả 6 shop · web.sa.* → 5 shop SEA · web.vn.* → chỉ VN"))
check_type = c2.radio(t("Loại check"), list(CHECK_TYPES), key="wa_check_type", format_func=lambda c: t(CHECK_TYPES[c]))
pids = list(dict.fromkeys(short_key(x) for x in re.split(r"[\s,;]+", raw or "") if x.strip()))
if not pids:
    st.info(t("Nhập ít nhất một Package ID."))
    st.stop()

sig = (g["id"], tuple(pids), (common.master_meta() or {}).get("uploaded_at"))
if st.session_state.get("wa_sig") != sig:
    expected, warns = wa.expected_rows(master, pids)
    st.session_state.update(wa_sig=sig, wa_expected=expected, wa_warns=warns, wa_actual=None, wa_results=None)
for w in st.session_state["wa_warns"]:
    st.warning(w)

# ---- 2. Giá trị kỳ vọng ----------------------------------------------------------
st.subheader(t("2. Giá trị đúng theo master"))
st.caption(t("Giá lấy từ sheet Webshop. Thời gian bán: điền tay hoặc để AI đọc sheet Timeline Selling (từ dòng 121), rồi duyệt lại."))
if st.button(t("🤖 AI đọc Timeline Selling"), disabled=not master.timeline):
    ai = common.ai_client()
    if ai:
        try:
            with st.spinner(t("{ai} đang đọc {n} dòng Timeline Selling...", ai=ai.label, n=len(master.timeline))):
                entries = wa.ai_extract_timeline(ai, master, pids, game_name=g["name"])
            st.session_state["wa_expected"] = wa.apply_timeline(st.session_state["wa_expected"], entries)
            st.session_state["wa_timeline"] = entries
            st.session_state.pop("wa_exp_editor", None)
        except AIError as e:
            st.error(str(e))
if st.session_state.get("wa_timeline"):
    with st.expander(t("AI đã đọc được (đối chiếu với dòng nguồn trước khi tin)")):
        st.dataframe(common.df(st.session_state["wa_timeline"]), hide_index=True, width="stretch")

expected_df = st.data_editor(
    common.df(st.session_state["wa_expected"], translate=False), key="wa_exp_editor", hide_index=True, width="stretch",
    disabled=["Package ID", "Shop"], column_config=EDITOR_LABELS,
)
expected = common.records(expected_df)
if check_type == "retime":
    # Gói cũ: chỉ so thời gian bán (và trạng thái nếu có điền), bỏ qua giá/tên.
    expected = [{**e, "Giá": None, "Tên gói": ""} for e in expected]

# ---- 3. Dữ liệu trên MyTool ------------------------------------------------------
st.subheader(t("3. Dữ liệu đang setup trên MyTool"))
tab_auto, tab_manual = st.tabs([t("Đọc MyTool tự động"), t("Nhập tay / dán")])
with tab_auto:
    if common.automation_notice():
        urls = g["mytool_sold_package"]
        common.reachability_warning(next((u for u in urls.values() if u), ""), "MyTool")
        missing_urls = [m for m in MARKETS if not urls.get(m)]
        if missing_urls:
            st.warning(t("{game}: chưa cấu hình URL Sold Package cho {markets} (Cài đặt → Game).",
                         game=g["name"], markets=", ".join(missing_urls)))
        if st.button(t("Đọc Sold Package trên các shop"), type="primary"):
            res = common.run_job("mytool_sold", {"package_ids": pids}, t("Đang đọc MyTool"))
            if res and res.get("ok"):
                actual = []
                for r in res["results"]:
                    parsed = wa.parse_mytool_row(r.get("_raw", {}))
                    actual.append({"Package ID": r["Package ID"], "Shop": r["Shop"], **parsed,
                                   "_not_found": r.get("_not_found", False)})
                st.session_state["wa_actual"] = actual
                st.session_state["wa_raw"] = res["results"]
        if st.session_state.get("wa_raw"):
            with st.expander(t("Dữ liệu thô đọc từ MyTool")):
                st.dataframe(common.df([{"Package ID": r["Package ID"], "Shop": r["Shop"], **r.get("_raw", {})}
                                        for r in st.session_state["wa_raw"]]), width="stretch")
with tab_manual:
    base_rows = st.session_state.get("wa_actual") or [
        {"Package ID": e["Package ID"], "Shop": e["Shop"], "Tên gói": "", "Giá": None, "Từ": "", "Đến": "", "Trạng thái": "",
         "_not_found": False} for e in st.session_state["wa_expected"]]
    manual_df = st.data_editor(common.df(base_rows, translate=False), key="wa_act_editor", hide_index=True, width="stretch",
                               disabled=["Package ID", "Shop"],
                               column_config={**EDITOR_LABELS, "_not_found": st.column_config.CheckboxColumn(t("Không tìm thấy"))})
    if st.button(t("Dùng dữ liệu nhập tay")):
        st.session_state["wa_actual"] = common.records(manual_df)

# ---- 4. Kết quả ------------------------------------------------------------------
st.subheader(t("4. Kết quả"))
actual = st.session_state.get("wa_actual")
if not actual:
    st.info(t("Cần dữ liệu MyTool (bước 3)."))
    st.stop()
results = wa.compare(expected, actual)
errors = [r for r in results if r["Kết quả"].startswith("❌")]
m1, m2, m3 = st.columns(3)
m1.metric(t("Gói"), len(pids))
m2.metric(t("Điểm kiểm tra"), len(results))
m3.metric(t("Sai"), len(errors))
only_err = st.toggle(t("Chỉ hiện dòng sai"), value=bool(errors))
st.dataframe(common.df(errors if only_err else results), hide_index=True, width="stretch")
report = wa.report_markdown(results, date.today(), g["name"])
c1, c2 = st.columns(2)
c1.download_button(t("⬇ Tải báo cáo Excel"), data=wa.report_excel(results),
                   file_name=f"Webshop-Audit-{date.today():%Y-%m-%d}.xlsx", type="primary")
c2.download_button(t("⬇ Tải báo cáo Markdown"), data=report.encode("utf-8"),
                   file_name=f"Webshop-Audit-{date.today():%Y-%m-%d}.md")
with st.expander(t("Báo cáo dạng text (copy gửi team)")):
    st.code(report, language=None)
if errors:
    st.warning(t("Có sai lệch. Theo rule, app không tự sửa trên MyTool — hãy sửa tay hoặc xác nhận với team trước khi thay đổi."))

# Khoá metrics/bảng giữ tiếng Việt (dữ liệu lưu), trang Lịch sử dịch khi hiển thị.
common.record_button(
    t("📌 Lưu báo cáo vào lịch sử"), "webshop_audit",
    t("Kiểm tra webshop {day} — {packages} gói, {errors} lỗi ({check_type})", day=f"{date.today():%d/%m/%Y}",
      packages=len(pids), errors=len(errors), check_type=t(CHECK_TYPES[check_type]).lower()),
    {"metrics": {"Gói": len(pids), "Điểm kiểm tra": len(results), "Sai": len(errors)},
     "tables": {"Dòng sai": errors, "Toàn bộ": results}, "package_ids": pids},
    {f"Webshop-Audit-{date.today():%Y-%m-%d}.xlsx": wa.report_excel(results),
     f"Webshop-Audit-{date.today():%Y-%m-%d}.md": report.encode("utf-8")},
    key="wa_rec",
)
