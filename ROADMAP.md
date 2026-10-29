# Lộ trình nền tảng L2M Ops

Mục tiêu: app của mọi người trong team chạy chung trên một nền tảng — cùng đăng nhập, cùng dữ liệu, cùng menu — rồi
**liên kết thông tin** giữa các app để làm việc thuận tiện nhất.

Nguyên tắc xuyên suốt:
- Mỗi tính năng là một plugin.
- Plugin chỉ dùng nền tảng qua `core.sdk`.
- Plugin liên kết với nhau qua dữ liệu dùng chung, không gọi code của nhau.

Nhờ vậy, khi nền tảng dời sang server nội bộ hay thay đổi bên trong, plugin không phải sửa.

## Phase 1 — Đưa app của mọi người lên nền tảng *(đang làm)*

**Nền tảng đã có:**
- Khung plugin:
  - Menu tự dựng từ `plugins/<id>/plugin.toml`.
  - Plugin lỗi không làm hỏng phần còn lại.
- `core.sdk`:
  - Lưu dữ liệu vào CSDL chung, có lịch sử sửa / xoá.
  - Quyền, game đang chọn, file master, bảng Item ID, AI, secret.
- Quy định `PLUGIN_GUIDE.md` và hướng dẫn cho AI `AGENTS.md` / `CLAUDE.md`.
- Trang **Plugin của team**:
  - Thông báo, danh sách plugin.
  - Tải bộ khởi đầu, tự kiểm tra, gửi plugin.
  - Quy định, lộ trình.
- Kiểm tra tự động `tools/check_plugins.py`; GitHub Actions chạy sau mỗi lần đẩy code.

**Việc của admin:**
1. Gửi thông báo cho team kèm đường dẫn trang **Plugin của team**.
2. Thêm người làm plugin vào kho GitHub. Ai chưa có GitHub thì gửi zip qua website.
3. Nhận plugin gửi lên (trang Lịch sử hoạt động, loại *Gửi plugin*) và đưa vào `plugins/<id>/`.
4. Thêm thư viện / secret mà plugin cần.
5. Ghi lại nhu cầu "Cần từ nền tảng" trong README của các plugin để làm ở phase 3.

**Việc của thành viên:**
1. Tải bộ khởi đầu; đưa AI đọc `AGENTS.md` + `PLUGIN_GUIDE.md`.
2. Chuyển app hiện có thành plugin.
   - Dữ liệu lưu qua sdk, dùng đúng **mã chung** (mục 5.2).
   - Có nút nhập dữ liệu từ app cũ.
3. Chạy thử bằng `run.bat`, tự kiểm tra, gửi.

**Xong khi:** mỗi app của team chạy được như một plugin trên website, với dữ liệu thật trong CSDL chung.

## Phase 2 — Liên kết thông tin

Làm khi đã có dữ liệu thật của các plugin.

1. Rà dữ liệu mọi plugin đang lưu (trang Plugin của team có số bản ghi theo plugin), cùng thống nhất mã chung còn thiếu.
2. **Danh mục chung** do nền tảng giữ: gói (Product Key), item (Item ID), bản update (vùng + phiên bản + ngày), thuật ngữ dịch, thị trường.
3. **Bảng liên kết** "A → quan hệ → B" mà plugin nào cũng ghi được (vd update KR → giới thiệu → item 812; gói → chứa → item;
   thuật ngữ → là tên dịch của → item), cùng hàm sdk để ghi / đọc liên kết.
4. **Trang chi tiết** cho gói / item / bản update: mỗi plugin góp một khung thông tin (nội dung master, lịch sử setup,
   performance, bản dịch, update nước ngoài liên quan…).
5. **Tìm kiếm chung** trên dữ liệu của mọi plugin.

**Xong khi:** mở một gói hoặc một item là thấy thông tin của mọi plugin liên quan trên cùng một trang.

## Phase 3 — Việc chạy nền

1. **Chạy định kỳ** (vd thu thập update mỗi sáng): plugin khai báo lịch trong plugin.toml.
   - Trước mắt chạy bằng GitHub Actions.
   - Khi có server nội bộ thì chạy trên server.
2. **Lệnh agent cho plugin:** việc cần VPN / trình duyệt (NC tool, MyTool) chạy qua agent trên máy từng người, như các tính năng hiện có.
   - Admin duyệt từng lệnh, vì code này chạy trên máy cả team.
3. **Lưu file** lớn ngoài CSDL (kho file), để CSDL không đầy.

## Phase 4 — Dời sang server nội bộ

Làm khi có quyền tạo project.

1. Dựng CSDL Postgres và website trên server, chuyển dữ liệu từ CSDL hiện tại sang.
2. Chạy định kỳ trên server, bỏ GitHub Actions.
3. Đổi địa chỉ cho agent, website và người dùng.

Plugin không phải sửa gì, vì chỉ dùng `core.sdk`.

## Phase 5 — Trợ lý AI xuyên plugin

Hỏi đáp trên dữ liệu đã liên kết của mọi plugin. Ví dụ: "bản update TW tuần sau có item nào chưa dịch, gói nào tương tự
đã bán ở SEA và bán thế nào?"
