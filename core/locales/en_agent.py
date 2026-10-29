"""Bản dịch tiếng Anh — chạy thao tác tự động từ website qua agent (ui/common.py, ui/auth.py, automation/agent.py)."""

EN = {
    # ---- ui/common.py, ui/auth.py (website gửi lệnh) -------------------------------------
    "Chưa thấy agent trên máy bạn. Thao tác NC tool / MyTool cần VPN công ty và phiên SSO của chính bạn, nên website "
    "gửi lệnh về máy bạn chạy. Lần đầu: bấm **⬇ Tải agent cho máy này**, giải nén, nháy đúp **agent.bat** (tự cài "
    "mọi thứ, có sẵn tài khoản của bạn) và bật VPN. Agent chạy ngầm (chấm tròn ở khay hệ thống) và tự bật cùng "
    "Windows. Tải lại trang này sau vài giây.":
        "No agent found on your machine. NC tool / MyTool actions need the company VPN and your own SSO sign-in, so the website "
        "sends them to your machine. First time: click **⬇ Download agent for this machine**, unzip it, double-click **agent.bat** "
        "(it installs everything and already has your account) and turn on the VPN. The agent runs in the background (a dot in "
        "the system tray) and starts with Windows. Reload this page after a few seconds.",
    "🟠 Agent đang chạy bản code khác website. Agent cài từ ngày 29/10/2026 trở đi tự cập nhật trong "
    "vài phút; bản cài trước đó: tải agent bản mới, giải nén đè lên thư mục agent cũ rồi mở lại "
    "agent.bat (một lần, từ đó tự cập nhật).":
        "🟠 The agent runs a different code version than the website. Agents installed from 29/10/2026 on update themselves "
        "within a few minutes; older installs: download the new agent, unzip it over the old agent folder and reopen agent.bat "
        "(once — after that it updates itself).",
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
    "Nút NC tool / MyTool trên website chạy trên máy đang chạy agent của tài khoản này. "
    "Mỗi người dùng tài khoản riêng, nếu không lệnh sẽ chạy trên máy người khác.":
        "NC tool / MyTool buttons on the website run on the machine where this account's agent is running. "
        "Everyone should use their own account, otherwise actions run on someone else's machine.",
    "Hiện cửa sổ agent": "Show agent window",
    "Agent chạy ngầm trên máy {host}. Bấm để mở cửa sổ log của nó trên máy đó "
    "(đóng cửa sổ log không tắt agent).":
        "The agent runs in the background on {host}. Click to open its log window on that machine "
        "(closing the log window does not stop the agent).",
    "Đã gửi — cửa sổ agent sẽ hiện trên máy {host} sau vài giây.": "Sent — the agent window will appear on {host} in a few seconds.",
    "Trình duyệt đã bị đóng trước khi thao tác xong. Chạy lại và giữ cửa sổ trình duyệt mở tới khi log báo "
    "xong (nếu cửa sổ bật lên trên máy người khác: bạn đang dùng tài khoản của họ).":
        "The browser was closed before the action finished. Run it again and keep the browser window open until the log says "
        "done (if the window popped up on someone else's machine, you are using their account).",
    "Chưa thấy agent trên máy bạn.": "No agent found on your machine.",
    "Chạy trên máy **{host}** (agent của {user}) — giữ trang này mở tới khi xong.":
        "Running on **{host}** ({user}'s agent) — keep this page open until it finishes.",
    "Đang chờ agent nhận lệnh…": "Waiting for the agent to pick up the job…",
    "Lệnh đã bị huỷ hoặc hết hạn trước khi agent chạy.": "The job was cancelled or expired before the agent ran it.",
    "Agent trên máy {host} không nhận lệnh. Kiểm tra agent còn chạy (chấm tròn ở khay hệ "
    "thống) và máy còn mạng, rồi bấm lại.":
        "The agent on {host} did not pick up the job. Check that the agent is still running (the dot in the system tray) "
        "and the machine is online, then try again.",
    "Mất liên lạc với agent trên máy {host} (agent bị tắt hoặc máy mất mạng).":
        "Lost contact with the agent on {host} (the agent was stopped or the machine went offline).",
    "Quá thời gian chờ agent.": "Timed out waiting for the agent.",
    # ---- automation/agent.py: đăng nhập, nhận lệnh -------------------------------------------
    "Đăng nhập một lần bằng tài khoản L2M Ops của bạn — lệnh bạn bấm trên website sẽ chạy trên máy này.":
        "Sign in once with your L2M Ops account — actions you click on the website will run on this machine.",
    "Mật khẩu: ": "Password: ",
    "Sai username hoặc mật khẩu.": "Wrong username or password.",
    "✓ Đã kết nối lại CSDL chung.": "✓ Reconnected to the shared database.",
    "⚠ Mất kết nối CSDL chung: {error} — đang thử lại…": "⚠ Lost connection to the shared database: {error} — retrying…",
    "Website yêu cầu hiện cửa sổ agent.": "The website asked to show the agent window.",
    "Website yêu cầu hiện cửa sổ agent — cửa sổ này đang mở.": "The website asked to show the agent window — this window is already open.",
    "Lệnh đã bị huỷ trên website.": "The job was cancelled on the website.",
    "Agent bị tắt giữa chừng.": "The agent was stopped mid-job.",
    "✅ Agent đang chạy ngầm cho tài khoản {user} trên máy {host}.": "✅ Agent running in the background for account {user} on {host}.",
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
    "⚠ Trên máy này còn một agent khác đang chạy (cửa sổ agent.bat cũ?). Đóng cửa sổ đó để lệnh không chạy hai lần.":
        "⚠ Another agent is still running on this machine (an old agent.bat window?). Close it so jobs do not run twice.",
    "Đã tắt agent.": "Agent stopped.",
    "Đã huỷ.": "Cancelled.",
    # ---- automation/agent.py: biểu tượng khay ---------------------------------------------
    "Mất kết nối CSDL chung — đang thử lại": "Lost connection to the shared database — retrying",
    "Đang chạy lệnh {job}": "Running job {job}",
    "Có bản agent mới trên website": "A new agent version is on the website",
    "Đang chờ lệnh từ website": "Waiting for jobs from the website",
    "Website đã có bản code mới ({version}). Tải agent bản mới ở thanh bên trái website, giải nén đè lên thư mục "
    "này rồi mở lại agent.bat.":
        "The website has a new code version ({version}). Download the new agent from the website sidebar, unzip it over "
        "this folder and reopen agent.bat.",
    "Có bản agent mới": "New agent version",
    # ---- tự cập nhật (automation/agent.py, automation/updater.py) ------------------------------
    "Website đã có bản code mới ({version}) — agent sẽ tự cập nhật khi không chạy lệnh.":
        "The website has a new code version ({version}) — the agent will update itself when no job is running.",
    "Thư mục agent đã có bản code {version} — khởi động lại agent để dùng.":
        "The agent folder already has code version {version} — restarting the agent to use it.",
    "Đang tải bản code {version} từ GitHub để tự cập nhật…": "Downloading code version {version} from GitHub to update…",
    "Code trên GitHub chưa khớp bản website ({version}) — website có thể chưa cập nhật xong; thử lại sau ít phút.":
        "The code on GitHub does not match the website version ({version}) yet — the website may still be updating; "
        "retrying in a few minutes.",
    "chép code mới chưa trọn vẹn": "the new code was not copied completely",
    "⚠ Chưa tự cập nhật được: {error} — thử lại sau ít phút (hoặc tải agent bản mới trên website).":
        "⚠ Could not update automatically: {error} — retrying in a few minutes (or download the new agent from the website).",
    "✓ Đã chép bản code {version} — khởi động lại agent…": "✓ Copied code version {version} — restarting the agent…",
    "✓ Agent đã tự cập nhật lên bản {version}.": "✓ The agent updated itself to version {version}.",
    "Agent đã tự cập nhật lên bản mới của website ({version}).":
        "The agent updated itself to the website's new version ({version}).",
    "Mở website, bấm ⬇ Tải agent cho máy này ở thanh bên trái, giải nén đè lên "
    "thư mục agent rồi mở lại agent.bat.":
        "Open the website, click ⬇ Download agent for this machine in the sidebar, unzip it over "
        "the agent folder and reopen agent.bat.",
    "Tài khoản {user} · máy {host}": "Account {user} · {host}",
    "Mở website": "Open website",
    "Tự bật cùng Windows": "Start with Windows",
    "Tắt agent": "Stop agent",
    "Tự bật cùng Windows: bật.": "Start with Windows: on.",
    "Tự bật cùng Windows: tắt.": "Start with Windows: off.",
    "Agent đang chạy lệnh {job}. Tắt agent sẽ huỷ lệnh này. Vẫn tắt?":
        "The agent is running job {job}. Stopping the agent cancels this job. Stop anyway?",
    "Đang tắt agent…": "Stopping the agent…",
    # ---- automation/agent.py: chạy ngầm, cửa sổ log, agent.bat ---------------------------------
    "Agent chưa đăng nhập trên máy này — mở agent.bat để đăng nhập.": "The agent is not signed in on this machine — open agent.bat to sign in.",
    "⚠ Chưa kết nối được CSDL chung: {error} — đang thử lại…": "⚠ Cannot reach the shared database yet: {error} — retrying…",
    "Đang bật agent chạy ngầm (bản {version})…": "Starting the background agent (version {version})…",
    "⚠ Không hiện được biểu tượng ở khay hệ thống — agent vẫn chạy; mở agent.bat để xem log.":
        "⚠ Could not show the system tray icon — the agent keeps running; open agent.bat to see the log.",
    "Agent đang chạy ngầm. Bấm vào chấm tròn này để xem cửa sổ log; chuột phải để tắt.":
        "The agent is running in the background. Click this dot to see the log window; right-click to stop it.",
    "⚠ Agent dừng vì lỗi: {error}": "⚠ The agent stopped because of an error: {error}",
    "Đóng cửa sổ này chỉ ẩn log — agent vẫn chạy ngầm. Tắt agent: chuột phải chấm tròn ở khay hệ thống → Tắt agent.":
        "Closing this window only hides the log — the agent keeps running. To stop it: right-click the dot in the system tray → Stop agent.",
    "Agent đã tắt. Mở lại agent.bat để bật lại.": "The agent has stopped. Open agent.bat again to restart it.",
    "Nhấn Enter để đóng.": "Press Enter to close.",
    "Cửa sổ này tự đóng sau {n} giây — nhấn phím bất kỳ để tiếp tục xem log.":
        "This window closes in {n} seconds — press any key to keep watching the log.",
    "Agent đang chạy ngầm trên máy này. Đây là cửa sổ log của nó.": "The agent is running in the background on this machine. This is its log window.",
    "Đang tắt agent đang chạy để đổi tài khoản…": "Stopping the running agent to switch accounts…",
    "Có bản code mới — đang tắt agent cũ để cập nhật…": "New code found — stopping the old agent to update…",
    "⚠ Không tắt được agent đang chạy. Tắt nó ở biểu tượng khay hệ thống rồi mở lại agent.bat.":
        "⚠ Could not stop the running agent. Stop it from the system tray icon, then reopen agent.bat.",
    "⚠ Không bật được tự chạy cùng Windows: {error}": "⚠ Could not enable start with Windows: {error}",
    "Agent chạy ngầm chưa báo sẵn sàng — xem log ở data\\agent.log.":
        "The background agent did not report ready — see the log in data\\agent.log.",
    "✅ Agent đang chạy ngầm. Tìm chấm tròn màu xanh ở khay hệ thống (góc phải thanh tác vụ, có thể nằm trong nút ^): "
    "bấm vào để xem lại cửa sổ log, chuột phải để tắt agent. Trên website còn có nút Hiện cửa sổ agent.":
        "✅ The agent is running in the background. Look for the green dot in the system tray (right end of the taskbar, maybe "
        "behind the ^ button): click it to see the log window again, right-click to stop the agent. The website also has a "
        "Show agent window button.",
    "Tự bật cùng Windows: bật (tắt ở menu chuột phải của chấm tròn).": "Start with Windows: on (turn it off from the dot's right-click menu).",
    "Tự bật cùng Windows: tắt (bật ở menu chuột phải của chấm tròn).": "Start with Windows: off (turn it on from the dot's right-click menu).",
    "Agent đang chạy ngầm trên máy này — tắt nó trước (agent.bat --stop).":
        "The agent is already running in the background on this machine — stop it first (agent.bat --stop).",
    "Không có agent nào đang chạy ngầm.": "No background agent is running.",
}
