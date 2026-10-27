"""Bản dịch tiếng Anh — chạy thao tác tự động từ website qua agent (ui/common.py, automation/agent.py)."""

EN = {
    # ---- ui/common.py (website gửi lệnh) ---------------------------------------------
    "Chưa thấy agent trên máy bạn. Thao tác NC tool / MyTool cần VPN công ty và phiên SSO của chính bạn, nên website "
    "gửi lệnh về máy bạn chạy: mở **agent.bat** trong thư mục app trên máy bạn (máy có VPN, đã nối CSDL chung ở "
    "trang Cài đặt), đăng nhập một lần bằng tài khoản L2M Ops rồi giữ cửa sổ đó mở. Tải lại trang này sau vài giây.":
        "No agent found on your machine. NC tool / MyTool actions need the company VPN and your own SSO sign-in, so the website "
        "sends them to your machine: open **agent.bat** in the app folder on your machine (VPN on, connected to the shared "
        "database in Settings), sign in once with your L2M Ops account and keep that window open. Reload this page after a few seconds.",
    "🟢 Thao tác tự động chạy qua agent trên máy **{host}** của bạn.": "🟢 Automation runs through the agent on your machine **{host}**.",
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
    "Máy này chưa nối CSDL chung. Mở bản local (run.bat) → Cài đặt → Nối máy này vào CSDL chung, rồi chạy lại agent.bat.":
        "This machine is not connected to the shared database. Open the local app (run.bat) → Settings → Connect this machine "
        "to the team's shared database, then run agent.bat again.",
    "Thao tác tự động đang bị tắt trên máy này (L2M_NO_AUTOMATION=1).": "Automation is disabled on this machine (L2M_NO_AUTOMATION=1).",
    "⚠ Tài khoản {user} đang có agent khác chạy trên máy {host}; lệnh sẽ chạy ở máy nào nhận trước.":
        "⚠ Account {user} already has another agent running on {host}; each job runs on whichever machine picks it up first.",
    "Đã tắt agent.": "Agent stopped.",
}
