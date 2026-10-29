# Quy định làm plugin cho L2M Ops

> Dành cho thành viên team **và AI hỗ trợ họ** (Claude, ChatGPT, Cursor…).
> AI: đọc hết file này trước khi viết code, làm đúng từng mục, và chạy `tools/check_plugins.py` đến khi báo OK.
> Công cụ kiểm tra tự động (trên máy, trên website và trên GitHub) chặn các điều ở mục 12.

## 1. Plugin là gì

- Mỗi tính năng (app) của một thành viên là **một plugin**, nằm trong **một thư mục** `plugins/<id>/` của kho code nền tảng.
- Nền tảng lo phần chung: đăng nhập, phân quyền, chọn game, ngôn ngữ, menu, nơi lưu dữ liệu chung, lịch sử hoạt động, AI.
- Plugin chỉ lo nghiệp vụ của mình và dùng nền tảng qua **một cửa duy nhất**: `from core import sdk`.
- Plugin **không gọi code của plugin khác**. Các plugin liên kết với nhau qua **dữ liệu dùng chung** (mục 5). Đây là điều kiện để phase 2 nối được thông tin của mọi người.
- **Ai sửa được gì:**
  - Thành viên toàn quyền trong thư mục plugin của mình.
  - Phần lõi chỉ admin nền tảng sửa: `core/`, `ui/`, `views/`, `automation/`, `tools/`, `app.py`, `requirements.txt`.

## 2. Cấu trúc thư mục (bắt buộc)

```
plugins/<id>/
├── plugin.toml     khai báo (mục 3)
├── __init__.py     để trống
├── README.md       mô tả plugin theo mẫu (mục 9)
├── page.py         trang; nhiều trang thì nhiều file
├── locales.py      (không bắt buộc) bản tiếng Anh, mục 8
└── …               file code phụ, ảnh nhỏ
```

- `<id>`:
  - Chữ thường không dấu, số và `_`, dài 3–32 ký tự, bắt đầu bằng chữ. Ví dụ: `update_tracker`, `translation_hub`, `package_monitor`.
  - Đặt một lần, **không đổi**, vì dữ liệu đã lưu gắn với id.
- Dung lượng: cả thư mục tối đa 5 MB, mỗi file tối đa 2 MB. Dữ liệu lớn lưu bằng sdk (mục 5).
- Cách bắt đầu nhanh nhất: chép thư mục `plugins/_template` (plugin mẫu) thành `plugins/<id>`.

## 3. plugin.toml

```toml
id = "update_tracker"              # trùng tên thư mục
name = "Update nước ngoài"         # tên trên menu
description = "Thu thập và tóm tắt bản update KR/TW/JP."
version = "0.1.0"                  # tăng mỗi lần cập nhật
owners = ["myly"]                  # tài khoản website của người phụ trách (có thể nhiều người)
icon = ":material/public:"         # :material/<tên>: (fonts.google.com/icons) hoặc một emoji
section = "Thị trường"             # nhóm trên menu; bỏ trống = "Plugin"
access = "all"                     # all = mọi người đã đăng nhập; admin = chỉ admin
games = []                         # [] = mọi game; ["l2m"] = chỉ hiện khi chọn Lineage2M SEA

[[pages]]
file = "page.py"
title = "Update nước ngoài"
icon = ":material/public:"

[[pages]]                          # trang thứ hai (nếu có)
file = "report.py"
title = "Báo cáo update"
```

Không đặt `section` trùng nhóm của nền tảng ("Chức năng", "Team", "Hệ thống").

## 4. Viết trang

- Trang là file Python dùng **Streamlit**. File chạy lại từ trên xuống mỗi lần người dùng thao tác, như một app Streamlit thường.
- Dòng đầu tiên của trang: `sdk.header(sdk.t("Tiêu đề"))`.
- **Không** gọi `st.set_page_config`, `st.navigation`, `st.Page`: nền tảng đã lo.
- **Khoá widget và `st.session_state` phải có tiền tố `<id>_`**, vì mọi trang dùng chung một session. Cách đơn giản nhất là dùng `sdk.key("ten")`:
  ```python
  st.text_input("Từ khoá", key=sdk.key("q"))      # -> "update_tracker_q"
  st.session_state[sdk.key("picked")] = 5
  ```
