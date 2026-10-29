# Ghi chú gói nạp (plugin mẫu)

Người phụ trách: ten_tai_khoan

## Làm gì
Ghi chú theo gói nạp (Product Key); hiện kèm tên gói lấy từ file master của team. Đây là plugin mẫu, minh hoạ cách dùng `core.sdk`.

## Trang
- **Ghi chú gói nạp** (`page.py`): thêm, xem, xoá ghi chú; xem lịch sử sửa / xoá; ghi tổng hợp vào Lịch sử hoạt động.

## Dữ liệu lưu
| Bộ sưu tập | Khoá | Trường | Mã chung dùng |
|---|---|---|---|
| `notes` | `id` = `<product_key>-<YYYYMMDDHHMMSS>` | `product_key`, `note`, `date` | `product_key`, `date` |

Dữ liệu gắn với game đang chọn.

## Dữ liệu dùng từ nền tảng / plugin khác
- `sdk.master()`: tên gói theo Product Key.

## Cần từ nền tảng
Không có (không cần chạy định kỳ, VPN, thư viện thêm hay secret).

## Thay đổi
- 0.1.0 (2026-10-29): bản đầu.
