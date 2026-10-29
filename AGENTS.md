# Hướng dẫn cho AI làm việc trong kho code L2M Ops

Kho code này là **nền tảng L2M Ops**: website Streamlit cho team vận hành game, gồm các tính năng của nền tảng và
**plugin** của từng thành viên (`plugins/<id>/`). Người dùng có thể không phải lập trình viên — giải thích ngắn gọn, dễ hiểu.

## Khi giúp một thành viên làm hoặc sửa plugin

1. **Đọc `PLUGIN_GUIDE.md` trước khi viết code** và làm đúng từng mục. Đây là quy định chung của cả team.
2. **Chỉ tạo / sửa file trong `plugins/<id>/`** của plugin đó. Không sửa `core/`, `ui/`, `views/`, `automation/`,
   `tools/`, `app.py`, `requirements.txt` hay plugin của người khác — kể cả khi việc đó có vẻ tiện hơn.
3. Plugin mới: chép `plugins/_template` thành `plugins/<id>`, sửa `id` trong `plugin.toml` cho trùng tên thư mục.
4. Dùng nền tảng **chỉ qua** `from core import sdk` (xem docstring từng hàm trong `core/sdk.py`).
5. Dữ liệu lưu bằng `sdk.save` / `sdk.load`, dùng đúng **mã chung** (PLUGIN_GUIDE.md mục 5.2), khoá bản ghi ổn định.
6. Khoá widget / `st.session_state` dùng `sdk.key("…")`; chữ hiển thị bọc `sdk.t("…")`; kiểm tra `sdk.can_edit()` trước
   khi lưu / sửa / xoá; giờ hiện tại dùng `sdk.now()`.
7. Không ghi key / mật khẩu / token vào file — dùng `sdk.secret("TEN")` và nhắc người dùng gửi giá trị cho admin.
8. Sau mỗi lần sửa:
   - chạy `.venv\Scripts\python.exe tools\check_plugins.py plugins\<id>` (máy khác Windows: `python tools/check_plugins.py plugins/<id>`)
     và sửa đến khi báo `OK`;
   - nhắc người dùng chạy thử bằng `run.bat`;
   - cập nhật `README.md` của plugin (dữ liệu lưu, thay đổi) và tăng `version` trong `plugin.toml`.
9. Cần thứ nền tảng chưa có (thư viện mới, secret, chạy định kỳ, VPN / trình duyệt, việc nặng): **không tự sửa phần lõi**.
   Ghi vào README mục "Cần từ nền tảng" và nói người dùng nhắn admin.
10. Chuyển một app có sẵn thành plugin: giữ nghiệp vụ, thay phần lưu trữ bằng sdk, thêm nút nhập dữ liệu từ app cũ.

## Khi người dùng là admin nền tảng và yêu cầu sửa phần lõi

Sửa theo yêu cầu. Giữ tương thích ngược cho `core/sdk.py` (plugin đang dùng): được thêm hàm, không đổi tên / bỏ hàm hay
đổi ý nghĩa tham số. Đổi quy định thì cập nhật `PLUGIN_GUIDE.md`, `core/plugins.py` (phần kiểm tra) và `ROADMAP.md` cùng lúc.
