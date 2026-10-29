# L2M Ops Toolkit

App gom các workflow vận hành Lineage2M SEA trước đây làm qua Claude Chat (skill `lineage2m-ops`) thành một app chạy độc lập.

| Function | Workflow gốc | App làm gì |
|---|---|---|
| **Tạo gói nạp NC** | Task 9 | Đọc Item Mapping → plan Goods Admin + Limit Admin theo convention → map Item ID → điền form trên NC tool (bạn duyệt, bấm Register) → audit lại từng trường |
| **Case nạp lỗi** | Task 10 | Sheet CS → MyTool Search Order (Export Excel) → lọc `DELIVERY_SERVER_ERROR` → Diamonds từ master → `Payment Error Case <MMDD>.xlsx` + CSV từng user |
| **Kiểm tra webshop VNG** | Task 4 | So gói trên MyTool Sold Package (6 shop) với master: giá, thời gian bán, tên, trạng thái → báo cáo ✅/❌ |

## Chạy app

1. Đặt thư mục app ở **đường dẫn ngắn**, ví dụ `C:\L2M-Ops` hoặc `Documents\L2M-Ops`. Windows giới hạn đường dẫn 260 ký tự, để quá sâu sẽ lỗi khi nạp thư viện.
2. Nháy đúp **`run.bat`**. Lần đầu app tự tạo môi trường Python và cài thư viện (mất vài phút), sau đó mở `http://localhost:8501`.

Yêu cầu: Windows 10/11, Microsoft Edge (có sẵn), mạng Internet ở lần chạy đầu. **Không cần cài Python trước**: `run.bat` / `agent.bat` gọi `tools\setup.ps1`, máy chưa có Python 3.10+ (64-bit) thì tự tải Python 3.13 bản portable chính thức (gói `python` trên NuGet của Microsoft, kiểm tra mã SHA256) vào thư mục `.python` của app — không cần quyền admin, không cài vào hệ thống, không đổi PATH. Các lần sau chỉ kiểm tra nhanh (dưới 1 giây); `requirements.txt` đổi thì tự cài thêm thư viện.

## Thiết lập lần đầu (trang Cài đặt)

1. **AI**: chọn provider (Claude / OpenAI / Gemini / Gateway nội bộ), nhập API key, bấm *Test kết nối AI*.
2. **Đăng nhập SSO**: bấm *Mở trình duyệt để đăng nhập SSO*, đăng nhập NC tool + MyTool rồi đóng cửa sổ. Phiên đăng nhập được giữ trong `data/browser-profile`, app không bao giờ nhập mật khẩu.
3. **URL Sold Package**: mở từng shop LIVE trên MyTool (SG/ID/PH/MY/TH/VN) rồi dán URL trang Sold Package vào.
4. **Calibrate form NC** (trang Tạo gói NC → Nâng cao): app đọc form thật và map đúng từng ô theo `name`/`id`, lưu vào `data/nc_fields.json`. Nên chạy 1 lần trước lần tạo gói đầu tiên.

## Nguyên tắc an toàn

- Mọi thao tác tạo trên tool đều phải qua bước duyệt plan và tick xác nhận. Mặc định app **chỉ điền form**, bạn tự bấm Register.
- App không tự sửa gì trên MyTool. Trang kiểm tra webshop chỉ báo cáo.
- Case nạp lỗi bám theo danh sách CS: order lỗi dư trên MyTool chỉ được liệt kê, không tự thêm.
- AI chỉ làm phần cần hiểu ngữ cảnh (map tên item, đọc Timeline Selling, viết tóm tắt). Kết quả AI luôn hiển thị để duyệt. Account Number và Game Account ID không được gửi lên AI.

## Chế độ team (cả team dùng chung qua mạng LAN)

Máy của bạn làm server tạm: nháy đúp **`run-team.bat`** và giữ cửa sổ đó mở trong lúc team dùng.

1. **Trên chính máy server**, mở `http://localhost:8501` rồi tạo tài khoản **admin đầu tiên**. Vì lý do an toàn, chỉ người ngồi tại máy server mới tạo được tài khoản này.
2. Vào **Thành viên** để cấp tài khoản cho từng người, với vai trò Admin / Thành viên / Chỉ xem.
3. Gửi cho thành viên địa chỉ **`http://<IP máy server>:8501`**. Địa chỉ IP có ghi ở trang Cài đặt → Server team.
4. Lần đầu chạy, Windows có thể hỏi có cho Python qua tường lửa không. Chọn **Allow** cho mạng Private/Domain. Nếu không có quyền, nhờ IT mở 2 cổng 8501 (web) và 8502 (API đồng bộ).

