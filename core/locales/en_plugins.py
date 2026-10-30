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

    "{file}:{line}: không đọc st.secrets — dùng sdk.secret(\"TÊN\")": "{file}:{line}: do not read st.secrets — use sdk.secret(\"NAME\")",
    "{file}:{line}: st.{name} không còn trong Streamlit mới — dùng st.rerun / st.cache_data / st.query_params":
        "{file}:{line}: st.{name} no longer exists in current Streamlit — use st.rerun / st.cache_data / st.query_params",
    "dùng AI chung của team qua sdk.ai()": "use the team's shared AI through sdk.ai()",

    # core/plugins.py — tách câu trả lời của AI
    "Không thấy dòng 'FILE: …' nào — nhờ AI trả lời đúng định dạng ở mục 3 của AI_PROMPT.md":
        "No 'FILE: …' line found — ask your AI to answer in the format of section 3 of AI_PROMPT.md",
    "{file}: không thấy khối code chứa nội dung file": "{file}: no code block with the file content found",
    "Trong câu trả lời không có file {file}": "The answer has no {file} file",
    "{file}: nằm ngoài thư mục plugins/{id}/ — bỏ qua": "{file}: outside the plugins/{id}/ folder — skipped",

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
    "**Thông báo cho cả team** — nền tảng đã nhận plugin (phase 1: đưa app của mọi người lên), làm bằng **AI nào cũng được** "
    "(ChatGPT, Gemini, Copilot, Claude, Cursor…).  \n"
    "1. Tab **Bắt đầu**: tải **AI_PROMPT.md**, đưa cho AI của bạn kèm mô tả app.  \n"
    "2. Tab **Kiểm tra & gửi**: dán câu trả lời của AI để kiểm tra; đạt thì gửi cho admin.\n\n"
    "Quy định đầy đủ ở tab *Quy định*, các bước tiếp theo của cả team ở tab *Lộ trình*.":
        "**Announcement for the team** — the platform now accepts plugins (phase 1: bring everyone's apps in), built with "
        "**any AI** (ChatGPT, Gemini, Copilot, Claude, Cursor…).  \n"
        "1. **Get started** tab: download **AI_PROMPT.md** and give it to your AI along with a description of your app.  \n"
        "2. **Check & submit** tab: paste the AI's answer to check it; once it passes, send it to the admin.\n\n"
        "Full rules in the *Rules* tab, the team's next steps in the *Roadmap* tab.",
    "Bắt đầu": "Get started",
    "Kiểm tra & gửi": "Check & submit",
    "Danh sách plugin": "Plugin list",
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
    "⬇ Tải AI_PROMPT.md": "⬇ Download AI_PROMPT.md",
    "Một file cho mọi AI: quy định, công cụ của nền tảng, plugin mẫu và cách trả lời để nền tảng tự tách file. "
    "Đính kèm vào AI (hoặc dán toàn bộ nội dung), rồi mô tả app của bạn.":
        "One file for any AI: the rules, the platform tools, a sample plugin and the answer format the platform splits into "
        "files. Attach it to your AI (or paste all of it), then describe your app.",
    "Xem / sao chép toàn bộ prompt ({n} ký tự)": "View / copy the whole prompt ({n} characters)",
    "Đã đọc {n} file: {files}": "Read {n} files: {files}",
    "✅ Plugin **{name}** (`{id}` v{version}) đạt quy định — {n} trang.":
        "✅ Plugin **{name}** (`{id}` v{version}) meets the rules — {n} pages.",
    "⬇ Tải plugin (.zip) để chạy thử trên máy": "⬇ Download the plugin (.zip) to try it on your machine",
    "**Gửi** — gửi cho admin ngay dưới đây; hoặc nếu bạn đã được thêm vào kho code, đưa thư mục vào đúng chỗ "
    "`plugins/{id}/`.":
        "**Submit** — send it to the admin right below; or, if you have been added to the code repository, put the folder at "
        "`plugins/{id}/`.",
    "Ghi chú cho admin (đổi gì, cần thêm thư viện / secret gì)":
        "Note for the admin (what changed, any library / secret needed)",
    "📤 Gửi plugin cho admin": "📤 Send the plugin to the admin",
    "Gửi plugin {id} v{version}": "Plugin submission {id} v{version}",
    "Đã gửi (bản ghi #{aid} ở trang Lịch sử hoạt động, loại Gửi plugin). Admin sẽ đưa lên.":
        "Sent (record #{aid} in Activity history, type Plugin submission). The admin will publish it.",
    "Plugin chưa đạt — {n} điểm cần sửa. Sao chép danh sách dưới, gửi lại cho AI: "
    "\"Công cụ kiểm tra báo các lỗi sau, sửa hết và trả lại toàn bộ file:\"":
        "The plugin does not pass yet — {n} things to fix. Copy the list below and send it back to your AI: "
        "\"The checker reports these problems, fix them all and return every file:\"",
    "**Dán câu trả lời của AI** (AI dạng chat) — dán toàn bộ, từ đầu tới dòng END OF FILES. App chỉ đọc code, không chạy.":
        "**Paste your AI's answer** (chat AIs) — paste all of it, down to the END OF FILES line. The app only reads the code, "
        "it does not run it.",
    "Dán câu trả lời của AI": "Paste your AI's answer",
    "🔍 Kiểm tra": "🔍 Check",
    "**Hoặc tải lên file .zip** của thư mục plugin (thư mục có plugin.toml) — khi làm bằng Bộ khởi đầu / AI làm việc trên thư mục.":
        "**Or upload a .zip** of the plugin folder (the one with plugin.toml) — when working with the Starter kit / a folder-based AI.",
    "File .zip của plugin": "Plugin .zip file",
    "**Bộ khởi đầu** — chạy thử plugin trên máy bạn (run.bat), tách câu trả lời của AI thành file (make-plugin.bat), "
    "dùng với AI làm việc trên thư mục (Cursor, Claude Code, Copilot, Codex, Gemini CLI). "
    "Không chứa địa chỉ CSDL hay dữ liệu của team.":
        "**Starter kit** — try your plugin on your machine (run.bat), split an AI answer into files (make-plugin.bat), and use "
        "it with folder-based AIs (Cursor, Claude Code, Copilot, Codex, Gemini CLI). It contains no database address or team data.",
    "⬇ Tải bộ khởi đầu làm plugin (.zip)": "⬇ Download the plugin starter kit (.zip)",
    "Admin: plugin gửi lên nằm ở trang Lịch sử hoạt động (loại Gửi plugin) — tải zip, kiểm tra, rồi đưa thư mục "
    "vào plugins/<id>/ trên GitHub.":
        "Admin: submitted plugins are in Activity history (type Plugin submission) — download the zip, review it, then put "
        "the folder in plugins/<id>/ on GitHub.",
    "Chưa có file {file}.": "File {file} is missing.",
    "Tài liệu viết bằng tiếng Anh để cả team, kể cả thành viên nước ngoài, cùng đọc.":
        "This document is in English so the whole team, including international members, can read it.",
}
