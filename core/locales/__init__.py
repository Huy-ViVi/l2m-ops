"""Bản dịch giao diện. Mỗi file <mã ngôn ngữ>_<khu vực>.py có một dict tên <MÃ> (vd EN): chuỗi gốc tiếng Việt -> bản dịch.

Chia theo khu vực để dễ tìm: en_common (khung app, đăng nhập, lịch sử, dữ liệu chung, cài đặt, thông báo hệ thống),
en_nc (tạo gói NC tool), en_payment (case nạp lỗi), en_webshop (kiểm tra webshop, master).
Giữ nguyên các chỗ {tên} trong bản dịch. Kiểm tra thiếu/thừa: python tests/test_i18n.py --missing
"""