> ⚠️ **Đừng gửi IP VPN.** Khi GlobalProtect đang bật, máy có thêm một IP VPN (card "PANGP Virtual Ethernet Adapter"). Máy khác thường không vào được qua IP này. Trang Cài đặt → Server team liệt kê mọi IP của máy và đánh dấu sẵn IP nào là VPN; hãy gửi IP của card **Ethernet** (LAN công ty). Thành viên làm từ xa qua VPN thường không vào được máy của nhau, khi đó cần một server riêng do IT cấp.
> Cửa sổ `run-team.bat` phải luôn mở. Tắt cửa sổ đó là server dừng.

| Quyền | Được làm |
|---|---|
| Admin | Toàn quyền: quản lý thành viên, cài đặt (AI key, URL tool), sửa/xoá mọi bản ghi, khôi phục bản đã xoá |
| Thành viên | Chạy function, tải master, lưu lịch sử, sửa bảng Item ID, sửa/xoá bản ghi của chính mình |
| Chỉ xem | Xem kết quả, lịch sử, tải file |

- **Lịch sử hoạt động:** mỗi đợt case nạp lỗi, plan/setup gói NC, báo cáo kiểm tra webshop, lần cập nhật master đều được lưu kèm file kết quả. Mọi người xem lại, thêm ghi chú, đổi trạng thái được. Tab *Nhật ký thay đổi* ghi lại ai đã sửa gì, lúc nào, kể cả đăng nhập.
- **Dữ liệu dùng chung:** bảng Item ID (một người thêm thì cả team dùng được) và các phiên bản master đã tải lên (có thể tải lại, hoặc chọn dùng lại bản cũ).
- **Đăng nhập** được ghi nhớ 14 ngày nên tải lại trang không bị đăng xuất. Đổi mật khẩu hoặc khoá tài khoản sẽ đăng xuất người đó trên mọi thiết bị.

**Thao tác tự động (tra MyTool, tạo gói NC) chạy ở máy từng người**, vì nó dùng phiên đăng nhập SSO của chính người đó:
- Người ngồi tại máy server (mở bằng `localhost`) dùng được trực tiếp. Người truy cập qua IP thì thấy nút tự động bị tắt.
- Thành viên cần tự động thì cài bản local trên máy mình (copy thư mục app, chạy `run.bat`). Sau đó vào Cài đặt → Server team, điền `http://<IP máy server>:8502` và token do admin cấp ở trang Thành viên. Từ đó mỗi lần bấm "Lưu vào lịch sử" ở bản local, kết quả tự đẩy lên server team.

Lưu ý:
- Máy server tắt hoặc ngủ thì team không vào được. Toàn bộ dữ liệu nằm ở `data/app.db` trên máy server, nên sao lưu file này định kỳ.
- Kết nối trong LAN là HTTP thường (không mã hoá). Chỉ dùng trong mạng nội bộ công ty, không mở ra Internet.
- Khi muốn chuyển lên server riêng (VM nội bộ do IT cấp): chép nguyên thư mục app kèm `data/`, chạy `run-team.bat` trên máy đó, không phải sửa code. Trên server Linux không có trình duyệt, đặt `L2M_NO_AUTOMATION=1`.

## Website ngoài + CSDL chung (Streamlit Community Cloud + Supabase)

Thay cho việc lấy một máy làm server: website chạy trên **Streamlit Community Cloud** (miễn phí, app đặt ở Mỹ), dữ liệu nằm trong **Postgres của Supabase** (miễn phí). Bản local của từng người (run.bat) nối vào cùng CSDL đó, nên ai sửa gì cả team thấy ngay.

| Nơi chạy | Làm được | Ghi chú |
|---|---|---|
| Website (Streamlit Cloud) | Mọi thứ. Nút NC tool / MyTool chạy qua **agent** trên máy người bấm (mục dưới) | Máy chủ website không vào được NC tool / MyTool (`L2M_NO_AUTOMATION=1`) |
| Bản local (run.bat) nối CSDL chung | Mọi thứ, kể cả thao tác tự động NC tool / MyTool (cần VPN + SSO trên máy đó) | Đăng nhập bằng tài khoản trên website; kết quả ghi thẳng vào CSDL chung |
| Agent (agent.bat) | Chạy các nút NC tool / MyTool bạn bấm trên website, ngay trên máy bạn | Cần VPN, Edge hoặc Chrome (tự chọn), phiên SSO của bạn; chạy ngầm, tự bật cùng Windows |