- Import code phụ của chính mình: `from . import helpers` hoặc `from plugins.<id> import helpers`.
- Chỉ import `core.sdk` từ nền tảng. Không import `core.store`, `core.db`, `ui`, `views`, `automation` hay plugin khác.
- Người quyền **Chỉ xem**: kiểm tra `sdk.can_edit()` trước khi hiện nút lưu / sửa / xoá.
- Plugin bị lỗi lúc chạy thì nền tảng bắt lại và chỉ báo lỗi ở trang của plugin. Dù vậy, vẫn nên tự bắt lỗi nghiệp vụ (file sai mẫu, thiếu cột…) và báo dễ hiểu.
- Việc chậm: bọc bằng `st.spinner`. Dữ liệu đọc nhiều lần: dùng `st.cache_data` (nhớ đưa `sdk.game_id()` vào tham số).
- Giờ hiện tại: dùng `sdk.now()` (giờ Việt Nam), không dùng `datetime.now()`, vì máy chủ chạy giờ UTC.

## 5. Dữ liệu

### 5.1 Lưu và đọc

- Dữ liệu cần giữ lâu **chỉ lưu bằng sdk**, vào CSDL chung của team.
- Không ghi file ra ổ đĩa để giữ dữ liệu: ổ đĩa của website bị xoá mỗi lần khởi động lại.
- Không dùng CSDL riêng (sqlite, Postgres riêng) hay Google Sheet riêng làm nơi lưu chính.

| Hàm | Dùng để |
|---|---|
| `sdk.save("updates", records, key="id")` | Thêm hoặc ghi đè. Cùng khoá thì ghi đè, bản cũ được giữ trong lịch sử. Trả về số bản ghi thay đổi. |
| `sdk.load("updates", region="KR")` | Đọc mọi bản ghi, có thể lọc theo trường. Mỗi bản ghi có thêm `_key`, `_updated_by`, `_updated_at`. |
| `sdk.get("updates", "kr-2026-10-29")` | Đọc một bản ghi theo khoá. |
| `sdk.delete("updates", keys)` | Xoá; bản cũ được giữ trong lịch sử. |
| `sdk.history("updates", key)` | Các bản cũ. Khôi phục bằng `sdk.save("updates", ban_cu["data"])`. |
| `sdk.collections()` | Các bộ sưu tập của plugin và số bản ghi. |
| `sdk.record("Tiêu đề", summary, files)` | Ghi một bản vào trang Lịch sử hoạt động của team, kèm file kết quả (Excel, ảnh…). |

- **Bản ghi** là một dict, và mọi giá trị phải lưu được dạng JSON: chữ, số, True/False, None, list, dict. Ngày giờ thì sdk tự đổi sang chữ.
- **Khoá:**
  - Mỗi bản ghi có một khoá ổn định, mặc định là trường `id`.
  - Đặt khoá theo nội dung để chạy lại không sinh bản trùng. Ví dụ: `kr-2026-10-29`, `web.item195-TH-2026-10-28`.
- **Bộ sưu tập** (tên nhóm bản ghi): chữ thường không dấu, số, `_`. Ví dụ: `updates`, `terms`, `daily_sales`.
- **Game:**
  - Mặc định dữ liệu gắn với game đang chọn ở thanh bên.
  - Dữ liệu dùng cho mọi game: thêm `game=""` khi save / load.
- Mỗi bản ghi tối đa 200 KB. File lớn đính kèm qua `sdk.record(..., files={"ten.xlsx": bytes})`.

### 5.2 Mã chung — bắt buộc, để phase 2 liên kết được thông tin

Khi dữ liệu có thông tin dưới đây, **phải** dùng đúng tên trường và định dạng này:

