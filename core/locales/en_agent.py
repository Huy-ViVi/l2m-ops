"""Bản dịch tiếng Anh — chạy thao tác tự động từ website qua agent (ui/common.py, automation/agent.py)."""

EN = {
    # ---- ui/common.py (website gửi lệnh) ---------------------------------------------
    "Chưa thấy agent trên máy bạn. Thao tác NC tool / MyTool cần VPN công ty và phiên SSO của chính bạn, nên website "
    "gửi lệnh về máy bạn chạy. Lần đầu: bấm **⬇ Tải agent cho máy này**, giải nén, nháy đúp **agent.bat** (tự cài "
    "mọi thứ, có sẵn tài khoản của bạn), bật VPN và giữ cửa sổ đó mở. Tải lại trang này sau vài giây.":
        "No agent found on your machine. NC tool / MyTool actions need the company VPN and your own SSO sign-in, so the website "
        "sends them to your machine. First time: click **⬇ Download agent for this machine**, unzip it, double-click **agent.bat** "
        "(it installs everything and already has your account), turn on the VPN and keep that window open. Reload this page after a few seconds.",
    "🟠 Agent đang chạy bản code khác website: tải agent bản mới, giải nén đè lên thư mục agent cũ "
    "rồi mở lại agent.bat.":
        "🟠 The agent runs a different code version than the website: download the new agent, unzip it over the old agent folder "
        "and reopen agent.bat.",
    "⬇ Tải agent cho máy này": "⬇ Download agent for this machine",
    "Giải nén rồi nháy đúp agent.bat: lần đầu tự cài Python + thư viện; đã có sẵn địa chỉ CSDL chung "
    "và tài khoản của bạn. Không gửi file này cho người khác.":
        "Unzip it and double-click agent.bat: the first run installs Python + libraries; it already contains the shared database "
        "address and your account. Do not send this file to anyone else.",
    "🟢 Thao tác tự động chạy trên máy **{host}** (agent của tài khoản **{user}**). Không phải máy của bạn? "
    "Bạn đang dùng tài khoản của người khác: đăng xuất rồi đăng nhập bằng tài khoản riêng.":
        "🟢 Automation runs on **{host}** (the agent of account **{user}**). Not your machine? You are using someone else's "
        "account: sign out and sign in with your own.",
    "🟢 Agent: máy **{host}**": "🟢 Agent: **{host}**",
    "⚪ Chưa bật agent (agent.bat)": "⚪ Agent not running (agent.bat)",
    "Nút NC tool / MyTool trên website chạy trên máy đang mở agent.bat của tài khoản này. "
    "Mỗi người dùng tài khoản riêng, nếu không lệnh sẽ chạy trên máy người khác.":
        "NC tool / MyTool buttons on the website run on the machine where this account's agent.bat is open. "
        "Everyone should use their own account, otherwise actions run on someone else's machine.",
    "Trình duyệt đã bị đóng trước khi thao tác xong. Chạy lại và giữ cửa sổ Edge mở tới khi log báo xong "
    "(nếu cửa sổ bật lên trên máy người khác: bạn đang dùng tài khoản của họ).":
        "The browser was closed before the action finished. Run it again and keep the Edge window open until the log says done "
        "(if the window popped up on someone else's machine, you are using their account).",
    "Chưa thấy agent trên máy bạn.": "No agent found on your machine.",
    "Chạy trên máy **{host}** (agent của {user}) — giữ trang này mở tới khi xong.":
        "Running on **{host}** ({user}'s agent) — keep this page open until it finishes.",
    "Đang chờ agent nhận lệnh…": "Waiting for the agent to pick up the job…",
    "Lệnh đã bị huỷ hoặc hết hạn trước khi agent chạy.": "The job was cancelled or expired before the agent ran it.",
    "Agent trên máy {host} không nhận lệnh. Kiểm tra cửa sổ agent.bat còn mở và máy còn mạng, rồi bấm lại.":
        "The agent on {host} did not pick up the job. Check that the agent.bat window is still open and the machine is online, then try again.",
    "Mất liên lạc với agent trên máy {host} (cửa sổ agent bị đóng hoặc máy mất mạng).":
        "Lost contact with the agent on {host} (the agent window was closed or the machine went offline).",
    "Quá thời gian chờ agent.": "Timed out waiting for the agent.",
    # ---- automation/agent.py (cửa sổ agent.bat) -----------------------------------------
    "Đăng nhập một lần bằng tài khoản L2M Ops của bạn — lệnh bạn bấm trên website sẽ chạy trên máy này.":
        "Sign in once with your L2M Ops account — actions you click on the website will run on this machine.",
    "Mật khẩu: ": "Password: ",
    "Sai username hoặc mật khẩu.": "Wrong username or password.",
    "✓ Đã kết nối lại CSDL chung.": "✓ Reconnected to the shared database.",
    "⚠ Mất kết nối CSDL chung: {error} — đang thử lại…": "⚠ Lost connection to the shared database: {error} — retrying…",
    "Lệnh đã bị huỷ trên website.": "The job was cancelled on the website.",
    "✅ Agent đang chạy cho tài khoản {user} trên máy {host}. Giữ cửa sổ này mở trong lúc dùng website; Ctrl+C để tắt.":
        "✅ Agent running for account {user} on {host}. Keep this window open while using the website; Ctrl+C to stop.",
    "⚠ Không đọc được lệnh từ CSDL chung: {error}": "⚠ Could not read jobs from the shared database: {error}",
    "▶ Lệnh #{id}: {job}": "▶ Job #{id}: {job}",
    "⚠ Chưa gửi được kết quả lệnh #{id}: {error} — thử lại…": "⚠ Could not send the result of job #{id}: {error} — retrying…",
    "■ Lệnh #{id}: xong": "■ Job #{id}: done",
    "■ Lệnh #{id}: lỗi — {error}": "■ Job #{id}: failed — {error}",
    "Máy này chưa nối CSDL chung. Dán địa chỉ CSDL admin gửi cho bạn (postgresql://…) rồi bấm Enter "
    "— ký tự không hiện ra khi dán, đó là bình thường.":
        "This machine is not connected to the shared database yet. Paste the database address your admin sent you "
        "(postgresql://…) and press Enter — the characters stay hidden while you paste, that is expected.",
    "Thao tác tự động đang bị tắt trên máy này (L2M_NO_AUTOMATION=1).": "Automation is disabled on this machine (L2M_NO_AUTOMATION=1).",
    "⚠ Tài khoản {user} đang có agent khác chạy trên máy {host}; lệnh sẽ chạy ở máy nào nhận trước.":
        "⚠ Account {user} already has another agent running on {host}; each job runs on whichever machine picks it up first.",
    "Đã tắt agent.": "Agent stopped.",
}