**Agent: bấm trên website, chạy trên máy bạn.** NC tool / MyTool chỉ vào được từ mạng công ty bằng SSO của từng người, nên website gửi lệnh vào CSDL chung (bảng `jobs`), agent trên máy *của chính người bấm* nhận lệnh, chạy `automation.runner` y như bản local (mở Edge trên màn hình người đó, vẫn tự bấm Register), đẩy log lên website mỗi giây và trả kết quả (file MyTool nằm ở bảng `job_files`).
1. Admin tạo tài khoản riêng cho từng người (Quản lý thành viên). Lệnh đi theo tài khoản: dùng chung tài khoản thì lệnh chạy trên máy người khác.
2. Người đó đăng nhập website, bấm **⬇ Tải agent cho máy này** (thanh bên trái — chỉ hiện khi chưa có agent hoặc agent chạy bản cũ). Zip do website tạo từ chính code của nó (`core/bundle.py`), kèm `data/local.json` đã điền địa chỉ CSDL chung và tài khoản người tải. Giải nén, nháy đúp **`agent.bat`**: tự cài Python + thư viện, không hỏi gì thêm, bật agent chạy ngầm rồi tự đóng cửa sổ sau 10 giây. Bật VPN.
   - Không tải từ website thì giải nén code app bất kỳ rồi mở `agent.bat`: agent hỏi địa chỉ CSDL (dán vào, ký tự không hiện) và tài khoản **một lần** (`agent.bat --logout` để đổi tài khoản).
   - Agent báo bản code của nó (`bundle.code_version()`); khác bản của website thì thanh bên báo 🟠 và hiện lại nút tải để giải nén đè. Agent chạy ngầm cũng tự thấy website có bản mới (website ghi bản của nó vào bảng `agents`, dòng `~website`).
   - **Tự cập nhật** (`automation/updater.py`): agent cài từ zip của website (`data/local.json` có `"auto_update": true`) thấy website lên bản mới — lúc vừa bật, hoặc lúc rảnh (không chạy lệnh) — thì tải code từ kho GitHub `huy-vivi/l2m-ops` (`archive/HEAD.zip`), **chỉ dùng khi code tải về đúng là bản website đang chạy** (tính lại `bundle.version_of`; ai sửa được CSDL cũng không bắt agent chạy code lạ được), chép đè file code (không đụng `data/`, `.venv`), rồi một tiến trình PowerShell ẩn chờ agent cũ thoát, cài thêm thư viện nếu `requirements.txt` đổi, bật lại agent bằng code mới và hiện thông báo "Agent đã tự cập nhật". Không tải được / GitHub chưa khớp bản website thì chạy tiếp bản cũ, 5 phút sau thử lại. Thư mục code đang phát triển (không có `auto_update`) không bị chép đè; nhưng code trên đĩa đã đúng bản website thì agent cũng tự khởi động lại. Agent cài trước khi có tính năng này cần tải zip mới **một lần**.
   - Zip chứa mật khẩu CSDL: chỉ tài khoản Thành viên/Admin đã đăng nhập mới tải được; không gửi zip cho người khác.
3. Trên website, các nút NC tool / MyTool bấm được khi agent đang chạy (trang hiện "🟢 … agent trên máy …"). Lệnh chỉ chạy trên agent của đúng người bấm; lệnh chờ quá 2 phút bị bỏ (không mở NC tool bất ngờ); tắt agent giữa chừng thì website báo mất liên lạc.

**Kiểm tra máy sau khi đăng nhập website** (`ui/agent_setup.py`; nút **Kiểm tra máy** ở thanh bên chạy lại bất cứ lúc nào). Website ở Mỹ không đọc được máy người dùng, nên agent tự kiểm tra máy mỗi phút — mỗi 10 giây khi chưa vào được NC tool — (có trình duyệt đã chọn, vào được NC tool / MyTool — tức VPN đang bật, đã bật tự chạy cùng Windows, đã đăng ký link) rồi ghi vào CSDL (bảng `agents`, cột `checks`):
- Agent đang chạy và máy ổn → báo "Máy … đã đủ điều kiện".
- Agent chạy nhưng còn thiếu (VPN tắt, agent bản cũ, thiếu trình duyệt) → hộp hướng dẫn sửa từng mục. Trong hộp có một fragment chạy ngầm 2 giây/lần: máy đổi trạng thái (vd vừa bật VPN) thì hộp tự chuyển sang "đã đủ điều kiện", cả tiêu đề, không cần bấm. **Kiểm tra lại**: dòng "đã gửi yêu cầu… đang chờ agent trả lời" hiện ngay (lúc bấm không gọi CSDL, lệnh gửi ngay sau đó), rồi hộp ghi rõ agent đã kiểm tra lúc nào (hoặc agent không trả lời sau 20 giây). Dòng chờ / kết quả nằm ở một chỗ cố định đầu hộp để các phần bên dưới không xê dịch.
- Tài khoản đã cài agent (bản có link) nhưng agent đang tắt → website tự mở link **`l2mops-agent://start`** (agent.bat đăng ký link này trong `HKCU\Software\Classes`, không cần admin). Trình duyệt hỏi *"This site is trying to open L2M Ops Agent"* → tick **Always allow** → **Open**; agent bật lên và báo về. Trình duyệt không hỏi (có trình duyệt chặn tự mở khi chưa bấm gì) → bấm nút **▶ Bật agent** hiện ở thanh bên. Quá 25 giây không thấy → hộp hướng dẫn cài đặt.
- Agent bản cũ (trước khi có link, website biết qua cột `checks` không có `protocol`) đang tắt → mở ngay hộp hướng dẫn tải bản mới, không thử bật.
- Hộp thoại đang mở được vẽ lại ở mọi lượt chạy của trang (vd bật VPN làm mất kết nối rồi nối lại) cho tới khi người dùng bấm Đóng / Để sau / dấu X. Agent ghi vào log khi NC tool đổi trạng thái (vào được / chưa vào được) và khi website yêu cầu kiểm tra lại.
- Chưa có agent → hộp **hướng dẫn cài đặt bằng hình** (7 bước, vẽ bằng SVG trong `ui/guide_art.py`, có tên tài khoản và địa chỉ website của người xem) + nút tải agent + nút **▶ Bật agent**.
- Mở website trên máy không phải Windows → chỉ báo một dòng (xem/sửa dữ liệu bình thường).