| Trường | Ý nghĩa | Định dạng | Ví dụ |
|---|---|---|---|
| `product_key` | Product Key của gói | như master, bỏ `com.ncv.l2m.` (sdk tự chuẩn hoá trường này; tự ghép khoá thì dùng `sdk.product_key(...)`) | `web.item195` |
| `item_id` | Item ID trên NC tool | số nguyên | `79` |
| `item_name` | tên item như trên tool / master (tiếng Anh) | chữ | `Fancy Class Card (11 Times) (Bound)` |
| `market` | shop / thị trường bán | `SG` `ID` `PH` `MY` `TH` `VN` | `TH` |
| `region` | máy chủ / phiên bản nước ngoài | `KR` `TW` `JP` `NA` `EU` `SEA` … | `KR` |
| `version` | phiên bản / bản update | như nguồn ghi | `2026.10.29` |
| `date` | ngày | `YYYY-MM-DD` | `2026-10-29` |
| `datetime` | thời điểm, giờ Việt Nam | `YYYY-MM-DD HH:MM:SS` | `2026-10-29 09:30:00` |
| `currency` | tiền tệ | mã ISO | `THB` |
| `price` | giá | số | `19.99` |
| `lang` | ngôn ngữ của văn bản | `vi` `en` `th` `id` `ko` `ja` `zh-TW` … | `th` |
| `url` | đường dẫn nguồn | đầy đủ `https://…` | |

- Không lưu trường `game`: sdk tự gắn game.
- Các trường khác: tên tiếng Anh, `snake_case`, không dấu. Ví dụ: `title`, `summary`, `revenue_usd`.
- Đã dùng một tên trường thì không đổi tên hay đổi ý nghĩa nữa. Cần khác đi thì thêm trường mới.
- Liệt kê mọi bộ sưu tập và trường trong README.md của plugin (mục 9).

### 5.3 Dữ liệu dùng chung của nền tảng (chỉ đọc)

- `sdk.master()`: file master *All Product Information* hiện hành của game đang chọn.
  - `.packages`: gói theo Product Key, gồm tên, giá, limit, diamonds và danh sách item.
  - `.webshop`: giá theo thị trường.
  - `.display_name(product_key)`: tên hiển thị của gói.
  - `.timeline`: lịch bán.
- `sdk.items()`: bảng Item ID dùng chung của team.
- Dùng hai hàm này thay vì tự đọc file master hay tự giữ danh sách Item ID riêng.

## 6. Bí mật, AI, thư viện

- **Không** ghi API key, mật khẩu, token, địa chỉ CSDL vào code hay file trong plugin. Thay vào đó:
  - Trong code, đọc bằng `sdk.secret("TEN")`.
  - Gửi giá trị riêng cho admin. Admin cài vào secrets của website với tên `PLUGIN_<ID>_<TEN>`.
- AI: dùng `sdk.ai()`, theo cấu hình AI chung của team; có `.text(system, prompt)` và `.json(system, prompt, schema)`. Không tự gọi API AI bằng key riêng.
- Thư viện:
  - Chỉ dùng thư viện chuẩn của Python và thư viện có trong `requirements.txt` của nền tảng (streamlit, pandas, openpyxl, requests…).
  - Cần thêm thư viện: nhắn admin tên, phiên bản và lý do.
- Ngoài ra không dùng: `subprocess`, `os.system`, Playwright / Selenium, đọc biến môi trường trực tiếp.

## 7. Việc chạy nền, chạy định kỳ, cần VPN

Phase 1 **chưa** hỗ trợ trong plugin:
- việc chạy định kỳ (vd thu thập update mỗi sáng);
- việc cần VPN công ty hoặc điều khiển trình duyệt (NC tool, MyTool);
- việc nặng (trên khoảng 30 giây, hoặc file rất lớn).

Trong lúc chờ:
- Cho người dùng **bấm nút để chạy** (việc ngắn), hoặc **tải file lên** để plugin xử lý.
- Ghi rõ nhu cầu vào README mục "Cần từ nền tảng" để admin làm ở phase 3.

## 8. Ngôn ngữ

- Chữ hiển thị viết **tiếng Việt** và bọc bằng `sdk.t("…")`. Chỗ cần điền số dùng `sdk.t("Đã lưu {n} dòng", n=5)`, không dùng f-string bên trong `sdk.t`.
- Khuyến khích thêm `locales.py` để người chọn English thấy tiếng Anh:
  ```python
  EN = {"Đã lưu {n} dòng": "Saved {n} rows"}
  ```
  Dict phải viết thẳng: nền tảng đọc file này mà không chạy nó.

## 9. README.md của plugin (mẫu)

