"""Bản dịch tiếng Anh — tạo gói trên NC tool (views/nc_setup.py, core/nc_setup.py, automation/nc_billing.py)."""

EN = {
    # views/nc_setup.py — tiêu đề, chọn gói
    "🛒 Tạo gói nạp trên NC tool": "🛒 Create top-up packages on NC tool",
    "Item Mapping → plan Goods Admin + Limit Admin → điền form (bạn duyệt & bấm Register) → audit":
        "Item Mapping → Goods Admin + Limit Admin plan → fill the forms (you review & click Register) → audit",
    "Game **{name}** chưa khai báo đủ app group / tiền tố Store Product Key. "
    "Admin vào **Cài đặt → Game** để bổ sung (có nút lấy danh sách app group từ NC tool).":
        "Game **{name}** is missing its app group / Store Product Key prefix. "
        "An admin can add them in **Settings → Game** (there is a button to fetch the app group list from NC tool).",
    "1. Chọn gói cần setup": "1. Choose packages to set up",
    "Gói trong Item Mapping": "Packages in Item Mapping",
    "Hoặc dán Product Key (mỗi dòng 1 key)": "Or paste Product Keys (one per line)",
    "Không có trong Item Mapping: {keys} — kiểm tra lại key hoặc tải master mới nhất.":
        "Not in Item Mapping: {keys} — check the keys or upload the latest master.",
    "Chọn ít nhất một gói.": "Choose at least one package.",
    "Convention cố định (áp cho mọi gói)": "Fixed conventions (apply to every package)",

    # Cột bảng / khoá dữ liệu lưu lịch sử (giữ tiếng Việt trong dữ liệu, dịch khi hiển thị)
    "Gói": "Package",
    "Tên": "Name",
    "Giá USD": "Price USD",
    "Trường": "Field",
    "Giá trị": "Value",
    "Ghi chú": "Note",
    "Kết quả": "Result",
    "Kỳ vọng": "Expected",
    "Thấy trên tool": "Seen on tool",
    "Đã đăng ký": "Registered",
    "Trường cần điền tay": "Fields to fill manually",
    "Kết quả setup": "Setup results",
    "Vấn đề còn lại": "Remaining issues",
    "Trường sai (audit)": "Wrong fields (audit)",
    "Trường sai": "Wrong fields",

    # core/nc_setup.py — convention cố định (hiển thị qua common.df)
    "Mặc định (now → 2099-12-31 21:59:59)": "Default (now → 2099-12-31 21:59:59)",
    "Sale status sau khi tạo": "Sale status after creation",
    "Sale pending → bấm Start sale ở Product lookup để mở bán": "Sale pending → click Start sale in Product lookup to open sales",
    "ĐỂ TRỐNG — không check nước nào": "LEAVE EMPTY — do not tick any country",
    # core/nc_setup.py — cách khớp item (giá trị dữ liệu, dịch khi hiển thị)
    "chính xác": "exact",
    "trùng tên trên tool": "same name on tool",
    "gần đúng (khác Bound)": "close (Bound differs)",
    "gần đúng (fuzzy)": "close (fuzzy)",
    "chưa có": "no match",
    "Tool (đã chọn)": "Tool (picked)",

    # views/nc_setup.py — duyệt plan
    "2. Duyệt plan từng gói": "2. Review each package's plan",
    "Tên setup trên tool (tối đa {max} ký tự; tên Excel: {excel})": "Setup name on tool (max {max} characters; Excel name: {excel})",
    "⚠ {n} ký tự — tool sẽ cắt thành: “{cut}”": "⚠ {n} characters — the tool will cut it to: “{cut}”",
    "Không giới hạn — không tạo limit": "Unlimited — no limit will be created",
    "{amount} / {user_type} / không gia hạn — {note}": "{amount} / {user_type} / no renewal — {note}",
    "{price} / {price} USD (Excel ${excel} → làm tròn lên)": "{price} / {price} USD (Excel ${excel} → rounded up)",
    "Limit sẽ tạo": "Limit to create",
    "Diamonds trong gói": "Diamonds in package",
    "Dòng trong master": "Row in master",
    "**Item composition** — sửa trực tiếp Item ID / Quantity nếu cần, tick *Xác nhận* khi đã chắc chắn":
        "**Item composition** — edit Item ID / Quantity directly if needed, tick *Confirmed* once you are sure",
    "Tên trong Excel": "Name in Excel",
    "Tên item trên tool": "Item name on tool",
    "Cách khớp": "Match type",
    "Xác nhận": "Confirmed",

    # views/nc_setup.py — tìm Item ID
    "**Tìm Item ID cho các item chưa xác nhận**": "**Find Item IDs for unconfirmed items**",
    "Danh sách item {group} đã tải từ NC tool: **{n}** item": "{group} item list downloaded from NC tool: **{n}** items",
    " (cập nhật {at})": " (updated {at})",
    " — chưa tải": " — not downloaded yet",
    "Tên trong Excel hay khác tên trên tool, nên app so khớp gần đúng với danh sách này; AI chỉ chọn trong các item thật đó.":
        "Excel names often differ from tool names, so the app fuzzy-matches against this list; AI only picks among these real items.",
    "📥 Tải danh sách item từ NC tool ({group})": "📥 Download item list from NC tool ({group})",
    "Tìm với tên trống rồi lật hết các trang kết quả. Chạy lại khi tool có item mới.":
        "Searches with an empty name and pages through all results. Run again when the tool has new items.",
    "Đang tải danh sách item": "Downloading item list",
    "Đã lưu {n} item của {group}. Tự khớp được {matched} item trùng tên.":
        "Saved {n} {group} items. Auto-matched {matched} items with identical names.",
    "🔎 Tra riêng {n} item trên NC tool": "🔎 Look up {n} items on NC tool",
    "Đang tra Item lookup": "Looking up in Item lookup",
    "🤖 AI chọn giúp ({n} item có ứng viên)": "🤖 Let AI pick ({n} items with candidates)",
    "Đang hỏi {ai}...": "Asking {ai}...",
    "— chưa chọn —": "— not picked —",
    "{item_id} — {name}  ·  giống {score:.0%}": "{item_id} — {name}  ·  {score:.0%} similar",
    "  ·  🤖 AI chọn": "  ·  🤖 AI pick",
    "Cạnh mỗi item là số gói trong master đã dùng nó và gói gần nhất (gói mới thêm ở cuối sheet Item Mapping). "
    "⭐ = nên dùng: trong các item cùng tên, item có trong nhiều gói gần đây nhất. "
    "Chỉ đếm được dòng item app đã biết Item ID ({pct:.0%} dòng trong master) — tải danh sách item từ NC tool để đếm đủ hơn.":
        "Next to each item: how many packages in the master used it and the latest one (new packages are added at the bottom of "
        "the Item Mapping sheet). ⭐ = recommended: among items with the same name, the one in the most recent packages. "
        "Only item rows whose Item ID the app knows are counted ({pct:.0%} of rows in the master) — download the item list "
        "from NC tool to count more.",
    "{n} gói, gần nhất {key}": "{n} packages, latest {key}",
    "chưa gói nào dùng": "not used in any package",
    "⭐ Nên dùng **{item_id}**: có trong {n} gói của master ({recent} gói trong {window} gói gần nhất). "
    "Gói gần nhất dùng nó: {key} — {package}":
        "⭐ Recommended: **{item_id}** — in {n} packages of the master ({recent} of the latest {window}). "
        "Latest package using it: {key} — {package}",
    " (gói mới nhất).": " (the newest package).",
    " ({n} gói trước).": " ({n} packages ago).",
    " Cùng tên nhưng chưa gói nào dùng: {ids}.": " Same name but not used in any package: {ids}.",
    " ⚠ Khác item trùng tên **{item_id}** — kiểm tra kỹ trước khi chọn.":
        " ⚠ Differs from the item with the exact same name (**{item_id}**) — check carefully before picking.",
    " · đã tra theo “{query}”": " · looked up as “{query}”",
    "Chưa có ứng viên. Tải danh sách item hoặc tra riêng trên NC tool; vẫn không ra thì nhập Item ID tay ở bảng item phía trên.":
        "No candidates yet. Download the item list or look it up on NC tool; if still nothing, enter the Item ID manually in the item table above.",
    "Item trên tool": "Item on tool",
    "✅ Áp dụng {n} Item ID đã chọn": "✅ Apply {n} picked Item IDs",
    "Đã áp dụng {n} Item ID. Bấm 'Lưu Item ID… vào bảng dùng chung' để cả team dùng lại.":
        "Applied {n} Item IDs. Click 'Save … Item IDs to the shared table' so the whole team can reuse them.",
    "💾 Lưu {n} Item ID đã xác nhận vào bảng dùng chung": "💾 Save {n} confirmed Item IDs to the shared table",
    "Đã lưu vào bảng Item ID của {game} — từ giờ app (và cả team) sẽ tự nhận các item này.":
        "Saved to the {game} Item ID table — from now on the app (and the whole team) will recognize these items automatically.",

    # views/nc_setup.py — setup trên tool
    "3. Setup trên NC tool": "3. Set up on NC tool",
    "Còn {n} vấn đề ở {packages} gói — xử lý xong mới setup được.":
        "{n} issues left in {packages} packages — resolve them before setting up.",
    "⬇ Tải plan (JSON)": "⬇ Download plan (JSON)",
    "📝 Lưu plan vào lịch sử (nháp — chưa setup)": "📝 Save plan to history (draft — not set up yet)",
    "Plan setup {n} gói: {keys}": "Setup plan for {n} packages: {keys}",
    "Đã lưu plan nháp #{aid}. {msg}": "Saved draft plan #{aid}. {msg}",
    "Cách bấm Register": "How to click Register",
    "App điền form, tôi tự kiểm tra & bấm Register (khuyến nghị)": "The app fills the form, I check it & click Register myself (recommended)",
    "App tự bấm Register khi điền đủ mọi trường": "The app clicks Register itself once every field is filled",
    "Tạo purchase limit ngay sau khi có Product #": "Create the purchase limit right after the Product # exists",
    "Tôi đã kiểm tra plan của {n} gói {game} và đồng ý tạo trên môi trường RC":
        "I have checked the plan for {n} {game} packages and agree to create them on the RC environment",
    "🚀 Mở NC tool & điền form": "🚀 Open NC tool & fill the forms",
    "Đang setup trên NC tool": "Setting up on NC tool",
    "Nhớ bấm **Start sale** ở Product lookup để mở bán (sau khi tạo, gói ở trạng thái Sale pending).":
        "Remember to click **Start sale** in Product lookup to open sales (new packages are in Sale pending status).",
    "Setup {ok}/{n} gói trên NC: {keys}": "Set up {ok}/{n} packages on NC: {keys}",
    "Đã ghi lịch sử #{aid}. {msg}": "Logged to history #{aid}. {msg}",

    # views/nc_setup.py — audit
    "4. Audit sau khi setup (bắt buộc)": "4. Audit after setup (required)",
    "🔍 Audit từng gói": "🔍 Audit each package",
    "Nhập Product # (và Limit GUID nếu có) trước.": "Enter the Product # (and Limit GUID if any) first.",
    "Đang đọc trang chi tiết": "Reading detail pages",
    "❌ {n} trường sai": "❌ {n} wrong fields",
    "❔ = trang không hiển thị đủ để kết luận tự động — mở link kiểm tra bằng mắt: {url}":
        "❔ = the page does not show enough to decide automatically — open the link and check by eye: {url}",
    "Audit setup NC: {keys}": "NC setup audit: {keys}",
    "Đã ghi kết quả audit vào lịch sử #{aid}.": "Audit results logged to history #{aid}.",

    # views/nc_setup.py — calibrate
    "⚙ Nâng cao: Calibrate form NC tool (chạy 1 lần sau khi đăng nhập)": "⚙ Advanced: Calibrate NC tool forms (run once after signing in)",
    "App mở form thật, liệt kê mọi ô nhập và tự map với các trường cần điền. "
    "Kết quả lưu vào data/nc_fields.json để lần sau điền chính xác theo name/id (dùng chung cho mọi game).":
        "The app opens the real form, lists every input and maps it to the fields to fill. "
        "The result is saved to data/nc_fields.json so later runs fill exactly by name/id (shared by every game).",
    "Đang đọc {label}": "Reading {label}",
    "**{form}** — map được {n} trường": "**{form}** — mapped {n} fields",
    "Xem toàn bộ ô trên trang": "See every input on the page",
    "Lưu mapping {form}": "Save mapping {form}",
    "Đã lưu vào {path}": "Saved to {path}",

    # core/nc_setup.py — purchase limit, kiểm tra plan
    "Không hiểu Purchase Limit '{value}' — nhập tay": "Cannot read Purchase Limit '{value}' — enter it manually",
    "Không gia hạn → Permanent / 1": "No renewal → Permanent / 1",
    "Chu kỳ '{period}' chưa được hỗ trợ — nhập tay": "Period '{period}' is not supported yet — enter it manually",
    "Thiếu tên gói": "Package name is missing",
    "Tên gói {n} ký tự > {max} — tool sẽ cắt im lặng. Rút gọn tên setup "
    "(vd 901 dùng 'Einhasad Shirt Superb Blessing Pack')":
        "Package name is {n} characters > {max} — the tool cuts it silently. Shorten the setup name "
        "(e.g. 901 uses 'Einhasad Shirt Superb Blessing Pack')",
    "Thiếu giá USD": "USD price is missing",
    "Gói chưa có item nào": "The package has no items",
    "Item '{name}' chưa có Item ID — tra Item lookup trên NC tool": "Item '{name}' has no Item ID — look it up in Item lookup on NC tool",
    "Item '{name}' khớp {match} với '{tool_name}' (ID {item_id}) — cần xác nhận":
        "Item '{name}' matched ({match}) to '{tool_name}' (ID {item_id}) — needs confirmation",
    "Item '{name}' có Quantity không hợp lệ — đọc lại cột Quantity": "Item '{name}' has an invalid Quantity — re-check the Quantity column",
    # core/nc_setup.py — audit
    "Tên gói (admin/customer/description)": "Package name (admin/customer/description)",
    "xuất hiện {n} lần": "appears {n} times",
    "có ID trên trang": "ID found on page",
    "không thấy ID": "ID not found",
    "(trống)": "(empty)",

    # automation/nc_billing.py — log khi điền form
    "✗ CHƯA MAP — điền tay": "✗ NOT MAPPED — fill manually",
    "✗ CHƯA ĐIỀN ĐƯỢC — điền tay": "✗ COULD NOT FILL — fill manually",
    "⚠ Không thấy app group '{group}'. Các ô chọn đang có trên trang:": "⚠ App group '{group}' not found. Select boxes on the page:",
    "{n} lựa chọn:": "{n} options:",
    "(không có ô <select> nào chứa app group — có thể là dropdown nạp dữ liệu khi gõ; gửi ảnh chụp ô này để chỉnh)":
        "(no <select> contains the app group — it may be a dropdown that loads while typing; send a screenshot of it so it can be adjusted)",
    "✗ Không thấy ô chọn app group trên trang Item lookup": "✗ App group selector not found on the Item lookup page",
    "✓ Tìm thấy {n} app group": "✓ Found {n} app groups",
    "Tạo gói {key} — {name} (giá {price})": "Create package {key} — {name} (price {price})",
    "Tên gói ×3 = {name}": "Package name ×3 = {name}",
    "{name} chưa có Item ID — bỏ qua, thêm tay": "{name} has no Item ID — skipped, add it manually",
    "✗ Đã thêm item {item_id} nhưng không thấy ô Quantity — điền tay {qty}":
        "✗ Added item {item_id} but the Quantity box was not found — enter {qty} manually",
    "✗ Không thấy $.fn.addGoodsItem trên trang — thêm item bằng tay": "✗ $.fn.addGoodsItem not found on the page — add items manually",
    "⚠ Còn trường chưa điền được nên KHÔNG tự bấm Register.": "⚠ Some fields could not be filled, so Register was NOT clicked automatically.",
    "⏸ Kiểm tra form trong trình duyệt rồi tự bấm Register. App đang chờ (tối đa 30 phút)...":
        "⏸ Check the form in the browser, then click Register yourself. The app is waiting (up to 30 minutes)...",
    "✓ Đã đăng ký.": "✓ Registered.",
    "✗ Chưa đăng ký (cửa sổ đóng hoặc hết giờ).": "✗ Not registered (window closed or timed out).",
    "Tạo purchase limit cho {key} (Product #{goods_id})": "Create purchase limit for {key} (Product #{goods_id})",
    "(không thấy ô)": "(field not found)",
    "✗ Chu kỳ '{period}' chưa có mã — chọn tay ô Renewal": "✗ Period '{period}' has no code — pick Renewal manually",
    "· Countries to Apply: để trống": "· Countries to Apply: left empty",
    "✓ Thêm Product #{goods_id}, weight 1": "✓ Added Product #{goods_id}, weight 1",
    "✗ Không thấy $.fn.addGoods — thêm product bằng tay": "✗ $.fn.addGoods not found — add the product manually",
    # automation/nc_billing.py — tra / tải item, tìm ID sau khi tạo
    "· Hiển thị {n} dòng mỗi trang": "· Showing {n} rows per page",
    "Không chọn được app group '{group}' trên trang Item lookup": "Could not select app group '{group}' on the Item lookup page",
    "· Đã đọc {pages} trang, {rows} dòng": "· Read {pages} pages, {rows} rows",
    "✓ Tải được {n} item": "✓ Downloaded {n} items",
    "⚠ Tìm với tên trống không ra kết quả — tool có thể bắt buộc nhập điều kiện tìm":
        "⚠ Searching with an empty name returned nothing — the tool may require a search condition",
    "Không thấy ô 'Item name' trên trang Item lookup": "'Item name' box not found on the Item lookup page",
    "{n} kết quả": "{n} results",
    " (tìm theo '{query}')": " (searched as '{query}')",
    "⚠ Tra bằng POST không được (có thể phiên đăng nhập hết hạn) — chuyển sang bấm qua giao diện":
        "⚠ POST lookup failed (the sign-in session may have expired) — switching to clicking through the UI",
    "⚠ Tra bằng POST không được — chuyển sang bấm qua giao diện": "⚠ POST lookup failed — switching to clicking through the UI",
    "· Đã đọc {pages} trang, {n} item": "· Read {pages} pages, {n} items",
    "✓ Tải được {n} item của {group}": "✓ Downloaded {n} items of {group}",
    "⚠ Không tự tìm được Product # ({error}) — nhập tay ở bước audit": "⚠ Could not find the Product # automatically ({error}) — enter it at the audit step",
    "⚠ Không tự tìm được Limit GUID ({error}) — nhập tay ở bước audit": "⚠ Could not find the Limit GUID automatically ({error}) — enter it at the audit step",
}