**Trình duyệt của từng người.** Ô **Trình duyệt** ở thanh bên (dưới Kiểm tra máy): mỗi người chọn Microsoft Edge / Google Chrome / Chromium cho riêng mình (lưu ở bảng `users`, cột `browser`). Người chưa chọn lần nào: lần đầu vào website, app lấy luôn trình duyệt đang mở website làm lựa chọn (Edge / Chrome trên Windows, đọc từ User-Agent; Cốc Cốc, Opera, Firefox, máy Mac… thì không tự chọn). Chọn **Theo team** (lưu là `team`) thì dùng **Trình duyệt mặc định** admin đặt ở trang Cài đặt và không tự đổi nữa. Lệnh gửi agent mang theo lựa chọn này (`_browser` trong payload, `automation/runner.py` dùng nó). Đổi trình duyệt → agent kiểm tra lại máy với trình duyệt mới; máy chưa có thì hộp hướng dẫn chỉ đúng trình duyệt đó + link tải. Chromium của Playwright không cài sẵn cùng agent (máy chưa tải thì kiểm tra máy báo thiếu). Đổi trình duyệt thì đăng nhập SSO lại một lần trong trình duyệt mới (cùng thư mục `data/browser-profile`).

**Agent chạy ngầm** (`automation/agent.py --background`, phần Windows ở `automation/desktop.py`, chỉ dùng thư viện có sẵn):
- Tiến trình `pythonw` không có cửa sổ; log ghi vào `data\agent.log`, trạng thái ở `data\agent.json`. Mỗi thư mục agent chỉ chạy một bản (mutex có tên).
- Một **chấm tròn ở khay hệ thống** (góc phải thanh tác vụ, Windows 11 có thể giấu trong nút ^): xanh lá = đang chờ lệnh, xanh dương = đang chạy lệnh, cam = mất kết nối CSDL / có bản mới. Bấm vào: mở **cửa sổ log**. Chuột phải: Hiện cửa sổ agent · Mở website · Tự bật cùng Windows · Tắt agent (đang chạy lệnh thì hỏi lại).
- **Hiện lại cửa sổ khi cần**, cách nào cũng được: bấm chấm tròn; bấm **Hiện cửa sổ agent** ở thanh bên website (cửa sổ hiện trên máy agent sau vài giây); hoặc mở lại `agent.bat` (cửa sổ đó thành cửa sổ log). Đóng cửa sổ log **không** tắt agent.
- **Tự bật cùng Windows**: `agent.bat` ghi khoá `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` của người dùng (không cần admin; thấy trong Task Manager → Startup apps). Tắt/bật ở menu chuột phải; lựa chọn được nhớ trong `data\local.json`.
- `agent.bat --stop` tắt agent; `agent.bat --foreground` chạy trong cửa sổ như bản cũ (đóng cửa sổ là tắt). Giải nén code mới đè lên rồi mở `agent.bat`: agent cũ tự tắt trước khi cài thư viện, bản mới bật lại.
- Không chạy cùng lúc thao tác tự động ở bản local và ở agent trên cùng một máy (dùng chung hồ sơ trình duyệt).
- Ai có địa chỉ CSDL chung là có toàn quyền trên CSDL đó: chỉ đưa cho người trong team.

Khi có `DATABASE_URL` (website: Secrets; bản local: trang Cài đặt → *Nối máy này vào CSDL chung*, lưu ở `data/local.json`):
- App luôn chạy chế độ team (đăng nhập) để mỗi thao tác ghi đúng tên người làm.
- Cài đặt chung (game, AI, NC tool, ngôn ngữ mặc định) và mọi phiên bản master lưu trong CSDL. Thư mục lưu kết quả vẫn là của từng máy.
- Đọc dữ liệu được cache 15 giây trong mỗi tiến trình: thay đổi từ máy khác hiện ra sau tối đa 15 giây, thay đổi của chính mình hiện ngay.

