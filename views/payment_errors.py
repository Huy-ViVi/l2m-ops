from pathlib import Path

import streamlit as st

from core import config
from core import payment_errors as pe
from core.ai import AIError
from core.i18n import t
from ui import auth, common

common.page_header(t("🧾 Case nạp lỗi"), t("Sheet CS → MyTool Search Order → master → file đền bù (Excel + CSV từng user)"))
settings = config.load_settings()


def _tr_rows(rows: list[dict]) -> list[dict]:
    """Lý do loại / mã sai là pe.Msg (giữ tiếng Việt trong file & lịch sử) -> dịch khi hiển thị."""
    return [{k: pe.tr(v) for k, v in r.items()} for r in rows]


@st.cache_data(show_spinner=False)
def _sheets(data: bytes) -> list[str]:
    return pe.list_sheets(data)


@st.cache_data(show_spinner=t("Đang đọc sheet CS..."))
def _cases(data: bytes, sheet: str, start: int, end: int | None, cols: tuple) -> list:
    return pe.read_cs(data, sheet, start, end, dict(cols))


@st.cache_data(show_spinner=t("Đang đọc file MyTool..."))
def _mytool(data: bytes, label: str) -> list[dict]:
    return pe.read_mytool_export(data, label)


SAMPLES = config.APP_ROOT / "tests" / "samples"
demo = (SAMPLES / "SAMPLE CS Escalation.xlsx").exists() and st.toggle(
    t("🧪 Chạy thử với dữ liệu mẫu (giả lập)"), key="pe_demo",
    help=t("Dùng 3 file mẫu trong tests/samples để xem toàn bộ quy trình. Không đụng tới master đang dùng."))

# ---- 1. Sheet CS ----------------------------------------------------------
st.subheader(t("1. Danh sách case từ CS"))
cs_file = None if demo else st.file_uploader(
    t("File CS escalation (.xlsx) — Google Sheet → Tệp → Tải xuống → Microsoft Excel"), type=["xlsx"], key="pe_cs")
cs_bytes = (SAMPLES / "SAMPLE CS Escalation.xlsx").read_bytes() if demo else (cs_file.getvalue() if cs_file else None)
cases: list[pe.CSCase] = []
if cs_bytes:
    data = cs_bytes
    sheets = common.guarded(t("Đọc danh sách tab của file CS"), _sheets, data)
    c1, c2, c3 = st.columns(3)
    sheet = c1.selectbox("Tab", sheets, index=sheets.index("Payment") if "Payment" in sheets else 0)
    start_row = c2.number_input(t("Đọc từ dòng"), min_value=2, value=2, step=1)
    end_row = c3.number_input(t("Đến dòng (0 = hết bảng)"), min_value=0, value=0, step=1)
    with st.expander(t("Cấu hình cột của sheet CS (mặc định theo template [NCV] - [L2M] Support Escalation)")):
        cc = st.columns(5)
        cols = {k: cc[i % 5].text_input(t(pe.CS_COLUMN_LABELS[k]), value=v, key=f"pe_col_{k}")
                for i, (k, v) in enumerate(pe.CS_COLUMNS.items())}
    try:
        cases = _cases(data, sheet, int(start_row), int(end_row) or None, tuple(cols.items()))
    except Exception as e:  # noqa: BLE001
        st.error(t("Không đọc được sheet CS: {error}", error=e))
    n_orders = sum(len(c.order_numbers) for c in cases)
    n_iap = sum(c.is_iap for c in cases)
    n_bad = sum(bool(c.bad_tokens) for c in cases)
    st.caption(t("{rows} dòng có dữ liệu · {orders} Order Number hợp lệ · {iap} dòng IAP · {bad} dòng có mã sai độ dài",
                 rows=len(cases), orders=n_orders, iap=n_iap, bad=n_bad))
    with st.expander(t("Xem dữ liệu CS đã đọc"), expanded=False):
        st.dataframe(common.df([{
            "Dòng": c.row, "Ticket": c.ticket, "User ID": c.user_id, "Server": c.server, "Account": c.account,
            "Nickname": c.nickname, "Provider": c.provider, "Order hợp lệ": ", ".join(c.order_numbers),
            "Mã sai": ", ".join(pe.tr(b) for b in c.bad_tokens),
        } for c in cases]), hide_index=True, width="stretch")

