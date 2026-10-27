"""Bản dịch tiếng Anh — case nạp lỗi (views/payment_errors.py, core/payment_errors.py).

File Payment Error Case <MMDD>.xlsx và CSV từng user là định dạng cố định giao CS/NC: không dịch.
"""

EN = {
    # views/payment_errors.py
    "🧾 Case nạp lỗi": "🧾 Failed top-up cases",
    "Sheet CS → MyTool Search Order → master → file đền bù (Excel + CSV từng user)":
        "CS sheet → MyTool Search Order → master → compensation files (Excel + one CSV per user)",
    "Đang đọc sheet CS...": "Reading the CS sheet...",
    "Đang đọc file MyTool...": "Reading the MyTool file...",
    "🧪 Chạy thử với dữ liệu mẫu (giả lập)": "🧪 Try it with sample data (simulated)",
    "Dùng 3 file mẫu trong tests/samples để xem toàn bộ quy trình. Không đụng tới master đang dùng.":
        "Uses the 3 sample files in tests/samples to walk through the whole flow. The current master is not touched.",
    "1. Danh sách case từ CS": "1. Case list from CS",
    "File CS escalation (.xlsx) — Google Sheet → Tệp → Tải xuống → Microsoft Excel":
        "CS escalation file (.xlsx) — Google Sheet → File → Download → Microsoft Excel",
    "Đọc danh sách tab của file CS": "Read the tab list of the CS file",
    "Đọc từ dòng": "Read from row",
    "Đến dòng (0 = hết bảng)": "To row (0 = end of table)",
    "Cấu hình cột của sheet CS (mặc định theo template [NCV] - [L2M] Support Escalation)":
        "CS sheet column setup (defaults follow the [NCV] - [L2M] Support Escalation template)",
    "Package name / ghi chú": "Package name / note",
    "Không đọc được sheet CS: {error}": "Could not read the CS sheet: {error}",
    "{rows} dòng có dữ liệu · {orders} Order Number hợp lệ · {iap} dòng IAP · {bad} dòng có mã sai độ dài":
        "{rows} rows with data · {orders} valid Order Numbers · {iap} IAP rows · {bad} rows with wrong-length codes",
    "Xem dữ liệu CS đã đọc": "View the CS data read",
    "Dòng": "Row",
    "Order hợp lệ": "Valid orders",
    "Mã sai": "Invalid codes",
    "2. Dữ liệu MyTool Search Order": "2. MyTool Search Order data",
    "Tự tra bằng trình duyệt": "Look up in the browser",
    "Tải file Export Excel": "Upload Export Excel files",
    "Shop cần tra": "Shops to search",
    "Cột Country của CS không quyết định shop — tra cả hai cho chắc.":
        "The CS Country column does not determine the shop — search both to be safe.",
    "Tra {n} Order Number & Export Excel": "Look up {n} Order Numbers & Export Excel",
    "Đang tra MyTool": "Searching MyTool",
    "File `<AppAlias>-orders.xlsx` (có thể chọn nhiều file: SEA + VN)":
        "`<AppAlias>-orders.xlsx` files (you can pick several: SEA + VN)",
    "{orders} order trong file MyTool · {errors} order DELIVERY_SERVER_ERROR":
        "{orders} orders in the MyTool files · {errors} DELIVERY_SERVER_ERROR orders",
    "Đang dùng master mẫu.": "Using the sample master.",
    "4. Kết quả đối chiếu": "4. Reconciliation result",
    "Cần sheet CS (bước 1) và dữ liệu MyTool (bước 2) để đối chiếu.":
        "The CS sheet (step 1) and MyTool data (step 2) are needed to reconcile.",
    "Chưa có master — cột Diamonds sẽ phải nhập tay.": "No master yet — the Diamonds column must be entered by hand.",
    "Đối chiếu CS × MyTool × master": "Reconcile CS × MyTool × master",
    "Thiếu Diamonds cho {n} gói — nhập tay (thường do master cũ chưa có gói mới).":
        "Diamonds missing for {n} packages — enter them by hand (usually an old master without the new packages).",
    "Diamonds / gói — {package}": "Diamonds / package — {package}",
    "Order lỗi thật": "Real failed orders",
    "User cần đền bù": "Users to compensate",
    "Case bị loại": "Excluded cases",
    "Cảnh báo": "Warnings",
    "Bị loại ({n})": "Excluded ({n})",
    "Cảnh báo ({n})": "Warnings ({n})",
    "Order dư trên MyTool ({n})": "Extra orders on MyTool ({n})",
    "Diamonds/gói": "Diamonds/package",
    "Không có cảnh báo.": "No warnings.",
    "Theo rule: KHÔNG tự thêm vào file. Hỏi lại CS/user trước, mặc định bám danh sách CS.":
        "Rule: do NOT add these to the file automatically. Check with CS/the user first; by default follow the CS list.",
    "**Checklist audit trước khi giao**": "**Audit checklist before handing over**",
    "5. Xuất file": "5. Export files",
    "Ngày của đợt xử lý": "Date of this batch",
    "Không có order lỗi thật nào để xuất.": "No real failed orders to export.",
    "{n} file: ": "{n} files: ",
    "Tạo file Excel/CSV": "Create Excel/CSV files",
    "⬇ Tải ZIP (Excel + CSV)": "⬇ Download ZIP (Excel + CSV)",
    "Lưu vào `{folder}`": "Save to `{folder}`",
    "Ghi đè {n} file đã có ({names}...)": "Overwrite {n} existing files ({names}...)",
    "💾 Lưu vào thư mục": "💾 Save to folder",
    "Đã lưu {n} file vào {folder}": "Saved {n} files to {folder}",
    "🤖 Viết tóm tắt đợt xử lý bằng AI (để báo cáo / gửi team)": "🤖 Write a batch summary with AI (for reporting / the team)",
    "Gửi lên AI: nickname, server, số order, Product ID, lý do loại. Không gửi Account Number hay Game Account ID.":
        "Sent to AI: nickname, server, order count, Product ID, exclusion reasons. Account Number and Game Account ID are never sent.",
    "Viết tóm tắt": "Write summary",
    "Đang gọi {ai}...": "Calling {ai}...",
    "📌 Lưu đợt này vào lịch sử": "📌 Save this batch to history",
    "[MẪU] ": "[SAMPLE] ",
    "{sample}Case nạp lỗi {day} — {users} user, {orders} order": "{sample}Failed top-up cases {day} — {users} users, {orders} orders",
    # Khoá metrics / bảng lưu lịch sử (dịch khi hiển thị)
    "Dòng CS": "CS row",
    "Order lỗi": "Failed orders",
    "User đền bù": "Compensated users",
    "Bị loại": "Excluded",
    "Nội dung": "Content",
    "Order dư trên MyTool": "Extra orders on MyTool",
    "Kiểm tra": "Check",
    "Lý do": "Reason",
    "(trống)": "(empty)",

    # core/payment_errors.py — thông báo đối chiếu (Msg: file/lịch sử giữ tiếng Việt, giao diện dịch)
    "{raw} (ô dạng số — Excel đã làm tròn mã)": "{raw} (numeric cell — Excel rounded the code)",
    "Không nhận diện được file export MyTool (không thấy cột OrderNumber / DeliveryStatus).":
        "Not recognised as a MyTool export file (no OrderNumber / DeliveryStatus column).",
    "File export MyTool thiếu cột OrderNumber hoặc DeliveryStatus.": "The MyTool export file is missing the OrderNumber or DeliveryStatus column.",
    "AppTransaction ID đầy đủ và không trùng ({unique}/{total})": "AppTransaction IDs complete and unique ({unique}/{total})",
    "Account Number đủ 19 số — sai: {names}": "Account Numbers have 19 digits — wrong: {names}",
    "Account Number đủ 19 số": "Account Numbers have 19 digits",
    "Game Account ID MyTool khớp cột D của CS — {n} lệch": "MyTool Game Account IDs match CS column D — {n} mismatched",
    "Game Account ID MyTool khớp cột D của CS": "MyTool Game Account IDs match CS column D",
    "Có đủ Diamonds cho mọi gói — thiếu: {packages}": "Diamonds known for every package — missing: {packages}",
    "Có đủ Diamonds cho mọi gói": "Diamonds known for every package",
    "CSV đúng dạng `<Account Number>,1` + CRLF": "CSVs use the `<Account Number>,1` + CRLF format",
    "File MyTool có {n} OrderNumber không đủ 19 số (có thể bị Excel làm tròn).":
        "The MyTool file has {n} OrderNumber(s) shorter than 19 digits (Excel may have rounded them).",
    "{pid}: không có trong master — cần tải bản master mới nhất": "{pid}: not in the master — upload the latest master",
    "{pid}: tên master '{name}' khác tên MyTool '{mytool}'": "{pid}: master name '{name}' differs from MyTool name '{mytool}'",
    "{provider}: IAP không có trên MyTool webpayment — user tự kiểm tra":
        "{provider}: IAP is not on MyTool webpayment — the user must check it themselves",
    "Transaction ID sai/thiếu số — tra theo User ID trên MyTool rồi báo CS sửa sheet":
        "Wrong/incomplete Transaction ID — look it up by User ID on MyTool, then ask CS to fix the sheet",
    "Dòng CS {row} ({nickname}): mã '{token}' không đủ 19 số": "CS row {row} ({nickname}): code '{token}' does not have 19 digits",
    "Không có Transaction ID": "No Transaction ID",
    "Không có trong file export MyTool (thử shop còn lại SEA ↔ VN)": "Not in the MyTool export file (try the other shop SEA ↔ VN)",
    "Order {order} xuất hiện ở nhiều dòng CS — chỉ tính 1 lần (dòng {row})":
        "Order {order} appears in several CS rows — counted once (row {row})",
    "Dòng CS {row}: Game Account ID khác MyTool ({cs_user} ≠ {mytool_user}) — order {order}":
        "CS row {row}: Game Account ID differs from MyTool ({cs_user} ≠ {mytool_user}) — order {order}",
    "Dòng CS {row}: Server CS {cs_server} ≠ MyTool {mytool_server} — đang giữ theo CS, hỏi lại nếu cần":
        "CS row {row}: CS server {cs_server} ≠ MyTool {mytool_server} — keeping the CS value, double-check if needed",
    "{n} order không phải DELIVERY_SERVER_ERROR — loại": "{n} order(s) not DELIVERY_SERVER_ERROR — excluded",
    "MyTool có thêm {n} order lỗi không nằm trong danh sách CS — không tự thêm, cần hỏi lại.":
        "MyTool has {n} more failed order(s) not on the CS list — not added automatically, check with CS.",
}