**Chuyển dữ liệu cũ lên CSDL chung** (một lần, từ máy đang có dữ liệu):

```bash
.venv\Scripts\python.exe tools\migrate_to_shared_db.py
```

Script chép tài khoản (giữ nguyên mật khẩu), lịch sử + file, Item ID, danh sách item NC tool, nhật ký, mọi phiên bản master và cài đặt chung. CSDL đích đã có dữ liệu thì dừng lại để tránh nhân đôi.

**Secrets của website** (Streamlit Cloud → App settings → Secrets), xem mẫu `.streamlit/secrets.toml.example`: `DATABASE_URL`, `L2M_APP_MODE = "team"`, `L2M_NO_AUTOMATION = "1"`, `L2M_PUBLIC = "1"`. `L2M_PUBLIC` tắt mọi quyền "máy chủ" trên website (tạo admin đầu tiên, đọc thư mục trên máy, automation).

**Số kết nối CSDL:** địa chỉ lưu ở secrets / `data/local.json` / zip agent là cổng 5432 của pooler (chế độ session), nhưng `core/db.py` (`pooled_url`) tự nối qua cổng **6543** (chế độ transaction). Chế độ session giữ một kết nối máy chủ cho mỗi kết nối của app và cả team chỉ được 15 (website + agent của từng người + tiến trình chạy lệnh của agent) — hết chỗ thì lệnh báo `EMAXCONNSESSION max clients reached` / `PoolTimeout`. Chế độ transaction chỉ mượn kết nối trong lúc chạy một giao dịch, nhận tới ~200. Vì kết nối máy chủ dùng chung, schema test đặt bằng `SET LOCAL search_path` theo từng giao dịch (không dùng `SET` cả phiên).

**Lưu ý gói miễn phí:** website ngủ khi lâu không ai vào (người vào đầu chờ khoảng 1 phút); Supabase tạm dừng project nếu 7 ngày không dùng (vào trang quản lý bấm Restore). Máy thành viên đã có `.venv` từ trước cần cài thêm thư viện: `.venv\Scripts\python.exe -m pip install -r requirements.txt`.

Test chế độ CSDL chung trên một schema tạm (tự xoá khi xong): đặt `L2M_TEST_DATABASE_URL` rồi chạy `tests\test_shared_db.py`, `tests\test_jobs.py` (thêm `L2M_TEST_BROWSER=1` để chạy một lượt thật website → agent → Edge ẩn trên trang NC tool giả lập) và `tests\test_agent_background.py` (bật agent chạy ngầm thật: thấy chấm tròn ở khay, một thông báo và cửa sổ log hiện lên rồi tự đóng; khoá Run dùng khoá registry tạm, không đụng khoá thật).

Mọi mốc thời gian ghi vào CSDL / hiển thị theo giờ Việt Nam (UTC+7, `config.now()`), vì máy chủ website chạy giờ UTC.

## Tìm Item ID khi tên trong Excel khác tên trên tool

Ở trang Tạo gói NC, phần **Tìm Item ID cho các item chưa xác nhận**:
1. **📥 Tải danh sách item từ NC tool**: tìm với tên trống rồi lật hết các trang kết quả, lưu toàn bộ item của app group vào CSDL. Chỉ cần chạy lại khi tool có item mới. Item nào trong Excel trùng tên hoàn toàn (bỏ qua hoa thường, dấu, `(Khóa)`/`(Bound)`) thì được nhận luôn.
2. Item còn lại hiện danh sách ứng viên gần giống nhất (có % độ giống). Số lần trong ngoặc (`1 Time` / `11 Times`) phải khớp, và khác Bound thì bị trừ điểm.
   Cạnh mỗi ứng viên là **số gói trong master đã dùng nó và gói gần nhất**. Gói "gần đây" là 30 gói cuối sheet Item Mapping, vì gói mới được thêm ở cuối sheet; các gói đang setup không được tính.
   **⭐ Nên dùng**: app chỉ so các item cùng tên, tức chỉ khác chữ thêm ở cuối như `Old`, `Nw`, và phải cùng số lần, cùng Bound. Item có trong nhiều gói gần đây hơn được ⭐; hoà thì xét tổng số gói. Item khác tên thì không bao giờ được ⭐ dù hay dùng (vd `Greater Class Skin Card` khi cần `Greater Class Card`).
   - Không có item trùng tên hoàn toàn và AI chưa chọn: ô chọn sẵn item ⭐.
   - Có item trùng tên mà ⭐ rơi vào item khác: app nhắc kiểm tra lại.
   - Chỉ đếm được dòng item app đã biết Item ID; tỉ lệ này ghi ngay dưới tiêu đề. Bấm 📥 tải danh sách item để đếm đủ hơn.
3. **🤖 AI chọn giúp**: AI chỉ được chọn trong các ứng viên là item thật trên tool, nên không thể bịa ID. Bạn duyệt rồi bấm **Áp dụng**.
4. **💾 Lưu vào bảng dùng chung**: lần sau cả team tự nhận các item này.

