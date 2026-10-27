"""Bản dịch tiếng Anh — khung app, đăng nhập, thông báo hệ thống, nhãn dùng chung (store, AI, mạng, đồng bộ, automation)."""

EN = {
    # app.py — điều hướng
    "Trang chủ": "Home",
    "Chức năng": "Functions",
    "Tạo gói nạp NC": "Create NC packages",
    "Case nạp lỗi": "Failed top-up cases",
    "Kiểm tra webshop VNG": "VNG webshop check",
    "Lịch sử hoạt động": "Activity history",
    "Dữ liệu dùng chung": "Shared data",
    "Quản lý thành viên": "Members",
    "Cài đặt": "Settings",
    "Hệ thống": "System",

    # core/store.py — nhãn vai trò / loại hoạt động / trạng thái
    "Thành viên": "Member",
    "Chỉ xem": "Viewer",
    "Tạo gói NC": "NC package setup",
    "Kiểm tra webshop": "Webshop check",
    "Cập nhật master": "Master update",
    "Nháp": "Draft",
    "Hoàn thành": "Done",
    "Cần kiểm tra": "Needs check",
    "Huỷ": "Cancelled",
    # core/store.py — lỗi
    "Cần username và mật khẩu": "Username and password are required",
    "Mật khẩu tối thiểu 8 ký tự": "Password must be at least 8 characters",
    "Vai trò không hợp lệ": "Invalid role",
    "Username '{username}' đã tồn tại": "Username '{username}' already exists",
    # core/store.py — thao tác trong nhật ký thay đổi (dữ liệu lưu tiếng Việt, dịch khi hiển thị)
    "tạo thành viên": "create member",
    "sửa thành viên": "edit member",
    "đặt lại mật khẩu": "reset password",
    "cấp token đồng bộ": "issue sync token",
    "kích hoạt": "activate",
    "khoá tài khoản": "lock account",
    "đăng nhập": "sign in",
    "tạo": "create",
    "sửa": "edit",
    "xoá": "delete",
    "khôi phục": "restore",
    "thêm file": "add file",
    "cập nhật kết quả": "update result",
    "thêm Item ID": "add Item ID",
    "sửa Item ID": "edit Item ID",
    "xoá Item ID": "delete Item ID",

    # ui/auth.py
    "Máy này": "This machine",
    "Server chưa có tài khoản admin. Người quản trị cần mở app ngay trên máy server để tạo admin đầu tiên.":
        "The server has no admin account yet. The administrator must open the app on the server machine itself to create the first admin.",
    "Tạo tài khoản admin đầu tiên": "Create the first admin account",
    "Tài khoản này quản lý thành viên, phân quyền và cài đặt của server team.":
        "This account manages members, roles and the team server's settings.",
    "Tên hiển thị": "Display name",
    "Mật khẩu (tối thiểu 8 ký tự)": "Password (at least 8 characters)",
    "Nhập lại mật khẩu": "Repeat password",
    "Tạo admin": "Create admin",
    "Hai mật khẩu không khớp": "The two passwords do not match",
    "Đăng nhập": "Sign in",
    "Mật khẩu": "Password",
    "Sai username/mật khẩu hoặc tài khoản đã bị khoá.": "Wrong username/password, or the account is locked.",
    "Chưa có tài khoản? Liên hệ admin của team để được cấp.": "No account yet? Ask your team admin to create one.",
    "Đăng xuất": "Sign out",
    "Chế độ cá nhân (local)": "Personal mode (local)",

    # ui/common.py
    "Mọi thông số phía sau (app group NC tool, master, bảng Item ID, URL MyTool, lịch sử) đi theo game này.":
        "Everything else (NC tool app group, master, Item ID table, MyTool URLs, history) follows this game.",
    "Bạn đang ở quyền **Chỉ xem**: xem được kết quả và lịch sử, nhưng không chạy hay lưu được.":
        "You have the **Viewer** role: you can see results and history, but cannot run or save anything.",
    "**{label}** bị lỗi: {error}": "**{label}** failed: {error}",
    "Chi tiết lỗi (chụp màn hình phần này gửi người hỗ trợ)": "Error details (screenshot this part and send it to support)",
    "đã đồng bộ ": "synced ",
    "lỗi: ": "error: ",
    "Đã đẩy lên server team ({info}).": "Pushed to the team server ({info}).",
    "Chưa đẩy được lên server team: {info}": "Could not push to the team server: {info}",
    "**📌 Lưu vào lịch sử**": "**📌 Save to history**",
    "**📌 Lưu vào lịch sử của team**": "**📌 Save to team history**",
    "Ghi chú (không bắt buộc)": "Note (optional)",
    "Đã lưu bản ghi #{aid}. {msg}": "Saved record #{aid}. {msg}",
    "Xem trong Lịch sử": "View in History",
    "Đang đọc file master...": "Reading master file...",
    "Cập nhật master: {name}": "Master update: {name}",
    "Tải lên lúc {at} bởi {by} — dùng chung cho mọi function": "Uploaded {at} by {by} — shared by every function",
    "Tải lên lúc {at} — dùng chung cho mọi function": "Uploaded {at} — shared by every function",
    "Chưa có file master **All Product Information** của {game} — tải lên bên phải.":
        "No **All Product Information** master file for {game} yet — upload it on the right.",
    "Chưa có file master **All Product Information** của {game}.": "No **All Product Information** master file for {game} yet.",
    "Tải master mới của {game} (.xlsx)": "Upload a new {game} master (.xlsx)",
    "Không đọc được file master: {error}": "Could not read the master file: {error}",
    "⚠ {n} cảnh báo khi đọc master": "⚠ {n} warnings while reading the master",
    "Quyền Chỉ xem không dùng được AI.": "The Viewer role cannot use AI.",
    "Mở Cài đặt": "Open Settings",
    "Quyền Chỉ xem không chạy được thao tác tự động.": "The Viewer role cannot run automation.",
    "Thao tác tự động dùng phiên đăng nhập MyTool/NC tool của chính bạn, nên phải chạy trên máy bạn: "
    "mở bản local của app (run.bat), cấu hình server team ở trang Cài đặt — kết quả sẽ tự đẩy lên đây. "
    "Hoặc tải file lên thủ công ở tab bên cạnh.":
        "Automation uses your own MyTool/NC tool sign-in, so it must run on your machine: open the local app (run.bat) "
        "and set the team server in Settings — results are pushed here automatically. Or upload the files manually in the next tab.",
    "Thao tác tự động đang bị tắt trên máy này (L2M_NO_AUTOMATION=1). Hãy tải file lên thủ công.":
        "Automation is disabled on this machine (L2M_NO_AUTOMATION=1). Upload the files manually.",
    "Bạn không chạy được thao tác tự động từ máy này.": "You cannot run automation from this machine.",
    "Tiến trình automation không trả kết quả — xem log phía trên.": "The automation process returned no result — see the log above.",
    "xong": "done",
    "lỗi (bấm để xem log)": "failed (click to see the log)",
    "Lỗi không rõ": "Unknown error",
    "Kiểm tra lại": "Check again",

    # core/ai.py
    "Gateway nội bộ (OpenAI-compatible)": "Internal gateway (OpenAI-compatible)",
    "Chưa có API key cho {label}": "No API key for {label}",
    "Gateway nội bộ chưa có base URL": "The internal gateway has no base URL",
    "Gateway nội bộ chưa có base URL.": "The internal gateway has no base URL.",
    "Provider không hợp lệ: {provider}": "Invalid provider: {provider}",
    "Chưa có API key cho {label}. Vào trang Cài đặt để nhập.": "No API key for {label}. Enter it on the Settings page.",
    "Chưa chọn model cho {label}.": "No model selected for {label}.",
    "Không lấy được danh sách model từ {label}: {error}": "Could not get the model list from {label}: {error}",
    "API key Claude không hợp lệ.": "Invalid Claude API key.",
    "API key Claude không có quyền dùng model này.": "This Claude API key is not allowed to use this model.",
    "Model Claude không tồn tại: {model}": "Claude model does not exist: {model}",
    "Claude đang giới hạn tốc độ (rate limit). Thử lại sau ít phút.": "Claude is rate limiting. Try again in a few minutes.",
    "Không kết nối được tới Claude API (kiểm tra mạng/proxy).": "Could not connect to the Claude API (check network/proxy).",
    "Claude API lỗi {code}: {message}": "Claude API error {code}: {message}",
    "Claude từ chối yêu cầu này.": "Claude refused this request.",
    "Kết quả bị cắt do vượt max_tokens — thử chia nhỏ dữ liệu.": "The result was cut off at max_tokens — try splitting the data.",
    "API key {label} không hợp lệ.": "Invalid {label} API key.",
    "Model không tồn tại trên {label}: {model}": "Model does not exist on {label}: {model}",
    "{label} đang giới hạn tốc độ hoặc hết quota.": "{label} is rate limiting or out of quota.",
    "Không kết nối được tới {label} (kiểm tra mạng/base URL).": "Could not connect to {label} (check network/base URL).",
    "{label} lỗi {code}: {message}": "{label} error {code}: {message}",
    "AI trả về dữ liệu không phải JSON hợp lệ.": "The AI did not return valid JSON.",

    # core/netcheck.py
    "Tool này chỉ vào được trong mạng nội bộ — hãy kết nối VPN (GlobalProtect) rồi thử lại.":
        "This tool is only reachable on the internal network — connect the VPN (GlobalProtect) and try again.",
    "Máy này không tra được tên miền của tool (DNS).": "This machine cannot resolve the tool's domain name (DNS).",
    "Không tới được địa chỉ của tool.": "The tool's address is unreachable.",
    "Hết thời gian chờ kết nối tới tool.": "Timed out connecting to the tool.",
    "Tool từ chối kết nối — có thể đang bảo trì hoặc sai địa chỉ trong Cài đặt.":
        "The tool refused the connection — it may be under maintenance, or the address in Settings is wrong.",
    "Kết nối bị ngắt giữa chừng. Thử lại; nếu lặp lại, kiểm tra VPN/tường lửa.":
        "The connection was reset. Try again; if it keeps happening, check the VPN/firewall.",
    "Máy đang mất kết nối mạng.": "This machine is offline.",
    "Proxy không kết nối được tới tool.": "The proxy could not connect to the tool.",
    "Không kết nối được proxy của máy.": "Could not connect to this machine's proxy.",
    "Lỗi chứng chỉ HTTPS của tool (có thể do VPN/proxy chặn HTTPS).": "The tool's HTTPS certificate failed (a VPN/proxy may be intercepting HTTPS).",
    " (tên miền: {host})": " (domain: {host})",
    "Chưa cấu hình URL": "URL not configured",
    "Không tra được tên miền {host}.": "Cannot resolve the domain {host}.",
    "Tra được {host} nhưng không kết nối được cổng {port} ({error}). Có thể cần VPN hoặc bị tường lửa chặn.":
        "Resolved {host} but could not connect to port {port} ({error}). You may need the VPN, or a firewall is blocking it.",
    "Kết nối được": "Reachable",

    # core/db.py
    "Chưa cài psycopg — chạy: pip install -r requirements.txt": "psycopg is not installed — run: pip install -r requirements.txt",
    "Địa chỉ phải bắt đầu bằng postgresql://": "The address must start with postgresql://",
    "Kết nối được (Postgres {version}).": "Connected (Postgres {version}).",
    "Không kết nối được: {error}": "Could not connect: {error}",

    # core/sync.py
    "Không kết nối được server team ({error})": "Could not connect to the team server ({error})",
    "Kết nối được server nhưng token không hợp lệ": "Reached the server, but the token is invalid",
    "Đã kết nối — đăng nhập server với tài khoản '{user}'": "Connected — signed in to the server as '{user}'",

    # automation/runner.py, automation/browser.py — log tiến trình
    "  ✓ Kết nối được {host}": "  ✓ Reachable: {host}",
    "  ⚠ Bỏ qua {url}: {problem}": "  ⚠ Skipped {url}: {problem}",
    "  ⚠ Không mở được {url}: {error}": "  ⚠ Could not open {url}: {error}",
    "🔐 Đăng nhập các trang vừa mở. Xong thì ĐÓNG cửa sổ trình duyệt để lưu phiên.":
        "🔐 Sign in on the pages that just opened. When done, CLOSE the browser window to save the session.",
    "  Tìm thấy {fields} ô, map được {mapped} trường.": "  Found {fields} inputs, mapped {mapped} fields.",
    "  ⚠ Chưa có Product # nên chưa tạo limit — chạy lại sau khi có Product #":
        "  ⚠ No Product # yet, so the limit was not created — run again once there is a Product #",
    "  ⚠ {game}: chưa cấu hình URL Search Order shop {shop}": "  ⚠ {game}: Search Order URL for shop {shop} is not configured",
    "Job không hợp lệ: {job}": "Invalid job: {job}",
    "  [hộp thoại] {message}": "  [dialog] {message}",
    "🔐 Cần đăng nhập — hãy đăng nhập trong cửa sổ trình duyệt vừa mở (app sẽ chờ).":
        "🔐 Sign-in required — sign in in the browser window that just opened (the app will wait).",
    "Hết thời gian chờ đăng nhập.": "Timed out waiting for sign-in.",
    "✅ Đã đăng nhập.": "✅ Signed in.",

    # core/cowork_import.py — nhãn trong bản ghi nhập từ Claude Cowork (dịch khi hiển thị)
    "Gói": "Package",
    "Loại": "Type",
    "Gói đã setup": "Packages set up",
    "Items (ID × SL)": "Items (ID × qty)",
    "Gói gốc": "Base packages",
    "Quy mô": "Scale",
    "Ngày": "Date",
    "Số": "No.",
    "Gói (product)": "Package (product)",
    "Trigger 2 — 6 product / gói": "Trigger 2 — 6 products / package",
    "Nhập từ lịch sử Claude Cowork (skill package-creation)": "Imported from Claude Cowork history (package-creation skill)",
}
