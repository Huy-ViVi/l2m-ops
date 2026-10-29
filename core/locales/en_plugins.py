"""Bản dịch tiếng Anh — nền tảng plugin (core/plugins.py, ui/plugin_host.py, views/plugins.py)."""

EN = {
    # app.py, core/store.py (loại bản ghi lịch sử)
    "Plugin của team": "Team plugins",
    "Gửi plugin": "Plugin submission",

    # core/plugins.py — khai báo plugin.toml
    "Thiếu file {file}": "Missing file {file}",
    "{file} viết sai cú pháp TOML: {error}": "{file} has invalid TOML syntax: {error}",
    "id phải là chữ thường không dấu, số hoặc _, 3–32 ký tự, bắt đầu bằng chữ (vd update_tracker)":
        "id must be lowercase ASCII letters, digits or _, 3–32 characters, starting with a letter (e.g. update_tracker)",
    "id '{id}' phải trùng tên thư mục: plugins/{id}/": "id '{id}' must match the folder name: plugins/{id}/",
    "Thiếu trường '{key}' trong {file}": "Missing field '{key}' in {file}",
    "Thiếu 'owners': danh sách tài khoản website của người phụ trách, vd [\"myly\"]":
        "Missing 'owners': website accounts of the people in charge, e.g. [\"myly\"]",
    "'access' chỉ nhận: {values}": "'access' only accepts: {values}",
    "'games' phải là danh sách mã game, vd [\"l2m\"] (để [] = mọi game)":
        "'games' must be a list of game ids, e.g. [\"l2m\"] ([] = every game)",
    "Cần ít nhất một trang: khối [[pages]] có file và title": "At least one page is required: a [[pages]] block with file and title",
    "Trang thứ {n} thiếu 'file' hoặc 'title'": "Page {n} is missing 'file' or 'title'",
    "Trang '{file}' phải là file .py nằm trong thư mục plugin": "Page '{file}' must be a .py file inside the plugin folder",
    "Không thấy file trang '{file}'": "Page file '{file}' not found",
    "Icon '{icon}' không hợp lệ — dùng :material/tên_icon: hoặc một emoji":
        "Icon '{icon}' is invalid — use :material/icon_name: or one emoji",

    # core/plugins.py — kiểm tra code
    "{file}:{line}: import ra ngoài thư mục plugin — chỉ import trong plugins/{id}/":
        "{file}:{line}: import reaches outside the plugin folder — only import within plugins/{id}/",
    "{file}:{line}: chỉ dùng nền tảng qua core.sdk (đang import {names})":
        "{file}:{line}: use the platform only through core.sdk (importing {names})",
    "{file}:{line}: không import code của plugin khác ({module}) — liên kết qua dữ liệu dùng chung":
        "{file}:{line}: do not import another plugin's code ({module}) — link through shared data",
    "{file}:{line}: không dùng {module} trong plugin — {hint}": "{file}:{line}: do not use {module} in a plugin — {hint}",
    "{file}:{line}: thư viện '{module}' chưa có trong requirements.txt của nền tảng — "
    "nhắn admin thêm (kèm phiên bản) hoặc dùng thư viện có sẵn":
        "{file}:{line}: library '{module}' is not in the platform's requirements.txt — "
        "ask the admin to add it (with a version) or use an available library",
    "{file}:{line}: không gọi st.{name} — {hint}": "{file}:{line}: do not call st.{name} — {hint}",
    "{file}:{line}: không đọc biến môi trường — dùng sdk.secret(\"TÊN\")":
        "{file}:{line}: do not read environment variables — use sdk.secret(\"NAME\")",
    "{file}:{line}: key '{key}' phải bắt đầu bằng '{prefix}' (dùng sdk.key(\"…\"))":
        "{file}:{line}: key '{key}' must start with '{prefix}' (use sdk.key(\"…\"))",
    "Tên thư mục không được bắt đầu bằng _ hoặc . (thư mục như vậy bị bỏ qua)":
        "The folder name must not start with _ or . (such folders are skipped)",
    "{file}: không đưa file bí mật / CSDL vào plugin (key để trong secrets, dữ liệu lưu bằng sdk.save)":
        "{file}: do not put secret / database files in a plugin (keys go in secrets, data is saved with sdk.save)",
    "{file}: {size} MB — file trong plugin tối đa {max} MB; dữ liệu lớn lưu bằng sdk.save()":
        "{file}: {size} MB — plugin files are limited to {max} MB; save large data with sdk.save()",
    "{file}: có vẻ chứa {what} — không ghi bí mật vào code, dùng sdk.secret()":
        "{file}: seems to contain {what} — do not write secrets in code, use sdk.secret()",
    "{file}:{line}: lỗi cú pháp Python — {error}": "{file}:{line}: Python syntax error — {error}",
    "Thư mục plugin {size} MB — tối đa {max} MB": "Plugin folder is {size} MB — the limit is {max} MB",
    # gợi ý / loại bí mật (giá trị truyền vào các câu trên)
    "lưu dữ liệu bằng sdk.save() / sdk.load()": "save data with sdk.save() / sdk.load()",
    "việc cần chạy chương trình ngoài sẽ đi qua agent (lộ trình phase 3)":
        "work that runs external programs will go through the agent (roadmap phase 3)",
    "việc cần trình duyệt / VPN sẽ đi qua agent (lộ trình phase 3)": "browser / VPN work will go through the agent (roadmap phase 3)",
    "nền tảng đã gọi st.set_page_config": "the platform already calls st.set_page_config",
    "menu do nền tảng dựng từ plugin.toml": "the platform builds the menu from plugin.toml",
    "địa chỉ CSDL kèm mật khẩu": "a database address with a password",

    # core/plugins.py — kiểm tra zip
    "File zip quá lớn (tối đa {max} MB)": "The zip file is too large (max {max} MB)",
    "Không đọc được file zip": "Could not read the zip file",
    "Zip có đường dẫn ra ngoài thư mục — không nhận": "The zip has paths outside its folder — rejected",
    "Trong zip không có file {file}": "No {file} in the zip",

    # ui/plugin_host.py
    "Plugin **{name}** đang bị lỗi: {error}": "Plugin **{name}** has an error: {error}",
    "Phần còn lại của website vẫn dùng bình thường. Báo cho người phụ trách plugin: {owners}.":
        "The rest of the website still works normally. Tell the plugin owner: {owners}.",
    "Chi tiết lỗi (gửi cho người phụ trách plugin)": "Error details (send to the plugin owner)",

    # views/plugins.py
    "🧩 Plugin của team": "🧩 Team plugins",
    "Mỗi tính năng của thành viên là một plugin trên nền tảng này — cùng đăng nhập, cùng dữ liệu, cùng menu.":
        "Each member's feature is a plugin on this platform — one sign-in, shared data, one menu.",
    "**Thông báo cho cả team** — nền tảng đã nhận plugin (phase 1: đưa app của mọi người lên).  \n"
    "1. Trước khi build / chuyển app của bạn: tải **Bộ khởi đầu** ở tab *Đưa plugin lên*.  \n"
    "2. Đưa AI của bạn đọc **AGENTS.md** và **PLUGIN_GUIDE.md** trong bộ đó, để nó tự làm theo quy định.  \n"
    "3. Chạy thử trên máy, tự kiểm tra, rồi gửi. Quy định đầy đủ ở tab *Quy định*, các bước tiếp theo ở tab *Lộ trình*.":
        "**Announcement for the team** — the platform now accepts plugins (phase 1: bring everyone's apps in).  \n"
        "1. Before building / converting your app: download the **Starter kit** in the *Submit a plugin* tab.  \n"
        "2. Have your AI read **AGENTS.md** and **PLUGIN_GUIDE.md** from that kit so it follows the rules on its own.  \n"
        "3. Try it on your machine, self-check, then submit. Full rules in the *Rules* tab, next steps in the *Roadmap* tab.",
    "Danh sách plugin": "Plugin list",
    "Đưa plugin lên": "Submit a plugin",
    "Quy định (PLUGIN_GUIDE.md)": "Rules (PLUGIN_GUIDE.md)",
    "Lộ trình": "Roadmap",
    "Chưa có plugin nào. Plugin đầu tiên sẽ hiện ở đây và ở menu bên trái.":
        "No plugins yet. The first plugin will appear here and in the left menu.",
    "Mã": "Id",
    "Phụ trách": "Owners",
    "Phiên bản": "Version",
    "Nhóm menu": "Menu group",
    "Bản ghi đã lưu": "Saved records",
    "✅ Đang chạy": "✅ Running",
    "⚠️ {n} lỗi — chưa lên menu": "⚠️ {n} problems — not in the menu",
    "⚠️ {name} — {n} lỗi cần sửa": "⚠️ {name} — {n} problems to fix",
    "Plugin lỗi khai báo (plugin.toml) hoặc vi phạm quy định không được đưa lên menu cho tới khi sửa xong; "
    "plugin lỗi khi chạy chỉ báo lỗi ở trang của nó, phần còn lại vẫn dùng bình thường.":
        "Plugins with a broken plugin.toml or rule violations stay out of the menu until fixed; "
        "a plugin that fails while running only shows the error on its own page, the rest keeps working.",
    "**1. Tải bộ khởi đầu** — code nền tảng chạy được trên máy bạn, plugin mẫu, quy định và hướng dẫn cho AI. "
    "Không chứa địa chỉ CSDL hay dữ liệu của team.":
        "**1. Download the starter kit** — platform code that runs on your machine, a sample plugin, the rules and AI "
        "instructions. It contains no database address or team data.",
    "⬇ Tải bộ khởi đầu làm plugin (.zip)": "⬇ Download the plugin starter kit (.zip)",
    "**2. Làm plugin** theo file BAT-DAU-LAM-PLUGIN.txt trong bộ đó (chép plugin mẫu, nhờ AI viết, chạy thử bằng run.bat).":
        "**2. Build the plugin** following BAT-DAU-LAM-PLUGIN.txt in the kit (copy the sample, ask your AI, try it with run.bat).",
    "**3. Tự kiểm tra** — nén thư mục plugin của bạn (thư mục có plugin.toml) thành .zip rồi tải lên đây. "
    "App chỉ đọc code, không chạy.":
        "**3. Self-check** — zip your plugin folder (the one with plugin.toml) and upload it here. "
        "The app only reads the code, it does not run it.",
    "File .zip của plugin": "Plugin .zip file",
    "✅ Plugin **{name}** (`{id}` v{version}) đạt quy định — {n} trang.":
        "✅ Plugin **{name}** (`{id}` v{version}) meets the rules — {n} pages.",
    "**4. Gửi** — đưa thư mục lên GitHub vào đúng chỗ `plugins/{id}/` (nếu bạn đã được thêm vào kho), "
    "hoặc gửi zip cho admin ngay dưới đây.":
        "**4. Submit** — upload the folder to GitHub at `plugins/{id}/` (if you have been added to the repository), "
        "or send the zip to the admin right below.",
    "Ghi chú cho admin (đổi gì, cần thêm thư viện / secret gì)":
        "Note for the admin (what changed, any library / secret needed)",
    "📤 Gửi plugin cho admin": "📤 Send the plugin to the admin",
    "Gửi plugin {id} v{version}": "Plugin submission {id} v{version}",
    "Đã gửi (bản ghi #{aid} ở trang Lịch sử hoạt động, loại Gửi plugin). Admin sẽ đưa lên.":
        "Sent (record #{aid} in Activity history, type Plugin submission). The admin will publish it.",
    "Plugin chưa đạt — {n} điểm cần sửa:": "The plugin does not pass yet — {n} things to fix:",
    "Admin: plugin gửi lên nằm ở trang Lịch sử hoạt động (loại Gửi plugin) — tải zip, kiểm tra, rồi đưa thư mục "
    "vào plugins/<id>/ trên GitHub.":
        "Admin: submitted plugins are in Activity history (type Plugin submission) — download the zip, review it, then put "
        "the folder in plugins/<id>/ on GitHub.",
    "Chưa có file {file}.": "File {file} is missing.",
    "Tài liệu này viết bằng tiếng Việt.": "This document is written in Vietnamese.",
}