## Nền tảng plugin (tính năng của thành viên)

Mỗi tính năng của thành viên là một **plugin**: thư mục `plugins/<id>/` có `plugin.toml`. Website tự đưa plugin vào menu.
- **Quy định chung:** `PLUGIN_GUIDE.md`.
- **Hướng dẫn cho AI của mọi người:** `AGENTS.md`, `CLAUDE.md`.
- **Các bước tiếp theo:** `ROADMAP.md`.

Trang **Team → Plugin của team** có:
- thông báo cho team;
- danh sách plugin: phiên bản, người phụ trách, số bản ghi, lỗi cần sửa;
- bộ khởi đầu tải về (code chạy trên máy + plugin mẫu `plugins/_template` + quy định, không có địa chỉ CSDL);
- ô tự kiểm tra zip (chỉ đọc code, không chạy) và nút gửi plugin cho admin. Bản gửi nằm ở Lịch sử hoạt động, loại *Gửi plugin*.

Cách nền tảng chạy plugin:
- **Một cửa:** plugin chỉ dùng nền tảng qua `core/sdk.py` (người dùng, quyền, game, lưu dữ liệu, lịch sử, master, Item ID, AI, secret). Các hàm ở đây giữ tương thích ngược để khi dời sang server nội bộ, plugin không phải sửa.
- **Dữ liệu:** lưu dạng JSON trong bảng `plugin_records` của CSDL chung, theo (plugin, bộ sưu tập, game, khoá). Mỗi lần sửa / xoá, bản cũ được giữ trong `plugin_record_history`.
- **Mã chung:** `product_key`, `item_id`, `market`, `region`, `date`… (PLUGIN_GUIDE.md mục 5.2). Đây là cơ sở để phase 2 liên kết thông tin giữa các plugin.
- **Kiểm tra:** `core/plugins.py` đọc code mà không chạy, chặn các vi phạm quy định. Plugin vi phạm không lên menu.
  - Chạy tay: `tools/check_plugins.py`.
  - Tự động: GitHub Actions (`.github/workflows/check.yml`) chạy sau mỗi lần đẩy code.
- **Cô lập lỗi:** plugin lỗi khi chạy chỉ báo lỗi ở trang của nó (`ui/plugin_host.py`), phần còn lại vẫn chạy.
- **Agent:** `plugins/` không nằm trong bản code của agent, nên cập nhật plugin không làm agent phải tự cập nhật.

Secret của plugin: cài vào secrets của website với tên `PLUGIN_<ID>_<TÊN>`; plugin đọc bằng `sdk.secret("TÊN")`.

## Nhiều game

Chọn game ở **🎮 Game** trên thanh bên trái (app nhớ lựa chọn này cho lần sau). Mọi thông số phía sau đi theo game đang chọn:

