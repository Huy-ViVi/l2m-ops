"""Bản dịch tiếng Anh — trang Team & Hệ thống: lịch sử, trang chủ, cài đặt, thành viên, dữ liệu dùng chung."""

EN = {
    # ---- views/history.py ----------------------------------------------------------
    "🕘 Lịch sử hoạt động": "🕘 Activity history",
    "Mọi đợt xử lý đã lưu: ai làm, lúc nào, kết quả và file đi kèm. Thêm ghi chú, sửa trạng thái, xoá bản ghi.":
        "Every saved run: who did it, when, the result and attached files. Add notes, change status, delete records.",
    "📥 Nhập lịch sử từ Claude Cowork (skill package-creation)": "📥 Import history from Claude Cowork (package-creation skill)",
    "Đọc bảng Setup History, counter.md và các file log trong thư mục 07_Package-Creation; "
    "bổ sung Item ID mới. Bản ghi đã nhập sẽ được bỏ qua, chạy lại không tạo trùng.":
        "Reads the Setup History table, counter.md and the log files in the 07_Package-Creation folder, and adds new Item IDs. "
        "Records already imported are skipped, so re-running never creates duplicates.",
    "Thư mục": "Folder",
    "Nhập / cập nhật lịch sử": "Import / update history",
    "Không thấy SKILL.md trong {path}": "SKILL.md not found in {path}",
    "Nhập lịch sử Cowork": "Import Cowork history",
    "Đã nhập {records} đợt mới (bỏ qua {skipped} đợt đã có), thêm {items} Item ID.":
        "Imported {records} new batches (skipped {skipped} already imported), added {items} Item IDs.",
    "Hoạt động": "Activities",
    "Nhật ký thay đổi": "Change log",
    "Ghi lại mọi thao tác thay đổi dữ liệu: tạo/sửa/xoá bản ghi, Item ID, thành viên, cài đặt, đăng nhập.":
        "Every data change is logged: creating/editing/deleting records, Item IDs, members, settings, sign-ins.",
    "Lúc": "Time",
    "Người": "User",
    "Thao tác": "Action",
    "Đối tượng": "Target",
    "Chi tiết": "Details",
    "Loại": "Type",
    "Tìm theo tiêu đề, ghi chú, người tạo, nội dung": "Search title, note, creator, content",
    "Mọi game": "All games",
    "Tắt: chỉ hiện lịch sử của {game}": "Off: show only {game} history",
    "Hiện bản đã xoá": "Show deleted",
    "Chưa có bản ghi nào.": "No records yet.",
    "Chưa có bản ghi nào của {game}.": "No {game} records yet.",
    "Ở mỗi function, sau khi có kết quả, bấm **Lưu vào lịch sử**.": "In each function, once you have a result, click **Save to history**.",
    "Tiêu đề": "Title",
    "Trạng thái": "Status",
    "Người tạo": "Created by",
    "Lúc tạo": "Created at",
    "Sửa lần cuối": "Last edited",
    "Nguồn": "Source",
    "Đồng bộ": "Sync",
    "Đã xoá": "Deleted",
    "Xem chi tiết bản ghi": "View record details",
    "tạo bởi **{created_by}** lúc {created_at} · sửa lần cuối {updated_by} lúc {updated_at} · nguồn {source}":
        "created by **{created_by}** at {created_at} · last edited by {updated_by} at {updated_at} · source {source}",
    "🗑 đã xoá": "🗑 deleted",
    "Nhập từ lịch sử Claude Cowork (skill package-creation)": "Imported from Claude Cowork history (package-creation skill)",
    "**File đính kèm**": "**Attached files**",
    "Dữ liệu gốc (JSON)": "Raw data (JSON)",
    "**Sửa bản ghi**": "**Edit record**",
    "Ghi chú": "Note",
    "💾 Lưu thay đổi": "💾 Save changes",
    "Đã lưu thay đổi bản ghi #{aid}.": "Saved changes to record #{aid}.",
    "Xác nhận xoá bản ghi #{aid}": "Confirm deleting record #{aid}",
    "🗑 Xoá": "🗑 Delete",
    "↩ Khôi phục": "↩ Restore",
    "Chỉ người tạo hoặc admin mới sửa/xoá được bản ghi này.": "Only the creator or an admin can edit/delete this record.",

    # ---- views/home.py --------------------------------------------------------------
    "các workflow vận hành game NCV trước đây làm qua Claude Chat, giờ chạy độc lập. Đổi game ở thanh bên trái.":
        "NCV game-ops workflows previously done through Claude Chat, now running standalone. Switch games in the left sidebar.",
    "Chưa cấu hình": "Not configured",
    "Chế độ": "Mode",
    "Team · {n} thành viên": "Team · {n} members",
    "Cá nhân (local)": "Personal (local)",
    "Master {game}": "Master {game}",
    "Chưa có": "None yet",
    "{reason}. Các bước dùng AI sẽ bị tắt cho đến khi admin cấu hình.": "{reason}. AI steps are disabled until an admin configures it.",
    "Mở Cài đặt": "Open Settings",
    "**Hoạt động gần đây — {game}**": "**Recent activity — {game}**",
    "Xem toàn bộ lịch sử": "View full history",
    "Đọc Item Mapping → dựng plan setup Goods Admin + Limit Admin theo convention → điền form trên NC tool "
    "(bạn duyệt và bấm Register) → audit lại từng trường.":
        "Reads Item Mapping → builds the Goods Admin + Limit Admin setup plan by convention → fills the forms on the NC tool "
        "(you review and click Register) → audits every field.",
    "Sheet CS → tra MyTool Search Order (Export Excel) → lọc DELIVERY_SERVER_ERROR → lấy Diamonds từ master → "
    "xuất `Payment Error Case <MMDD>.xlsx` + CSV từng user.":
        "CS sheet → MyTool Search Order lookup (Export Excel) → filter DELIVERY_SERVER_ERROR → Diamonds from master → "
        "export `Payment Error Case <MMDD>.xlsx` + a CSV per user.",
    "So gói đang bán trên MyTool (6 shop) với master: giá, thời gian bán, tên, trạng thái → báo cáo ✅/❌.":
        "Compares packages on sale on MyTool (6 shops) with master: price, sale period, name, status → ✅/❌ report.",
    "**Nguyên tắc an toàn**\n"
    "- App không bao giờ tự nhập mật khẩu. Bạn tự đăng nhập SSO trong cửa sổ trình duyệt của app (lưu ở `data/browser-profile`).\n"
    "- Trước mọi thao tác tạo/sửa trên tool, app luôn cho xem plan và chờ bạn xác nhận. Mặc định app chỉ điền form, bạn tự bấm Register.\n"
    "- AI chỉ dùng cho phần cần hiểu ngữ cảnh (map tên item, đọc Timeline Selling, viết tóm tắt). Kết quả AI luôn hiển thị để bạn duyệt.":
        "**Safety rules**\n"
        "- The app never types passwords. You sign in to SSO yourself in the app's browser window (stored in `data/browser-profile`).\n"
        "- Before any create/edit action on a tool, the app always shows the plan and waits for your confirmation. By default it only fills the form; you click Register yourself.\n"
        "- AI is used only where context is needed (mapping item names, reading Timeline Selling, writing summaries). AI results are always shown for your review.",

    # ---- views/settings.py ----------------------------------------------------------
    "⚙️ Cài đặt": "⚙️ Settings",
    "Chỉ admin mới sửa được cài đặt.": "Only admins can change settings.",
    "AI dùng mặc định": "Default AI",
    "Base URL (OpenAI-compatible, vd LiteLLM)": "Base URL (OpenAI-compatible, e.g. LiteLLM)",
    "Bấm 'Lấy danh sách model' để chọn từ các model key này được dùng.": "Click 'Fetch model list' to pick from the models this key can use.",
    "📋 Lấy danh sách model": "📋 Fetch model list",
    "API key lưu ở `data/settings.json` trên máy chạy app, không hiển thị cho thành viên khác. "
    "Có thể đặt qua biến môi trường (ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, GATEWAY_API_KEY, GATEWAY_BASE_URL).":
        "API keys are stored in `data/settings.json` on the machine running the app and are never shown to other members. "
        "They can also be set via environment variables (ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, GATEWAY_API_KEY, GATEWAY_BASE_URL).",
    "API key lưu trong CSDL chung (website và bản local cùng dùng), chỉ admin thấy ở trang Cài đặt. "
    "Có thể đặt qua biến môi trường / secrets (ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, GATEWAY_API_KEY, GATEWAY_BASE_URL).":
        "API keys are stored in the shared database (used by both the website and local apps) and only admins see them on the Settings page. "
        "They can also be set via environment variables / secrets (ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, GATEWAY_API_KEY, GATEWAY_BASE_URL).",
    "CSDL dùng chung của team": "Team shared database",
    "Đang dùng CSDL chung `{where}`: website và bản local của mọi người cùng đọc/ghi CSDL này.":
        "Using the shared database `{where}`: the website and everyone's local app read and write this database.",
    "Địa chỉ CSDL lấy từ biến môi trường / secrets DATABASE_URL.": "The database address comes from the DATABASE_URL environment variable / secret.",
    "Ngắt CSDL chung trên máy này": "Disconnect this machine from the shared database",
    "Đã ngắt CSDL chung: máy này quay về dữ liệu riêng (data/app.db).":
        "Disconnected from the shared database: this machine is back on its own data (data/app.db).",
    "🔗 Nối máy này vào CSDL chung của team (Supabase)": "🔗 Connect this machine to the team's shared database (Supabase)",
    "Dán địa chỉ CSDL admin gửi cho bạn (Supabase → Connect → Session pooler → URI, đã điền mật khẩu). "
    "Địa chỉ chỉ lưu ở data/local.json trên máy này. Nối xong, app chuyển sang màn hình đăng nhập: "
    "dùng tài khoản admin cấp cho bạn trên website.":
        "Paste the database address your admin sent you (Supabase → Connect → Session pooler → URI, with the password filled in). "
        "It is stored only in data/local.json on this machine. Once connected, the app switches to the sign-in screen: "
        "use the account your admin created for you on the website.",
    "Địa chỉ CSDL (Postgres URI)": "Database address (Postgres URI)",
    "🔌 Kiểm tra kết nối": "🔌 Test connection",
    "💾 Lưu và dùng CSDL chung": "💾 Save and use the shared database",
    "Chưa có địa chỉ CSDL: dán địa chỉ vào ô trên rồi bấm lại.": "No database address yet: paste it into the box above, then click again.",
    "Server team": "Team server",
    "chưa chạy": "not running",
    "đang chạy ở cổng {port}": "running on port {port}",
    "lỗi: {error}": "error: {error}",
    "App đang chạy **chế độ team**. Gửi cho thành viên cùng mạng LAN địa chỉ: **`{url}`**":
        "The app is running in **team mode**. Send members on the same LAN this address: **`{url}`**",
    "API nhận kết quả từ bản local: `{url}` ({status})": "API receiving results from local apps: `{url}` ({status})",
    "Card mạng": "Network adapter",
    "Mô tả": "Description",
    "Dùng cho team?": "Use for team?",
    "⚠️ IP VPN — máy khác thường KHÔNG vào được": "⚠️ VPN IP — other machines usually can NOT reach it",
    "✅ dùng được nếu cùng mạng": "✅ works on the same network",
    "Cổng API đồng bộ": "Sync API port",
    "Đổi cổng cần khởi động lại app.": "Changing the port requires restarting the app.",
    "Máy server phải đang bật, cửa sổ run-team.bat phải mở, và thành viên phải cùng mạng LAN với máy server. "
    "Thành viên làm việc từ xa qua VPN thường không vào được máy của nhau — khi đó cần server riêng (VM nội bộ do IT cấp).":
        "The server machine must be on, the run-team.bat window must stay open, and members must be on the same LAN as the server machine. "
        "Members working remotely over VPN usually cannot reach each other's machines — that needs a dedicated server (an internal VM from IT).",
    "Bản local này có thể tự đẩy mọi kết quả đã lưu lên server team. Admin của team cấp token ở trang Thành viên.":
        "This local app can push every saved result to the team server automatically. The team admin issues tokens on the Members page.",
    "Địa chỉ API server team": "Team server API address",
    "Token đồng bộ": "Sync token",
    "🔌 Kiểm tra kết nối server team": "🔌 Test team server connection",
    "Thư mục lưu kết quả": "Output folder",
    "Thư mục gốc": "Root folder",
    "Case nạp lỗi lưu vào <thư mục gốc>\\Payment-Error-Cases\\<YYYY-MM-DD>\\":
        "Failed top-up cases are saved to <root folder>\\Payment-Error-Cases\\<YYYY-MM-DD>\\",
    "Trình duyệt & NC tool (dùng chung mọi game)": "Browser & NC tool (shared by all games)",
    "Trình duyệt": "Browser",
    "msedge = Microsoft Edge có sẵn trên Windows (không cần tải thêm).": "msedge = Microsoft Edge, built into Windows (nothing to download).",
    "Mặc định khi tạo gói NC": "Default when creating NC packages",
    "Tôi tự bấm Register": "I click Register myself",
    "App tự bấm Register": "The app clicks Register",
    "Mỗi game có app group riêng trên NC tool, tiền tố Store Product Key, URL MyTool, bảng Item ID, master và lịch sử riêng.":
        "Each game has its own NC tool app group, Store Product Key prefix, MyTool URLs, Item ID table, master and history.",
    "Game mặc định khi mở app": "Default game when opening the app",
    "Ngôn ngữ mặc định": "Default language",
    "Áp dụng cho trình duyệt chưa tự chọn ngôn ngữ ở thanh bên (ô 🌐 Language).":
        "Applies to browsers that have not picked a language in the sidebar (the 🌐 Language box).",
    "Sửa thông số của game": "Edit game settings",
    "➕ Thêm game mới": "➕ Add new game",
    "Tên game (vd Journey of Monarch SEA)": "Game name (e.g. Journey of Monarch SEA)",
    "Tạo game": "Create game",
    "Đã tạo game {name}. Điền app group, tiền tố Store Product Key và URL MyTool rồi bấm Lưu cài đặt.":
        "Created game {name}. Fill in the app group, Store Product Key prefix and MyTool URLs, then click Save settings.",
    "📋 Lấy danh sách app group từ NC tool": "📋 Fetch app groups from NC tool",
    "Đang đọc danh sách app group": "Reading app group list",
    "App group trên NC tool": "App group on NC tool",
    "Dùng app group này cho game": "Use this app group for the game",
    "Tên game": "Game name",
    "Tiền tố Store Product Key": "Store Product Key prefix",
    "Store Product Key = tiền tố + Product Key trong master": "Store Product Key = prefix + Product Key from master",
    "Tên app group trên NC tool": "App group name on NC tool",
    "**MyTool — Sold Package (shop LIVE)** — mở từng shop trên MyTool rồi dán URL trang Sold Package vào đây":
        "**MyTool — Sold Package (LIVE shops)** — open each shop on MyTool and paste its Sold Package page URL here",
    "Xoá game này": "Delete this game",
    "Chỉ xoá thông số cấu hình. Lịch sử, bảng Item ID và master của game vẫn được giữ trong CSDL/thư mục data.":
        "Only the configuration is deleted. The game's history, Item ID table and master stay in the database/data folder.",
    "Xác nhận xoá": "Confirm delete",
    "🗑 Xoá game": "🗑 Delete game",
    "🌐 Kiểm tra kết nối từ máy này tới các tool": "🌐 Test connections from this machine to the tools",
    "Đang kiểm tra...": "Checking...",
    "Kết quả": "Result",
    "Máy đang dùng proxy hệ thống — trình duyệt có thể vẫn vào được dù kiểm tra DNS ở đây báo lỗi.":
        "This machine uses a system proxy — the browser may still get through even if the DNS check here fails.",
    "💾 Lưu cài đặt": "💾 Save settings",
    "Đã lưu.": "Saved.",
    "🧪 Test kết nối AI": "🧪 Test AI connection",
    "Đang gọi AI...": "Calling AI...",
    "{provider} trả lời: {reply}": "{provider} replied: {reply}",
    "🔐 Mở trình duyệt để đăng nhập SSO": "🔐 Open browser to sign in to SSO",
    "Đăng nhập NC tool & MyTool (đóng trình duyệt khi xong)": "Sign in to NC tool & MyTool (close the browser when done)",
    "Chế độ: **{mode}** · Dữ liệu app: `{path}`": "Mode: **{mode}** · App data: `{path}`",
    # nhật ký thay đổi (store.log) — hiển thị qua common.df
    "thêm game": "add game",
    "xoá game": "delete game",
    "sửa cài đặt": "edit settings",

    # ---- views/users.py -------------------------------------------------------------
    "👥 Quản lý thành viên": "👥 Members",
    "Cấp tài khoản, phân quyền, khoá tài khoản và cấp token đồng bộ cho bản local.":
        "Issue accounts, assign roles, lock accounts and issue sync tokens for local apps.",
    "Chỉ admin mới vào được trang này.": "Only admins can open this page.",
    "- **Admin**: toàn quyền, quản lý thành viên và cài đặt, sửa/xoá mọi bản ghi.\n"
    "- **Thành viên**: chạy function, lưu lịch sử, sửa dữ liệu dùng chung, sửa/xoá bản ghi của mình.\n"
    "- **Chỉ xem**: xem kết quả và lịch sử, tải file.":
        "- **Admin**: full access, manages members and settings, can edit/delete any record.\n"
        "- **Member**: runs functions, saves history, edits shared data, edits/deletes own records.\n"
        "- **Viewer**: views results and history, downloads files.",
    "Tên hiển thị": "Display name",
    "Vai trò": "Role",
    "Đang hoạt động": "Active",
    "Đã khoá": "Locked",
    "Có": "Yes",
    "Tạo lúc": "Created at",
    "**Thêm thành viên**": "**Add member**",
    "Mật khẩu ban đầu (tối thiểu 8 ký tự)": "Initial password (at least 8 characters)",
    "➕ Thêm": "➕ Add",
    "Đã tạo tài khoản {name}. Gửi username + mật khẩu cho thành viên qua kênh riêng.":
        "Created account {name}. Send the username + password to the member over a private channel.",
    "**Sửa thành viên**": "**Edit member**",
    "Chưa có thành viên nào.": "No members yet.",
    "Chọn thành viên": "Select member",
    "Đây là admin duy nhất — không đổi vai trò/khoá được.": "This is the only admin — its role cannot be changed and it cannot be locked.",
    "💾 Lưu": "💾 Save",
    "Đã cập nhật {user}.": "Updated {user}.",
    "Đặt lại mật khẩu": "Reset password",
    "🔑 Đặt lại mật khẩu": "🔑 Reset password",
    "Đã đặt lại mật khẩu.": "Password reset.",
    "🔐 Cấp token đồng bộ mới": "🔐 Issue new sync token",
    "Dùng cho bản local của thành viên đẩy kết quả lên server. Cấp mới sẽ vô hiệu token cũ.":
        "Lets the member's local app push results to the server. Issuing a new one revokes the old token.",
    "Token chỉ hiện một lần — copy ngay và gửi riêng cho thành viên. Họ dán vào Cài đặt → Server team ở bản local.":
        "The token is shown only once — copy it now and send it privately to the member. They paste it into Settings → Team server in their local app.",

    # ---- views/shared_data.py -------------------------------------------------------
    "🗂 Dữ liệu dùng chung": "🗂 Shared data",
    "Một người sửa, cả team dùng bản mới: bảng Item ID và file master của game đang chọn.":
        "One person edits, the whole team uses the update: the Item ID table and master file of the selected game.",
    "Bảng Item ID ({group})": "Item ID table ({group})",
    "File master": "Master file",
    "Tìm item": "Search items",
    "Tên trên tool": "Name on tool",
    "Tên khác trong Excel (alias)": "Other names in Excel (aliases)",
    "Sửa bởi": "Edited by",
    "{n} item của {game}. Mỗi game có bộ Item ID riêng. Tra ID mới ở trang Tạo gói NC → Tra Item lookup.":
        "{n} items for {game}. Each game has its own Item IDs. Look up new IDs on the Create NC packages page → Item lookup.",
    "**Thêm / sửa item — {game}**": "**Add / edit item — {game}**",
    "Item ID (trùng ID có sẵn = sửa)": "Item ID (an existing ID = edit)",
    "Tên trên tool (vd Eva's Seal Chest (Bound))": "Name on tool (e.g. Eva's Seal Chest (Bound))",
    "Alias, cách nhau bởi dấu phẩy (tên viết tắt trong Excel)": "Aliases, comma-separated (short names used in Excel)",
    "💾 Lưu item": "💾 Save item",
    "Cần Item ID và tên.": "Item ID and name are required.",
    "Đã lưu item {item_id} cho {game}.": "Saved item {item_id} for {game}.",
    "**Xoá item**": "**Delete item**",
    "Chọn item": "Select item",
    "🗑 Xoá item": "🗑 Delete item",
    "**Đang dùng ({game}):** `{name}` — tải lên {at}": "**In use ({game}):** `{name}` — uploaded {at}",
    "bởi {user}": "by {user}",
    "Chưa có master của {game}. Tải lên ở bất kỳ function nào.": "No master for {game} yet. Upload one from any function.",
    "**Các phiên bản đã tải lên**": "**Uploaded versions**",
    "⬇ Tải": "⬇ Download",
    "Dùng lại": "Use again",
    "Đã đặt {name} làm master hiện hành của {game}.": "Set {name} as the current master for {game}.",
}