# ---- 2. MyTool ------------------------------------------------------------
st.subheader(t("2. Dữ liệu MyTool Search Order"))
all_orders = list(dict.fromkeys(o for c in cases if not c.is_iap for o in c.order_numbers))
tab_auto, tab_upload = st.tabs([t("Tự tra bằng trình duyệt"), t("Tải file Export Excel")])
with tab_auto:
    if common.automation_notice():
        common.reachability_warning(common.game()["mytool_search_order"]["SEA"], "MyTool")
        shops = st.multiselect(t("Shop cần tra"), ["SEA", "VN"], default=["SEA", "VN"],
                               help=t("Cột Country của CS không quyết định shop — tra cả hai cho chắc."))
        if st.button(t("Tra {n} Order Number & Export Excel", n=len(all_orders)), disabled=not all_orders, type="primary"):
            res = common.run_job("mytool_orders", {"orders": all_orders, "shops": shops}, t("Đang tra MyTool"))
            if res and res.get("ok"):
                st.session_state["pe_auto_files"] = [r["file"] for r in res["results"] if r.get("file")]
        for f in st.session_state.get("pe_auto_files", []):
            st.caption(f"✓ {Path(f).name}")
with tab_upload:
    uploads = st.file_uploader(t("File `<AppAlias>-orders.xlsx` (có thể chọn nhiều file: SEA + VN)"), type=["xlsx"],
                               accept_multiple_files=True, key="pe_mytool")

mytool_rows: list[dict] = []
if demo:
    mytool_rows += _mytool((SAMPLES / "SAMPLE JVL2M_SEA-orders.xlsx").read_bytes(), "SAMPLE")
for f in st.session_state.get("pe_auto_files", []):
    if Path(f).exists():
        try:
            mytool_rows += _mytool(Path(f).read_bytes(), Path(f).name)
        except Exception as e:  # noqa: BLE001
            st.error(f"{Path(f).name}: {e}")
for up in uploads or []:
    try:
        mytool_rows += _mytool(up.getvalue(), up.name)
    except Exception as e:  # noqa: BLE001
        st.error(f"{up.name}: {e}")
if mytool_rows:
    n_err = sum(pe.is_server_error(r.get("DeliveryStatus", "")) for r in mytool_rows)
    st.caption(t("{orders} order trong file MyTool · {errors} order DELIVERY_SERVER_ERROR", orders=len(mytool_rows), errors=n_err))

# ---- 3. Master ------------------------------------------------------------
st.subheader("3. Master All Product Information")
if demo:
    master = common.load_master_path(SAMPLES / "SAMPLE All Product Information.xlsx")
    st.caption(t("Đang dùng master mẫu."))
else:
    master = common.master_widget("pe")

# ---- 4. Đối chiếu -----------------------------------------------------------
st.subheader(t("4. Kết quả đối chiếu"))
if not cases or not mytool_rows:
    st.info(t("Cần sheet CS (bước 1) và dữ liệu MyTool (bước 2) để đối chiếu."))
    st.stop()
if master is None:
    st.warning(t("Chưa có master — cột Diamonds sẽ phải nhập tay."))

overrides = st.session_state.setdefault("pe_diamonds", {})
missing = common.guarded(t("Đối chiếu CS × MyTool × master"), pe.build_result, cases, mytool_rows, master).missing_diamonds()
if missing:
    st.warning(t("Thiếu Diamonds cho {n} gói — nhập tay (thường do master cũ chưa có gói mới).", n=len(missing)))
    cols = st.columns(min(len(missing), 4))
    for i, pid in enumerate(missing):
        value = cols[i % 4].number_input(t("Diamonds / gói — {package}", package=pid), min_value=0, step=1,
                                         value=overrides.get(pid), key=f"pe_dia_{pid}")
        if value is None:
            overrides.pop(pid, None)
        else:
            overrides[pid] = int(value)
res = common.guarded(t("Đối chiếu CS × MyTool × master"), pe.build_result, cases, mytool_rows, master, overrides)

groups = res.groups()
n_warn = len(res.warnings) + len(res.master_notes)
m1, m2, m3, m4 = st.columns(4)
m1.metric(t("Order lỗi thật"), len(res.lines))
m2.metric(t("User cần đền bù"), len(groups))
m3.metric(t("Case bị loại"), len(res.excluded))
m4.metric(t("Cảnh báo"), n_warn)

t_users, t_pkg, t_ex, t_warn, t_extra = st.tabs(
    ["Users List", "Packages List", t("Bị loại ({n})", n=len(res.excluded)),
     t("Cảnh báo ({n})", n=n_warn), t("Order dư trên MyTool ({n})", n=len(res.extra_errors))])
with t_users:
    st.dataframe(common.df([{
        "Game Account ID": g.user_id, "Account Number": g.account, "Server": g.server, "Nickname": g.nickname,
        "Transaction ID": l.app_trans_id, "Package": l.product_id, "Qty": l.quantity,
        "Diamonds/gói": l.diamonds, "Total Diamond (user)": g.total_diamonds, "CSV": g.csv_name,
    } for g in groups for l in g.lines]), hide_index=True, width="stretch")
with t_pkg:
    st.dataframe(common.df(res.packages()), hide_index=True, width="stretch")
with t_ex:
    st.dataframe(common.df(_tr_rows(res.excluded)), hide_index=True, width="stretch")
with t_warn:
    for w in res.warnings:
        st.write("⚠ " + pe.tr(w))
    for n in res.master_notes:
        st.write("📘 " + pe.tr(n))
    if not res.warnings and not res.master_notes:
        st.write(t("Không có cảnh báo."))