| Theo game | Ghi chú |
|---|---|
| App group trên NC tool | App tự chọn đúng app group trước khi tìm item, tạo gói hay tạo limit (tool hay để mặc định game khác) |
| Tiền tố Store Product Key | Lineage2M: `com.ncv.l2m.` |
| Bảng Item ID | Mỗi game một bộ riêng, không lẫn nhau |
| File master | `data/master/<game>/`, có lịch sử phiên bản riêng |
| URL MyTool | Search Order (SEA/VN) và Sold Package (6 shop) |
| Lịch sử | Mặc định chỉ hiện game đang chọn; bật "Mọi game" để xem tất cả |
| Thư mục kết quả case nạp lỗi | Lineage2M giữ `Payment-Error-Cases\<ngày>\`; game khác ở `Payment-Error-Cases\<game>\<ngày>\` |

**Thêm game** (admin): vào Cài đặt → 🎮 Game → *Sửa thông số của game* → chọn **➕ Thêm game mới** và đặt tên. Sau đó:
1. Bấm **📋 Lấy danh sách app group từ NC tool** (cần VPN), chọn đúng app group của game rồi bấm *Dùng app group này*.
2. Điền **tiền tố Store Product Key** và các **URL MyTool** của game đó.
3. Bấm **💾 Lưu cài đặt**.

Dữ liệu từ bản trước (chỉ có Lineage2M) tự chuyển sang game Lineage2M khi khởi động: lịch sử, bảng Item ID, master và cài đặt.

## Ngôn ngữ giao diện (Tiếng Việt / English)

Chọn ở ô **🌐 Language** trên cùng thanh bên trái, kể cả ở trang đăng nhập. Mỗi trình duyệt nhớ lựa chọn riêng (cookie), nên trong chế độ team mỗi người dùng một ngôn ngữ khác nhau cùng lúc được. Trình duyệt chưa chọn thì dùng **Ngôn ngữ mặc định** do admin đặt ở trang Cài đặt.

- Theo ngôn ngữ đang chọn: toàn bộ chữ trên màn hình, thông báo lỗi, log automation, báo cáo webshop, phần giải thích/tóm tắt do AI viết.
- **Không đổi theo ngôn ngữ**: file `Payment Error Case <MMDD>.xlsx` + CSV từng user (định dạng cố định gửi CS/NC), tên trường/giá trị trên NC tool, tên item.
- Bản ghi lịch sử lưu nhãn gốc tiếng Việt và được dịch khi hiển thị. Tiêu đề và ghi chú do người dùng gõ giữ nguyên như lúc nhập.
- Bản dịch nằm trong `core/locales/en_*.py` (chuỗi gốc tiếng Việt → tiếng Anh). Thiếu bản dịch thì hiện tiếng Việt, không lỗi. Sửa chữ trong code thì chạy `tests\test_i18n.py --missing` để xem chuỗi nào cần dịch.

## AI

Đang dùng **gateway LiteLLM nội bộ** (provider "Gateway nội bộ", model `anthropic/claude-sonnet-5`). Key nằm trong `data/settings.json` trên máy chạy app, không nằm trong code. Admin đổi model ở trang Cài đặt → bấm *Lấy danh sách model* để chọn trong các model mà key được cấp. Cũng có thể đặt qua biến môi trường `GATEWAY_API_KEY`, `GATEWAY_BASE_URL`.

## Trạng thái kiểm chứng

- `tests/test_core.py`: logic đọc master, đối chiếu case nạp lỗi, xuất Excel/CSV theo template, plan NC, gợi ý item theo lịch sử gói (cả trang Tạo gói NC), audit webshop. Chạy trên file mẫu giả lập trong `tests/samples`.
- `tests/test_automation_mock.py`: điền form trên **form giả lập** mô phỏng NC tool (Edge headless).
- `tests/test_team.py`: tài khoản, mật khẩu, phiên đăng nhập, lịch sử, bảng Item ID dùng chung, API đồng bộ (HTTP thật: token sai → 401, Chỉ xem → 403), tách dữ liệu theo game, nâng cấp CSDL/cài đặt/master từ bản cũ.
- `tests/test_item_lookup_mock.py`: Tra Item lookup trên trang giả lập giống trang thật (app group mặc định là game khác, bảng form nằm trên bảng kết quả).
- `tests/test_nc_tool_mock.py`: tra Item ID bằng POST (cắt tên 40 ký tự, loại item 83/“Wrong”), tải toàn bộ danh sách item, tạo product + limit trên trang giả lập NC tool.
- `tests/test_i18n.py`: mọi chữ hiển thị đều có bản dịch tiếng Anh, chỗ `{}` khớp nhau, không dịch trùng lệch.
- `tests/test_plugins.py`: nền tảng plugin.
  - Plugin mẫu đạt quy định.
  - Bắt đủ các vi phạm: khai báo sai, import phần lõi / plugin khác, sqlite, thư viện lạ, `st.set_page_config`, khoá thiếu tiền tố, biến môi trường, bí mật, file lớn, lỗi cú pháp.
  - Kiểm tra zip, kể cả zip có đường dẫn lạ.
  - sdk: lưu / đọc / lọc / chuẩn hoá mã chung, lịch sử và khôi phục, tách dữ liệu theo plugin và theo game, bản dịch của plugin.
  - Trang plugin lỗi không làm hỏng trang; relative import; form của plugin mẫu lưu được.
  - Menu và trang Plugin của team; bộ khởi đầu không có `data/`.
  - `test_shared_db.py` chạy thêm phần dữ liệu plugin trên Postgres (ghi 1.200 bản ghi theo lô).
- `tests/test_jobs.py`: hàng đợi website → agent (chỉ chạy lệnh của đúng người, một máy nhận, hết hạn, huỷ giữa chừng, chuyển file kết quả, lệnh "hiện cửa sổ"); với CSDL chung: website chờ agent và hiện log, nút Hiện cửa sổ agent, và một lượt thật qua Edge ẩn.
- `tests/test_agent_update.py`: tự cập nhật — chỉ nhận code đúng bản website, chép đè đúng file code (không đụng `data/`, `.venv`, xoá file đã bỏ), từ chối zip có đường dẫn lạ, lệnh bật lại đọc đúng đường dẫn có dấu cách / ngoặc / nháy; với CSDL chung: một lượt thật (agent chạy ngầm từ bản sao app trong thư mục tạm tự tải từ máy chủ HTTP tạm thay GitHub, chép đè, tự bật lại, báo website bản mới).
- `tests/test_agent_background.py` (CSDL chung, Windows): agent chạy ngầm thật — sẵn sàng, chỉ một bản, chạy lệnh, mở cửa sổ log từ website và từ khay, bật/tắt tự chạy cùng Windows, báo bản mới, `--stop`; luồng `agent.bat` (lần đầu, mở lại khi đang chạy, tự tắt bản cũ khi có code mới); link `…://start` / `…://show` bật agent và hiện cửa sổ (dùng một tên link thử, xoá khi xong).
- `tests/test_jobs.py` phần kiểm tra máy sau đăng nhập: máy đủ điều kiện, thiếu VPN (hộp không mất khi trang chạy lại; Kiểm tra lại hiện dòng chờ ngay, gửi lệnh, hiện giờ kiểm tra, quá giờ chờ thì báo; agent tự thấy NC tool thì hộp tự chuyển sang đủ điều kiện cả tiêu đề; Đóng thì không mở lại), agent bản cũ đang tắt (hướng dẫn tải bản mới), người mới (hộp 7 hình + nút tải; cài xong Kiểm tra lại thấy agent), agent đã cài nhưng tắt (website bấm link rồi chờ), trình duyệt riêng (chọn Chrome → lưu theo tài khoản, agent kiểm tra lại, máy thiếu Chrome thì hướng dẫn + link tải, cài xong hộp tự chuyển; chưa chọn thì lấy trình duyệt đang mở website, nhận Edge / Chrome từ User-Agent, bỏ qua Cốc Cốc / Opera / Firefox / Mac).
- Chế độ team đã chạy thử trên trình duyệt ở `localhost`. **Chưa thử truy cập từ máy khác trong LAN** (cần máy thứ hai và tường lửa cho phép).
- **Chưa chạy trên tool thật** (NC Billing Admin, MyTool). Cần đăng nhập rồi Calibrate. Lần đầu nên chạy chế độ "tôi tự bấm Register" và đối chiếu kỹ.
- Định dạng ngày trên MyTool đang giả định `DD/MM/YYYY`. Nếu MyTool hiển thị `MM/DD`, cần chỉnh lại `core/webshop_audit.py`.