```markdown
# <Tên plugin>
Người phụ trách: <tài khoản>

## Làm gì
## Trang
## Dữ liệu lưu
| Bộ sưu tập | Khoá | Trường | Mã chung dùng |
|---|---|---|---|
## Dữ liệu dùng từ nền tảng / plugin khác
## Cần từ nền tảng
(chạy định kỳ? cần VPN? thư viện thêm? secret?)
## Thay đổi
- 0.1.0 (YYYY-MM-DD): bản đầu
```

## 10. Chạy thử, kiểm tra và đưa lên

1. **Chạy thử trên máy:**
   - Tải *Bộ khởi đầu* ở trang **Plugin của team** trên website và giải nén.
   - Chép `plugins/_template` thành `plugins/<id>`.
   - Nháy đúp `run.bat`. Plugin hiện ở menu bên trái; dữ liệu khi chạy thử chỉ lưu trên máy bạn.
2. **Tự kiểm tra:**
   - Chạy `.venv\Scripts\python.exe tools\check_plugins.py plugins\<id>` cho đến khi báo `OK`.
   - Hoặc nén thư mục plugin thành .zip rồi tải lên ô *Tự kiểm tra* trên trang **Plugin của team**.
3. **Đưa lên** — chọn một trong hai cách:
   - **GitHub** (khi admin đã thêm bạn vào kho):
     - Tải thư mục lên đúng chỗ `plugins/<id>/`, chỉ sửa trong thư mục của mình.
     - Khoảng 1–2 phút sau website tự cập nhật.
     - Kiểm tra tự động (tab Actions trên GitHub) chạy sau mỗi lần đẩy code. Báo đỏ thì sửa ngay.
   - **Gửi zip trên website:** trang **Plugin của team** → *Đưa plugin lên* → tải zip → *Gửi plugin cho admin*. Admin sẽ đưa lên.
4. **Mỗi lần cập nhật:**
   - Tăng `version` trong plugin.toml.
   - Thêm một dòng vào mục "Thay đổi" của README.
5. **Dữ liệu từ app cũ:** làm một nút "Nhập dữ liệu" trong plugin (tải file Excel / CSV xuất từ app cũ lên → `sdk.save`), để không mất dữ liệu đã có.

## 11. Checklist trước khi gửi

- [ ] `plugin.toml` đủ trường; `id` trùng tên thư mục; `owners` đúng tài khoản website.
- [ ] Chỉ import `core.sdk` từ nền tảng; không import plugin khác.
- [ ] Dữ liệu lưu bằng sdk. Mã chung đúng tên và định dạng (mục 5.2). Khoá bản ghi ổn định.
- [ ] Khoá widget / session_state có tiền tố `<id>_` (dùng `sdk.key`).
- [ ] Có kiểm tra `sdk.can_edit()` trước khi lưu, sửa, xoá.
- [ ] Không có key, mật khẩu, token, địa chỉ CSDL hay file dữ liệu lớn trong thư mục.
- [ ] Chữ hiển thị bọc `sdk.t`.
- [ ] README.md đủ mục; đã tăng `version`.
- [ ] `tools/check_plugins.py` báo OK; đã chạy thử bằng `run.bat`.

## 12. Bị chặn tự động

| Bị chặn | Thay bằng |
|---|---|
| Thiếu `plugin.toml` / `__init__.py` / `README.md`, khai báo sai | sửa theo mục 2–3 |
| Import `core.*` khác `core.sdk`, `ui`, `views`, `automation`, plugin khác | `from core import sdk`; liên kết qua dữ liệu |
| `sqlite3`, `psycopg`, `sqlalchemy` | `sdk.save` / `sdk.load` |
| `subprocess`, `os.system`, Playwright, Selenium | chờ phase 3 (agent); ghi nhu cầu vào README |
| `os.environ`, `os.getenv` | `sdk.secret` |
| `st.set_page_config`, `st.navigation` | bỏ — nền tảng đã lo |
| Khoá widget / session_state không có tiền tố `<id>_` | `sdk.key("…")` |
| Thư viện không có trong `requirements.txt` | nhắn admin thêm |
| Key / token / mật khẩu / địa chỉ CSDL trong file; file `.env`, `local.json`, `secrets.toml`, `.db` | `sdk.secret`; dữ liệu qua sdk |
| File > 2 MB, thư mục > 5 MB, lỗi cú pháp Python | tách dữ liệu ra CSDL; sửa lỗi |
