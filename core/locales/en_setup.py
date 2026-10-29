"""Bản dịch tiếng Anh — kiểm tra máy sau đăng nhập và hướng dẫn cài agent (ui/agent_setup.py, ui/guide_art.py)."""

EN = {
    # ---- ui/agent_setup.py: kiểm tra máy -------------------------------------------------
    "Bạn đang mở website trên máy không phải Windows: xem và sửa dữ liệu bình thường; các nút NC tool / MyTool "
    "cần một máy Windows đã cài agent.":
        "You are on a non-Windows device: you can view and edit data as usual; the NC tool / MyTool buttons need a Windows "
        "machine with the agent installed.",
    "Máy **{host}** đã đủ điều kiện: agent đang chạy, có {browser} và vào được NC tool. Các nút NC tool / MyTool "
    "đã dùng được.":
        "**{host}** is ready: the agent is running, {browser} is installed and NC tool is reachable. The NC tool / MyTool "
        "buttons are ready to use.",
    "⏳ Agent đang kiểm tra {browser} trên máy {host}…": "⏳ The agent is checking {browser} on {host}…",
    "⏳ Đang bật agent trên máy bạn… Trình duyệt hỏi mở **L2M Ops Agent** thì tick **Always allow** rồi bấm "
    "**Open**. Không thấy trình duyệt hỏi: bấm nút dưới đây.":
        "⏳ Starting the agent on your machine… If the browser asks to open **L2M Ops Agent**, tick **Always allow** and click "
        "**Open**. No prompt? Click the button below.",
    "⏳ Đã gửi yêu cầu kiểm tra lúc {time} — đang chờ agent trả lời (tối đa {n} giây)…":
        "⏳ Check requested at {time} — waiting for the agent to answer (up to {n} seconds)…",
    "Agent vừa kiểm tra lại máy {host} lúc {time}.": "The agent re-checked {host} at {time}.",
    "Agent trên máy {host} chưa trả lời sau {n} giây. Bấm Kiểm tra lại lần nữa; vẫn vậy thì mở lại agent.bat "
    "trên máy đó.":
        "The agent on {host} did not answer within {n} seconds. Click Check again once more; if it still fails, reopen agent.bat "
        "on that machine.",
    "Chưa thấy agent bản mới báo về. Giải nén bản mới đè lên thư mục agent cũ rồi mở lại agent.bat.":
        "The new agent has not reported in yet. Unzip the new version over the old agent folder and reopen agent.bat.",
    "Chưa thấy agent báo về sau {n} giây. Xem chấm tròn ở khay hệ thống (góc phải thanh tác vụ); chưa có thì "
    "làm theo các bước bên dưới.":
        "No agent reported in within {n} seconds. Look for the dot in the system tray (right end of the taskbar); if it is not "
        "there, follow the steps below.",
    "Agent trên máy **{host}** là bản cũ: website chưa bật được và chưa kiểm tra được máy. Tải agent bản mới "
    "bên dưới, giải nén đè lên thư mục agent cũ rồi mở **agent.bat** một lần — từ lần sau website tự bật agent.":
        "The agent on **{host}** is an old version: the website cannot start it or check the machine. Download the new agent "
        "below, unzip it over the old agent folder and open **agent.bat** once — after that the website starts the agent itself.",
    "Đã thấy agent trên máy **{host}**, nhưng còn thiếu vài bước.": "Found the agent on **{host}**, but a few steps are missing.",
    "Xem các bước còn thiếu": "See the missing steps",
    "Cài agent cho máy này": "Install the agent on this machine",
    "Máy Windows 10/11": "Windows 10/11 PC",
    "trình duyệt này không chạy trên Windows": "this browser is not running on Windows",
    "Microsoft Edge (có sẵn trên Windows) hoặc Google Chrome — chọn ở ô Trình duyệt, thanh "
    "bên trái":
        "Microsoft Edge (built into Windows) or Google Chrome — pick it in the Browser box in the sidebar",
    "VPN công ty khi chạy NC tool / MyTool": "Company VPN when running NC tool / MyTool",
    "Internet ở lần cài đầu (tự tải Python ~15 MB + thư viện)": "Internet for the first install (downloads Python ~15 MB + libraries)",
    "Không cần quyền admin, không cần cài Python trước": "No admin rights needed, no need to install Python first",
    "Bấm **⬇ Tải agent cho máy này** (nút ở trên hoặc ở thanh bên trái). File zip đã có sẵn tài khoản của bạn — "
    "không gửi cho người khác.":
        "Click **⬇ Download agent for this machine** (the button above or in the sidebar). The zip already contains your account "
        "— do not send it to anyone else.",
    "Nút tải agent ở thanh bên trái website": "The download agent button in the website sidebar",
    "Mở thư mục Downloads, chuột phải file zip → **Extract All…** (Giải nén tất cả) → **Extract**.":
        "Open your Downloads folder, right-click the zip → **Extract All…** → **Extract**.",
    "Giải nén file zip": "Extract the zip file",
    "Mở thư mục vừa giải nén, nháy đúp **agent.bat**.": "Open the extracted folder and double-click **agent.bat**.",
    "Nháy đúp agent.bat": "Double-click agent.bat",
    "Nếu Windows hiện **Windows protected your PC**: bấm **More info** → **Run anyway**. Agent không có chữ ký số "
    "nên Windows hỏi lại một lần.":
        "If Windows shows **Windows protected your PC**: click **More info** → **Run anyway**. The agent is not digitally signed, "
        "so Windows asks once.",
    "Hộp SmartScreen của Windows": "The Windows SmartScreen dialog",
    "Lần đầu agent tự tải Python + thư viện (vài phút, cần Internet). Xong thì cửa sổ tự đóng — không cần làm gì thêm.":
        "The first run downloads Python + libraries (a few minutes, needs Internet). The window closes by itself when done — "
        "nothing else to do.",
    "Cửa sổ cài đặt agent": "The agent setup window",
    "Agent chạy ngầm: chấm tròn xanh ở khay hệ thống (bấm **^** nếu không thấy). Tự bật cùng Windows; bấm vào chấm "
    "tròn để xem cửa sổ log.":
        "The agent runs in the background: a green dot in the system tray (click **^** if you do not see it). It starts with "
        "Windows; click the dot to see the log window.",
    "Chấm tròn của agent ở khay hệ thống": "The agent's dot in the system tray",
    "Lần sau, khi agent đang tắt, website tự bật nó: trình duyệt hỏi mở **L2M Ops Agent** → tick **Always allow** → "
    "**Open**.":
        "Next time, if the agent is off, the website starts it: the browser asks to open **L2M Ops Agent** → tick **Always allow** "
        "→ **Open**.",
    "Trình duyệt hỏi mở L2M Ops Agent": "The browser asking to open L2M Ops Agent",
    "Đã thấy agent trên máy **{host}**: máy đã đủ điều kiện chạy NC tool / MyTool.":
        "Found the agent on **{host}**: the machine is ready to run NC tool / MyTool.",
    "Đóng": "Close",
    "Chưa bật được agent trên máy này. Máy này đã cài agent: bấm **▶ Bật agent** bên dưới (trình duyệt hỏi thì "
    "chọn Open). Chưa cài hoặc đây là máy khác: làm theo các bước bên dưới.":
        "Could not start the agent on this machine. If it is installed here: click **▶ Start agent** below (choose Open if the "
        "browser asks). If not installed, or this is another machine: follow the steps below.",
    "Thao tác NC tool / MyTool chạy ngay trên máy bạn (cần VPN công ty và phiên SSO của bạn) qua một agent nhỏ. "
    "Cài một lần, khoảng 3 phút.":
        "NC tool / MyTool actions run on your own machine (they need the company VPN and your SSO sign-in) through a small agent. "
        "Install it once, about 3 minutes.",
    "▶ Bật agent": "▶ Start agent",
    "Máy {host} cần thêm vài bước": "{host} needs a few more steps",
    "Máy {host} đã đủ điều kiện": "{host} is ready",
    "Agent vừa tắt. Bấm **▶ Bật agent** (máy đã cài) hoặc mở lại agent.bat.":
        "The agent just stopped. Click **▶ Start agent** (if installed on this machine) or reopen agent.bat.",
    "Agent đang chạy trên máy **{host}**, nhưng còn thiếu:": "The agent is running on **{host}**, but something is missing:",
    "Agent đang chạy bản cũ": "The agent is an old version",
    "Tải agent bản mới, giải nén đè lên thư mục agent cũ rồi mở lại agent.bat (agent cũ tự tắt).":
        "Download the new agent, unzip it over the old agent folder and reopen agent.bat (the old agent stops by itself).",
    "Chưa vào được NC tool": "NC tool is not reachable",
    "Bật VPN công ty trên máy {host}. Agent tự thử lại mỗi 10 giây: vào được NC tool là hộp này tự chuyển "
    "sang đủ điều kiện, không cần bấm gì. Nếu VPN đã bật mà vẫn báo: kiểm tra địa chỉ NC tool ở trang Cài "
    "đặt.":
        "Turn on the company VPN on {host}. The agent retries every 10 seconds: once NC tool is reachable this box turns ready "
        "by itself, no need to click anything. If the VPN is on and this still shows: check the NC tool address on the "
        "Settings page.",
    "Máy {host} chưa có {browser}": "{host} does not have {browser}",
    "Thao tác NC tool / MyTool mở {browser} để dùng phiên SSO của bạn. Cài {browser}, hoặc chọn trình duyệt "
    "khác ở ô Trình duyệt (thanh bên trái).":
        "NC tool / MyTool actions open {browser} to use your SSO sign-in. Install {browser}, or pick another browser in the "
        "Browser box (sidebar).",
    "Tải {browser}": "Download {browser}",
    "Chromium của Playwright không cài sẵn cùng agent — nên chọn Microsoft Edge hoặc Google Chrome.":
        "Playwright's Chromium is not installed with the agent — pick Microsoft Edge or Google Chrome instead.",
    "Để sau": "Later",
    # ---- ui/auth.py, ui/common.py -------------------------------------------------------
    "Kiểm tra máy": "Check machine",
    "Kiểm tra máy bạn đã đủ điều kiện chạy NC tool / MyTool chưa; thiếu gì sẽ hiện hướng dẫn.":
        "Check whether your machine is ready to run NC tool / MyTool; anything missing comes with instructions.",
    "Hướng dẫn cài agent": "Agent install guide",
    "Theo team ({browser})": "Team default ({browser})",
    "Trình duyệt mở NC tool / MyTool trên máy của bạn (chỉ áp dụng cho tài khoản của bạn). Đổi trình duyệt "
    "thì đăng nhập SSO lại một lần trong trình duyệt mới.":
        "The browser that opens NC tool / MyTool on your machine (applies to your account only). After switching, sign in "
        "to SSO once in the new browser.",
    # ---- ui/guide_art.py ---------------------------------------------------------------
    "Đang chạy lệnh": "Running a job",
    "Cần chú ý: mất mạng / có bản mới": "Needs attention: offline / new version",
    # ---- automation/agent.py ------------------------------------------------------------
    "⚠ Không đăng ký được link để website bật agent: {error}": "⚠ Could not register the link the website uses to start the agent: {error}",
    "✓ Vào được NC tool.": "✓ NC tool is reachable.",
    "⚠ Chưa vào được NC tool — bật VPN công ty.": "⚠ NC tool is not reachable — turn on the company VPN.",
    "Website yêu cầu kiểm tra lại máy.": "The website asked to re-check this machine.",
}
