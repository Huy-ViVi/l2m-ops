"""Bản dịch tiếng Anh — kiểm tra webshop VNG (views/webshop_audit.py, core/webshop_audit.py), đọc master (core/master.py),
automation MyTool (automation/mytool.py)."""

EN = {
    # views/webshop_audit.py
    "🔎 Kiểm tra gói nạp trên webshop VNG": "🔎 VNG webshop package check",
    "MyTool Sold Package (6 shop LIVE) so với master: giá, thời gian bán, tên, trạng thái":
        "MyTool Sold Package (6 LIVE shops) vs master: price, sale period, name, status",
    "Gói mới được thêm": "Newly added packages",
    "Gói cũ đổi thời gian bán": "Existing packages with a new sale period",
    "1. Gói cần check": "1. Packages to check",
    "Package ID / Product Key (mỗi dòng 1 ID)": "Package ID / Product Key (one ID per line)",
    "web.itemXXX → check cả 6 shop · web.sa.* → 5 shop SEA · web.vn.* → chỉ VN":
        "web.itemXXX → all 6 shops · web.sa.* → 5 SEA shops · web.vn.* → VN only",
    "Loại check": "Check type",
    "Nhập ít nhất một Package ID.": "Enter at least one Package ID.",
    "2. Giá trị đúng theo master": "2. Expected values from the master",
    "Giá lấy từ sheet Webshop. Thời gian bán: điền tay hoặc để AI đọc sheet Timeline Selling (từ dòng 121), rồi duyệt lại.":
        "Prices come from the Webshop sheet. Sale period: fill it in by hand or let AI read the Timeline Selling sheet "
        "(from row 121), then review.",
    "🤖 AI đọc Timeline Selling": "🤖 AI reads Timeline Selling",
    "{ai} đang đọc {n} dòng Timeline Selling...": "{ai} is reading {n} Timeline Selling rows...",
    "AI đã đọc được (đối chiếu với dòng nguồn trước khi tin)": "What AI read (check against the source rows before trusting it)",
    "3. Dữ liệu đang setup trên MyTool": "3. Current setup on MyTool",
    "Đọc MyTool tự động": "Read MyTool automatically",
    "Nhập tay / dán": "Enter / paste by hand",
    "{game}: chưa cấu hình URL Sold Package cho {markets} (Cài đặt → Game).":
        "{game}: no Sold Package URL configured for {markets} (Settings → Game).",
    "Đọc Sold Package trên các shop": "Read Sold Package on every shop",
    "Đang đọc MyTool": "Reading MyTool",
    "Dữ liệu thô đọc từ MyTool": "Raw data read from MyTool",
    "Không tìm thấy": "Not found",
    "Dùng dữ liệu nhập tay": "Use the manual data",
    "4. Kết quả": "4. Results",
    "Cần dữ liệu MyTool (bước 3).": "MyTool data is needed (step 3).",
    "Điểm kiểm tra": "Checkpoints",
    "Sai": "Mismatches",
    "Chỉ hiện dòng sai": "Show mismatches only",
    "⬇ Tải báo cáo Excel": "⬇ Download Excel report",
    "⬇ Tải báo cáo Markdown": "⬇ Download Markdown report",
    "Báo cáo dạng text (copy gửi team)": "Text report (copy to send to the team)",
    "Có sai lệch. Theo rule, app không tự sửa trên MyTool — hãy sửa tay hoặc xác nhận với team trước khi thay đổi.":
        "There are mismatches. By rule the app never edits MyTool itself — fix them by hand or confirm with the team before changing anything.",
    "📌 Lưu báo cáo vào lịch sử": "📌 Save report to history",
    "Kiểm tra webshop {day} — {packages} gói, {errors} lỗi ({check_type})":
        "Webshop check {day} — {packages} packages, {errors} errors ({check_type})",
    "Dòng sai": "Mismatched rows",
    "Toàn bộ": "All",
    # Khoá / nhãn trong kết quả so sánh (dữ liệu giữ tiếng Việt, dịch khi hiển thị và trong báo cáo)
    "Tên gói": "Package name",
    "Giá": "Price",
    "Từ": "From",
    "Đến": "To",
    "Trường": "Field",
    "Giá bán": "Selling price",
    "Thời gian từ": "Start time",
    "Thời gian đến": "End time",
    "có bán": "on sale",
    "không tìm thấy": "not found",
    "❌ SAI": "❌ WRONG",

    # core/webshop_audit.py
    "{key}: không có trong sheet Webshop — giá kỳ vọng để trống": "{key}: not in the Webshop sheet — expected price left blank",
    "📋 Báo cáo Audit Gói Nạp — {game} Webshop": "📋 Top-up Package Audit Report — {game} Webshop",
    "Ngày kiểm tra: {day}": "Check date: {day}",
    "Phạm vi: {packages} gói × {shops} lượt shop": "Scope: {packages} packages × {shops} package-shop checks",
    "Tổng kết: {packages} gói, {errors} lỗi — cần sửa trên MyTool.": "Summary: {packages} packages, {errors} errors — fix on MyTool.",
    "Tổng kết: {packages} gói, {errors} lỗi — tất cả khớp.": "Summary: {packages} packages, {errors} errors — everything matches.",

    # core/master.py — cảnh báo khi đọc master
    "Không có {key} trong Item Mapping — dùng nội dung của {twin}": "{key} is not in Item Mapping — using the contents of {twin}",
    "Không có trong Item Mapping — kiểm tra nội dung gói trong mô tả (Name & Des)":
        "Not in Item Mapping — check the package contents in the description (Name & Des)",
    "Không thấy sheet '{sheet}'": "Sheet '{sheet}' not found",
    "{sheet}: không thấy header 'Product Key'": "{sheet}: 'Product Key' header not found",
    "Item Mapping: không thấy cột Included Items / Quantity": "Item Mapping: Included Items / Quantity columns not found",
    "Item Mapping: {key} xuất hiện nhiều lần (dòng {row}) — dùng bản đầu tiên":
        "Item Mapping: {key} appears more than once (row {row}) — using the first one",
    "Webshop: không dò được cột giá cho {markets}": "Webshop: could not find the price columns for {markets}",

    # automation/mytool.py — log
    "\n=== MyTool Search Order — shop {shop} ({n} mã) ===": "\n=== MyTool Search Order — shop {shop} ({n} codes) ===",
    "Không thấy ô nhập Order Number (Step 2)": "Order Number input box not found (Step 2)",
    "  · Order Info not available ở shop này": "  · Order Info not available in this shop",
    "  ✓ Đã export: {file}": "  ✓ Exported: {file}",
    "  ⚠ Shop {shop}: chưa cấu hình URL Sold Package (trang Cài đặt) — bỏ qua":
        "  ⚠ Shop {shop}: no Sold Package URL configured (Settings page) — skipped",
    "  ✗ Không thấy ô search ở shop {shop}": "  ✗ Search box not found in shop {shop}",
    "  ✗ {key}: không thấy": "  ✗ {key}: not found",
}
