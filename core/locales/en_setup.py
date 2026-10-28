"""Bản dịch tiếng Anh — kiểm tra máy sau đăng nhập và hướng dẫn cài agent (ui/agent_setup.py, ui/guide_art.py)."""

EN = {
    # ---- ui/agent_setup.py: kiểm tra máy -------------------------------------------------
    "Bạn đang mở website trên máy không phải Windows: xem và sửa dữ liệu bình thường; các nút NC tool / MyTool "
    "cần một máy Windows đã cài agent.":
        "You are on a non-Windows device: you can view and edit data as usual; the NC tool / MyTool buttons need a Windows "
        "machine with the agent installed.",
    "Máy **{host}** đã đủ điều kiện: agent đang chạy, có Microsoft Edge và vào được NC tool. Các nút NC tool / "
    "MyTool đã dùng được.":
        "**{host}** is ready: the agent is running, Microsoft Edge is installed and NC tool is reachable. The NC tool / "
        "MyTool buttons are ready to use.",
    "⏳ Đang bật agent trên máy bạn… Trình duyệt hỏi mở **L2M Ops Agent** thì tick **Always allow** rồi bấm **Open**.":
        "⏳ Starting the agent on your machine… If the browser asks to open **L2M Ops Agent**, tick **Always allow** and click **Open**.",
    "Cài agent cho máy này": "Install the agent on this machine",
    "Máy Windows 10/11": "Windows 10/11 PC",
    "trình duyệt này không chạy trên Windows": "this browser is not running on Windows",
    "Microsoft Edge (có sẵn trên Windows)": "Microsoft Edge (built into Windows)",
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
    "Đã thấy agent trên máy **{host}**, nhưng còn thiếu vài bước — bấm **Kiểm tra máy** ở thanh bên để xem.":
        "Found the agent on **{host}**, but a few steps are missing — click **Check machine** in the sidebar to see them.",
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
    "Đang tìm agent…": "Looking for the agent…",
    "Máy {host} cần thêm vài bước": "{host} needs a few more steps",
    "Agent vừa tắt. Bấm **▶ Bật agent** (máy đã cài) hoặc mở lại agent.bat.":
        "The agent just stopped. Click **▶ Start agent** (if installed on this machine) or reopen agent.bat.",
    "Agent đang chạy trên máy **{host}**, nhưng còn thiếu:": "The agent is running on **{host}**, but something is missing:",
    "Agent đang chạy bản cũ": "The agent is an old version",
    "Tải agent bản mới, giải nén đè lên thư mục agent cũ rồi mở lại agent.bat (agent cũ tự tắt).":
        "Download the new agent, unzip it over the old agent folder and reopen agent.bat (the old agent stops by itself).",
    "Chưa vào được NC tool": "NC tool is not reachable",
    "Bật VPN công ty trên máy {host} rồi bấm Kiểm tra lại. Nếu VPN đã bật mà vẫn báo: kiểm tra địa chỉ NC "
    "tool ở trang Cài đặt.":
        "Turn on the company VPN on {host}, then click Check again. If the VPN is on and this still shows: check the NC tool "
        "address on the Settings page.",
    "Máy {host} chưa có Microsoft Edge": "{host} does not have Microsoft Edge",
    "Thao tác NC tool / MyTool mở Edge để dùng phiên SSO của bạn. Cài Edge rồi bấm Kiểm tra lại.":
        "NC tool / MyTool actions open Edge to use your SSO sign-in. Install Edge, then click Check again.",
    "Tải Microsoft Edge": "Download Microsoft Edge",
    "Agent đang kiểm tra lại máy…": "The agent is re-checking the machine…",
    "Để sau": "Later",
    # ---- ui/auth.py, ui/common.py -------------------------------------------------------
    "Kiểm tra máy": "Check machine",
    "Kiểm tra máy bạn đã đủ điều kiện chạy NC tool / MyTool chưa; thiếu gì sẽ hiện hướng dẫn.":
        "Check whether your machine is ready to run NC tool / MyTool; anything missing comes with instructions.",
    "Hướng dẫn cài agent": "Agent install guide",
    # ---- ui/guide_art.py ---------------------------------------------------------------
    "Đang chạy lệnh": "Running a job",
    "Cần chú ý: mất mạng / có bản mới": "Needs attention: offline / new version",
    # ---- automation/agent.py ------------------------------------------------------------
    "⚠ Không đăng ký được link để website bật agent: {error}": "⚠ Could not register the link the website uses to start the agent: {error}",
}