with t_extra:
    st.caption(t("Theo rule: KHÔNG tự thêm vào file. Hỏi lại CS/user trước, mặc định bám danh sách CS."))
    st.dataframe(common.df(res.extra_errors), hide_index=True, width="stretch")

st.markdown(t("**Checklist audit trước khi giao**"))
audit = res.audit()
for ok, msg in audit:
    st.write(("✅ " if ok else "❌ ") + pe.tr(msg))

# ---- 5. Xuất file -----------------------------------------------------------
# File Payment Error Case + CSV là định dạng cố định giao CS/NC: không đổi theo ngôn ngữ giao diện.
st.subheader(t("5. Xuất file"))
day = st.date_input(t("Ngày của đợt xử lý"), value=config.today(), format="DD/MM/YYYY")
if not res.lines:
    st.info(t("Không có order lỗi thật nào để xuất."))
else:
    files = pe.planned_files(res, day)
    st.caption(t("{n} file: ", n=len(files)) + ", ".join(files[:6]) + (" ..." if len(files) > 6 else ""))
    zip_bytes = common.guarded(t("Tạo file Excel/CSV"), pe.build_zip, res, day)
    c1, c2 = st.columns(2)
    c1.download_button(t("⬇ Tải ZIP (Excel + CSV)"), data=zip_bytes,
                       file_name=f"Payment-Error-Cases-{day:%Y-%m-%d}.zip", mime="application/zip", type="primary")
    if auth.can_run() and auth.is_host_request():  # ghi vào ổ đĩa của máy chạy app
        folder = pe.output_folder(settings["output_root"], day, common.game()["id"])
        existing = [f for f in files if (folder / f).exists()]
        with c2:
            st.caption(t("Lưu vào `{folder}`", folder=folder))
            confirm = True
            if existing:
                confirm = st.checkbox(t("Ghi đè {n} file đã có ({names}...)", n=len(existing), names=", ".join(existing[:3])),
                                      key="pe_overwrite")
            if st.button(t("💾 Lưu vào thư mục"), disabled=not confirm):
                written = pe.save_to_folder(res, settings["output_root"], day, common.game()["id"])
                st.success(t("Đã lưu {n} file vào {folder}", n=len(written), folder=folder))

# ---- 6. Tóm tắt bằng AI -----------------------------------------------------
with st.expander(t("🤖 Viết tóm tắt đợt xử lý bằng AI (để báo cáo / gửi team)")):
    st.caption(t("Gửi lên AI: nickname, server, số order, Product ID, lý do loại. Không gửi Account Number hay Game Account ID."))
    if st.button(t("Viết tóm tắt")):
        ai = common.ai_client()
        if ai:
            try:
                with st.spinner(t("Đang gọi {ai}...", ai=ai.label)):
                    st.session_state["pe_summary"] = ai.text(
                        pe.summary_system(common.game()["name"]), pe.summary_prompt(res, common.game()["name"]), effort="low")
            except AIError as e:
                st.error(str(e))
    if st.session_state.get("pe_summary"):
        st.markdown(st.session_state["pe_summary"])

# ---- 7. Lưu lịch sử -----------------------------------------------------------
# Khoá metrics/bảng giữ tiếng Việt (dữ liệu lưu), trang Lịch sử dịch khi hiển thị.
if res.lines:
    common.record_button(
        t("📌 Lưu đợt này vào lịch sử"), "payment_errors",
        t("{sample}Case nạp lỗi {day} — {users} user, {orders} order", sample=t("[MẪU] ") if demo else "",
          day=f"{day:%d/%m/%Y}", users=len(groups), orders=len(res.lines)),
        {
            "metrics": {"Dòng CS": len(res.cases), "Order lỗi": len(res.lines), "User đền bù": len(groups),
                        "Bị loại": len(res.excluded), "Cảnh báo": n_warn},
            "text": st.session_state.get("pe_summary", ""),
            "tables": {
                "Users List": [{"Game Account ID": g.user_id, "Account Number": g.account, "Server": g.server,
                                "Nickname": g.nickname, "Transaction IDs": ", ".join(l.app_trans_id for l in g.lines),
                                "Packages": ", ".join(l.product_id for l in g.lines), "Total Diamond": g.total_diamonds}
                               for g in groups],
                "Bị loại": res.excluded,
                "Cảnh báo": [{"Nội dung": w} for w in res.warnings + res.master_notes],
                "Order dư trên MyTool": res.extra_errors,
                "Checklist": [{"Kết quả": "✅" if ok else "❌", "Kiểm tra": msg} for ok, msg in res.audit()],
            },
        },
        {pe.excel_name(day): pe.write_excel(res), f"Payment-Error-Cases-{day:%Y-%m-%d}.zip": zip_bytes},
        key="pe_rec",
    )
