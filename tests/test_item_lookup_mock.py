"""Test Tra Item lookup trên trang GIẢ LẬP giống trang thật (ảnh chụp 27/10/2026):
ô app group mặc định là game khác (NCV-Journey Of Monarch), bảng form tìm kiếm nằm trên bảng kết quả,
kết quả rỗng hiện 'There are no item details.'. Chạy Edge headless + web server cục bộ.

    python tests/test_item_lookup_mock.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("L2M_DATA_DIR", tempfile.mkdtemp(prefix="l2m-test-"))  # không đụng data/ thật hay CSDL chung

from playwright.sync_api import sync_playwright  # noqa: E402

from automation import nc_billing as nb  # noqa: E402
from core import nc_setup  # noqa: E402

PAGE = """<!doctype html><html><body>
<form id="f">
<table class="search">
  <tr><th>Item number</th><td><input name="itemNo"></td><th></th><td></td></tr>
  <tr><th>Item name (administrator)</th><td><input name="itemName"></td>
      <th>Item app group code</th><td>
        <!-- giống trang thật: <select> gốc bị ẩn, dropdown tuỳ biến (select2) vẽ ô giả bên trên -->
        <select name="appGroupCode" style="display:none">
          <option value="jomsa" selected>NCV-Journey Of Monarch</option>
          <option value="l2msa">NCV-Lineage2M</option>
          <option value="l2mkr">Lineage2M KR</option></select>
        <span class="select2-selection" id="agDisplay">NCV-Journey Of Monarch</span></td></tr>
  <tr><th>Game item key</th><td><input name="gameItemKey"> *If you enter a game item key, other conditions will not apply.</td></tr>
</table>
<button type="submit">Search</button>
</form>
<table id="result"><thead><tr><th>Item number</th><th>Item name(administrator)</th><th>Item name(customer)</th><th>App group</th></tr></thead>
<tbody><tr><td colspan="4">There are no item details.</td></tr></tbody></table>
<div id="pager"></div>
<script>
const DATA = [
  {no: 195, name: "Pa'agrio's Seal Chest (Bound)", grp: "l2msa"},
  {no: 9195, name: "Pa'agrio's Seal Chest (Bound)", grp: "jomsa"},
  {no: 42, name: "Ink of Mana (Unique)(Bound)", grp: "l2msa"},
  {no: 139, name: "Fancy Soul Crystal Stone (11 Times) (Bound)", grp: "l2msa"},
  {no: 138, name: "Eva's Seal Chest (Bound)", grp: "l2msa"},
  {no: 301, name: "Parchment of Mana (Bound)", grp: "l2msa"},
];
const PAGE_SIZE = 2;
let results = [], pageNo = 1;
const ag = document.querySelector('[name=appGroupCode]');
ag.addEventListener('change', () => { document.getElementById('agDisplay').textContent = ag.options[ag.selectedIndex].text; });
function render() {
  const g = ag.value, rows = results.slice((pageNo - 1) * PAGE_SIZE, pageNo * PAGE_SIZE);
  document.querySelector('#result tbody').innerHTML = rows.length
    ? rows.map(d => `<tr><td>${d.no}</td><td>${d.name}</td><td>${d.name}</td><td>${g}</td></tr>`).join('')
    : '<tr><td colspan="4">There are no item details.</td></tr>';
  const pages = Math.ceil(results.length / PAGE_SIZE);
  let html = '';
  for (let p = 1; p <= pages; p++) html += `<a href="#" data-p="${p}">${p}</a> `;
  if (pageNo < pages) html += `<a href="#" data-p="${pageNo + 1}">Next</a>`;
  document.getElementById('pager').innerHTML = html;
}
document.getElementById('pager').addEventListener('click', e => {
  if (e.target.dataset.p) { e.preventDefault(); pageNo = +e.target.dataset.p; render(); }
});
document.getElementById('f').addEventListener('submit', e => {
  e.preventDefault();
  const q = document.querySelector('[name=itemName]').value.toLowerCase();
  results = DATA.filter(d => d.grp === ag.value && d.name.toLowerCase().includes(q));
  pageNo = 1;
  render();
});
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        body = PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    auto = {"nc_base_url": f"http://127.0.0.1:{srv.server_address[1]}"}
    names = ["Pa'agrio's Seal Chest (Bound)", "Ink of Mana (Unique) (Bound)", "Không có item này"]
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        ctx = browser.new_context()
        res = nb.item_lookup(ctx, auto, names, "l2msa", "NCV-Lineage2M")
        shown = ctx.pages[-1].locator("#agDisplay").inner_text()  # ô giả đã cập nhật theo lựa chọn
        groups = nb.list_app_groups(ctx, auto)
        dump = nb.dump_items(ctx, auto, "l2msa", "NCV-Lineage2M")
        browser.close()
    srv.shutdown()
    c0 = nc_setup.lookup_candidates(res[names[0]]["rows"])
    c1 = nc_setup.lookup_candidates(res[names[1]]["rows"])
    checks = {
        "không lỗi": "_error" not in res,
        "chọn được <select> bị ẩn, ô hiển thị đổi sang NCV-Lineage2M": shown == "NCV-Lineage2M",
        "chọn đúng app group L2M (không lấy 9195 của JoM)": c0 == [{"item_id": 195, "name": "Pa'agrio's Seal Chest (Bound)"}],
        "bỏ qua bảng form tìm kiếm": all("Item app group code" not in " ".join(r.values()) for r in res[names[0]]["rows"]),
        "tên lệch dấu cách -> tìm lại bỏ (Bound) và ra ID 42": c1 and c1[0]["item_id"] == 42 and res[names[1]]["query"] == "Ink of Mana (Unique)",
        "không có kết quả -> rỗng, không lấy dòng 'no item details'": res[names[2]]["rows"] == [],
        "đọc được danh sách app group": ["l2msa", "NCV-Lineage2M"] in groups and ["jomsa", "NCV-Journey Of Monarch"] in groups,
        "tải hết danh sách item qua 3 trang, không lẫn item JoM": sorted(
            c["item_id"] for c in nc_setup.lookup_candidates(dump.get("rows", []))) == [42, 138, 139, 195, 301],
    }
    for k, ok in checks.items():
        print(("PASS " if ok else "FAIL ") + k)
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