## Cấu trúc

```
app.py                 # điểm vào Streamlit: đăng nhập, menu theo quyền, khởi động API (chế độ team)
run.bat / run-team.bat # chạy cá nhân / chạy làm server cho team
agent.bat              # agent: chạy trên máy bạn các nút NC tool / MyTool bấm trên website
views/                 # 3 function + Lịch sử, Dữ liệu dùng chung, Thành viên, Cài đặt
ui/                    # thành phần UI dùng chung, đăng nhập & phân quyền (auth.py)
  agent_setup.py       # sau đăng nhập website: kiểm tra máy, tự bật agent, hộp hướng dẫn cài đặt / sửa
  guide_art.py         # hình hướng dẫn cài agent (SVG vẽ bằng code, dịch được)
core/                  # logic thuần (không phụ thuộc UI)
  master.py            # đọc master All Product Information (dò cột theo tên header)
  payment_errors.py    # Task 10
  nc_setup.py          # Task 9 (plan, Item ID, audit)
  webshop_audit.py     # Task 4
  ai.py                # Claude / OpenAI / Gemini / Gateway
  store.py             # CSDL SQLite: thành viên, phiên, lịch sử + file, Item ID, nhật ký
  api_server.py, sync.py  # API nhận kết quả từ bản local / phía gửi
  i18n.py, locales/    # đa ngôn ngữ: t("chuỗi tiếng Việt") + bản dịch en_*.py
  cowork_import.py     # nhập lịch sử setup từ Claude Cowork (skill package-creation)
  jobs.py              # hàng đợi lệnh website -> agent (CSDL chung)
  bundle.py            # zip agent tải từ website + mã phiên bản code + bộ khởi đầu làm plugin
  plugins.py           # tìm plugin, đọc plugin.toml, kiểm tra theo PLUGIN_GUIDE.md (không chạy code)
  sdk.py               # cửa duy nhất plugin dùng nền tảng (giữ tương thích ngược)
plugins/               # plugin của thành viên: plugins/<id>/; _template = plugin mẫu
ui/plugin_host.py      # đưa plugin vào menu, chạy trang plugin trong khung cô lập lỗi
views/plugins.py       # trang Plugin của team
tools/check_plugins.py # kiểm tra plugin (máy, GitHub Actions)
PLUGIN_GUIDE.md, ROADMAP.md, AGENTS.md, CLAUDE.md  # quy định, lộ trình, hướng dẫn cho AI
automation/            # Playwright: NC tool + MyTool (chạy tiến trình riêng); agent.py nhận lệnh từ website
  desktop.py           # Windows cho agent chạy ngầm: biểu tượng khay, chạy một bản, tự bật cùng Windows, cửa sổ log
resources/item_ids.json  # Item ID nạp sẵn lần đầu (l2msa)
data/                  # cài đặt, app.db, master + các phiên bản, phiên trình duyệt (không commit)
```

Chạy test:

```bash
.venv\Scripts\python.exe tests\test_core.py
```

```bash
.venv\Scripts\python.exe tests\test_team.py
```
