"""Test luồng NC tool trên một server GIẢ LẬP mô phỏng đúng các tên/id ô đã ghi trong skill package-creation:
- Item lookup bằng POST /MobileGoodsAdmin/items (itemAppGroupCode tường minh, pageSize=100, tên lưu tối đa 40 ký tự)
- Register product: goodsName/goodsDisplayName, '+ Add' giá (dòng template ẩn), dialog PG #selectMobilePgCode...,
  radio _isDeliveryConfirmation, $.fn.addGoodsItem, nút #submit-form
- Register limit: limitName, limitUserType=3, limitDurationUnitType, limitBaseDayOfWeek=2, $.fn.addGoods
- Header app group mặc định jmsa (tool reset sau login)

    python tests/test_nc_tool_mock.py
"""
from __future__ import annotations

import html
import os
import sys
import tempfile
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("L2M_DATA_DIR", tempfile.mkdtemp(prefix="l2m-test-"))  # không đụng data/ thật hay CSDL chung

from playwright.sync_api import sync_playwright  # noqa: E402

from automation import nc_billing as nb  # noqa: E402
from core import nc_setup  # noqa: E402

ITEMS = [(2, "Diamonds", "l2msa"), (195, "Pa'agrio's Seal Chest (Bound)", "l2msa"),
         (217, "Einhasad's Tshirt Selection Chest (Bound)", "l2msa"), (2, "Royal Coin", "jmsa"),
         (83, "Fancy Class Card (11 Time) (Bound) Wrong", "l2msa"), (79, "Fancy Class Card (11 Times) (Bound) Old", "l2msa")]
ITEMS += [(1000 + i, f"Filler Item {i:03d}", "l2msa") for i in range(150)]  # để có nhiều trang
STATE = {"products": [], "limits": []}

HEADER = """<select id="headerAppGroup" name="headerAppGroup" onchange="this.form && 0">
  <option value="jmsa" selected>NCV-Journey Of Monarch</option><option value="l2msa">NCV-Lineage2M</option></select>"""

GOODS_NEW = """<!doctype html><html><body>""" + HEADER + """
<form method="post" action="/MobileGoodsAdmin/goods/new" id="f">
<table>
<tr><th>Item app group code</th><td><select name="goodsAppGroupCode" style="display:none">
  <option value="jmsa" selected>NCV-Journey Of Monarch</option><option value="l2msa">NCV-Lineage2M</option></select><span>NCV-Journey Of Monarch</span></td></tr>
<tr><th>Product name (administrator)</th><td><input name="goodsName" maxlength="40"></td></tr>
<tr><th>Product name (customer)</th><td><input name="goodsDisplayName" maxlength="40"></td></tr>
<tr><th>Product description</th><td><textarea name="goodsDisplayDescription"></textarea></td></tr>
<tr><th>Product base price</th><td><div id="bp"><div class="row" style="display:none">
  <select name="goodsBasicPricePolicyList[0].currencyGroupId"><option value="">-</option><option value="1">Cash</option></select>
  <input name="goodsBasicPricePolicyList[0].goodsBasicPrice"></div></div><button type="button" onclick="addRow('bp')">+ Add</button></td></tr>
<tr><th>Or a monetary base price</th><td><div id="mp"><div class="row" style="display:none">
  <select name="goodsBasicCurrencyPricePolicyList[0].currencyCode"><option value="">-</option><option value="USD">USD</option></select>
  <select name="goodsBasicCurrencyPricePolicyList[0].goodsBasicCurrencyPrice"><option value=""></option></select>
  <input type="text" name="goodsBasicCurrencyPricePolicyList[0].goodsBasicCurrencyPrice"></div></div><button type="button" onclick="addRow('mp')">+ Add</button></td></tr>
<tr><th>Store Product Key</th><td><table id="pglist"><tr><th>PG</th></tr></table><button type="button" onclick="document.getElementById('dlg').style.display='block'">Modify</button></td></tr>
<tr><th>Need to delivery confirm</th><td>
  <input type="radio" name="_isDeliveryConfirmation" value="true" id="dc1"><label for="dc1">Required</label>
  <input type="radio" name="_isDeliveryConfirmation" value="false" id="dc0" checked><label for="dc0">Not Required</label>
  <input type="hidden" name="isDeliveryConfirmation" value="false"></td></tr>
<tr><th>Product item composition</th><td><div id="items"><div class="row" style="display:none">
  <input name="itemList[0].itemId"><input name="itemList[0].itemQuantity"></div></div></td></tr>
</table>
<input type="button" id="submit-form" value="Register" onclick="document.getElementById('f').submit()">
</form>
<div id="dlg" style="display:none"><select id="selectMobilePgCode"><option value="1">Google(NCV)</option><option value="25">VNG Store</option></select>
  <input id="pgGoodsKey"><input id="paymentReputationScore"><button type="button" id="btnAddPg">Add</button>
  <button type="button" id="btnEditPgListOkay">OK</button><input type="button" value="Register"></div>
<script>
let n = {bp: 0, mp: 0, items: 0}, pg = 0;
function addRow(id) {
  const box = document.getElementById(id), tpl = box.querySelector('.row'), row = tpl.cloneNode(true);
  n[id] += 1; row.style.display = '';
  row.querySelectorAll('[name]').forEach(e => e.name = e.name.replace('[0]', '[' + n[id] + ']'));
  box.appendChild(row); return row;
}
document.querySelectorAll('[name=_isDeliveryConfirmation]').forEach(r => r.addEventListener('click',
  () => document.querySelector('[name=isDeliveryConfirmation]').value = r.value));
document.getElementById('btnAddPg').onclick = () => {
  const f = document.getElementById('f');
  for (const [k, id] of [['pgId', 'selectMobilePgCode'], ['pgGoodsKey', 'pgGoodsKey'], ['paymentReputationScore', 'paymentReputationScore']]) {
    const h = document.createElement('input'); h.type = 'hidden'; h.name = `goodsPgList[${pg}].${k}`; h.value = document.getElementById(id).value; f.appendChild(h);
  }
  pg += 1; document.getElementById('pglist').insertAdjacentHTML('beforeend', '<tr><td>added</td></tr>');
};
document.getElementById('btnEditPgListOkay').onclick = () => document.getElementById('dlg').style.display = 'none';
window.$ = function () {}; window.$.fn = {addGoodsItem: function (id, grp, name, type) {
  const row = addRow('items'); row.querySelector('[name$=".itemId"]').value = id;
  row.insertAdjacentText('afterbegin', name);
}};
document.getElementById('headerAppGroup').addEventListener('change', e => { document.cookie = 'grp=' + e.target.value; });
</script></body></html>"""

LIMIT_NEW = """<!doctype html><html><body>""" + HEADER + """
<form method="post" action="/MobileLimitAdmin/purchase/goodsgroup/new" id="f"><table>
<tr><th>Limit name</th><td><input name="limitName"></td></tr>
<tr><th>Limit description</th><td><input name="limitDescription"></td></tr>
<tr><th>Limit subject type</th><td><input type="radio" name="limitTargetType" value="1">Server <input type="radio" name="limitTargetType" value="2" checked>Product</td></tr>
<tr><th>Limit type</th><td><select name="limitType"><option value="1">Amount</option><option value="2">Purchase Limit</option></select></td></tr>
<tr><th>Application Standard</th><td><select name="limitUserType"><option value="1">Character</option><option value="3">Account</option></select></td></tr>
<tr><th>Renewal</th><td><input type="hidden" name="limitDurationType" value="0"><input name="limitDuration">
  <select name="limitDurationUnitType"><option value="3">Time</option><option value="5">Week</option><option value="6">Month</option><option value="9">Permanent</option></select></td></tr>
<tr><th>Limit amount</th><td><input name="limitQuantity"></td></tr>
<tr><th>Amount limit</th><td><input name="limitScore"></td></tr>
<tr><th>Base Time Standard</th><td><input type="hidden" name="limitBaseTimeType" value="0">
  <select name="limitBaseDayOfWeek"><option value="1">Sunday</option><option value="2">Monday</option></select></td></tr>
<tr><th>Limited product</th><td><div id="goods"></div></td></tr>
</table><input type="button" id="submit-form" value="Register" onclick="document.getElementById('f').submit()"></form>
<script>
let g = 0;
window.$ = function () {}; window.$.fn = {addGoods: function (id, grp, a, b, cur) {
  document.getElementById('goods').insertAdjacentHTML('beforeend',
    `<div>#${id} <input type="hidden" name="goodsList[${g}].goodsId" value="${id}"><input name="goodsList[${g}].quantityWeight"></div>`); g += 1;
}};
</script></body></html>"""

LOOKUP = """<!doctype html><html><body>""" + HEADER + """<form method="post"><input name="limitName"><input type="hidden" name="pageIndex" value="1"></form></body></html>"""


def rows_html(rows):
    return "<table>" + "".join("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in r) + "</tr>" for r in rows) + "</table>"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, body: str, code: int = 200, location: str | None = None):
        data = body.encode("utf-8")
        self.send_response(code)
        if location:
            self.send_header("Location", location)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/MobileGoodsAdmin/goods/new":
            return self._send(GOODS_NEW)
        if path == "/MobileLimitAdmin/purchase/goodsgroup/new":
            return self._send(LIMIT_NEW)
        if path == "/MobileLimitAdmin/purchase/goodsgroup":
            return self._send(LOOKUP)
        return self._send("<!doctype html><html><body>" + HEADER + "<form></form><table><tr><td>-</td></tr></table></body></html>")

    def do_POST(self):
        path = urlparse(self.path).path
        form = {k: v[-1] for k, v in parse_qs(self.rfile.read(int(self.headers["Content-Length"] or 0)).decode()).items()}
        if path == "/MobileGoodsAdmin/items":
            grp, q = form.get("itemAppGroupCode", ""), form.get("itemName", "").lower()
            size, idx = int(form.get("pageSize", 10)), int(form.get("pageIndex", 1))
            found = [(i, nm[:40], g) for i, nm, g in ITEMS if g == grp and q in nm[:40].lower()]
            page_rows = found[(idx - 1) * size: idx * size]
            rows = [["☐", i, g, nm, "Gameplay item"] for i, nm, g in page_rows] or [["There are no item details.", "", "", "", ""]]
            return self._send(rows_html(rows))
        if path == "/MobileGoodsAdmin/goods/new":
            number = 900 + len(STATE["products"]) + 1
            STATE["products"].append({"number": number, **form})
            return self._send("", 303, "/MobileGoodsAdmin/goods")
        if path == "/MobileGoodsAdmin/goods":
            rows = [["☐", p["number"], p.get("goodsAppGroupCode"), p.get("goodsName"), "Sale pending"] for p in STATE["products"]
                    if p.get("goodsPgList[0].pgGoodsKey") == form.get("pgGoodsKey") and p.get("goodsAppGroupCode") == form.get("goodsAppGroupCode")]
            return self._send(rows_html(rows))
        if path == "/MobileLimitAdmin/purchase/goodsgroup/new":
            STATE["limits"].append({"guid": str(uuid.uuid4()).upper(), **form})
            return self._send("", 303, "/MobileLimitAdmin/purchase/goodsgroup")
        if path == "/MobileLimitAdmin/purchase/goodsgroup":
            rows = [[lim["guid"], lim.get("limitName"), "Purchase Limit", "Account", "x"] for lim in STATE["limits"]
                    if form.get("limitName", "") in lim.get("limitName", "")]
            return self._send(rows_html(rows))
        return self._send("")


def main() -> int:
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    auto = {"nc_base_url": f"http://127.0.0.1:{srv.server_address[1]}"}
    plan = {"product_key": "web.item153", "name": "Seal Growth Package", "description": "Seal Growth Package",
            "store_product_key": "com.ncv.l2m.web.item153", "price_usd": 20, "reputation_score": 20,
            "app_group": "l2msa", "app_group_label": "NCV-Lineage2M",
            "items": [{"excel_name": "Pa'agrio Seal Chest", "item_id": 195, "item_name": "Pa'agrio's Seal Chest (Bound)", "quantity": 6},
                      {"excel_name": "Diamond", "item_id": 2, "item_name": "Diamonds", "quantity": 300}],
            "limit": nc_setup.parse_limit("2 / Account / Weekly")}
    long_name = "Einhasad's Tshirt Selection Chest (Bound)"  # 41 ký tự -> trên tool lưu 40
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        ctx = browser.new_context()
        ctx.on("page", lambda pg: pg.on("dialog", lambda d: d.accept()))
        look = nb.item_lookup(ctx, auto, [long_name, "Royal Coin", "Fancy Class Card (11 Times) (Bound)"], "l2msa", "NCV-Lineage2M")
        dump = nb.dump_items(ctx, auto, "l2msa", "NCV-Lineage2M")
        goods = nb.create_goods(ctx, plan, auto, mode="auto")
        lim = nb.create_limit(ctx, plan, goods["goods_id"] or "0", auto, mode="auto") if goods.get("goods_id") else {}
        browser.close()
    srv.shutdown()
    prod = STATE["products"][0] if STATE["products"] else {}
    limit = STATE["limits"][0] if STATE["limits"] else {}
    qty = {prod.get(f"itemList[{i}].itemId"): prod.get(f"itemList[{i}].itemQuantity") for i in range(1, 4)}
    cands = nc_setup.lookup_candidates(look[long_name]["rows"])
    fancy = [c for c in nc_setup.lookup_candidates(look["Fancy Class Card (11 Times) (Bound)"]["rows"])]
    checks = {
        "tên 41 ký tự vẫn tra ra ID 217 (query cắt 40)": [c["item_id"] for c in cands] == [217],
        "không lấy item của jmsa": look["Royal Coin"]["rows"] == [],
        "tải đủ item l2msa qua nhiều trang (100/trang)": len(dump["rows"]) == 155,
        "ứng viên Fancy: 83 'Wrong' bị loại khi xếp hạng": [c["item_id"] for c in nc_setup.rank_tool_items(
            "Fancy Class Card (11 Times) (Bound)", fancy, blocked={83: ""})][:1] == [79],
        "đăng ký product thành công + tìm lại Product #": goods.get("submitted") and goods.get("goods_id") == "901",
        "app group form = l2msa (không phải jmsa mặc định)": prod.get("goodsAppGroupCode") == "l2msa",
        "tên ×3": prod.get("goodsName") == prod.get("goodsDisplayName") == "Seal Growth Package" and prod.get("goodsDisplayDescription") == "Seal Growth Package",
        "base price Cash 20 (dòng thật, không phải template)": prod.get("goodsBasicPricePolicyList[1].currencyGroupId") == "1" and prod.get("goodsBasicPricePolicyList[1].goodsBasicPrice") == "20",
        "monetary price USD 20": prod.get("goodsBasicCurrencyPricePolicyList[1].currencyCode") == "USD" and "20" in (prod.get("goodsBasicCurrencyPricePolicyList[1].goodsBasicCurrencyPrice") or ""),
        "PG VNG Store 25 + key + reputation": (prod.get("goodsPgList[0].pgId"), prod.get("goodsPgList[0].pgGoodsKey"), prod.get("goodsPgList[0].paymentReputationScore")) == ("25", "com.ncv.l2m.web.item153", "20"),
        "delivery confirm = true": prod.get("isDeliveryConfirmation") == "true",
        "items 195×6, 2×300": qty.get("195") == "6" and qty.get("2") == "300",
        "không có lỗi / trường thiếu": goods.get("missing") == [],
        "limit: tạo + lấy GUID": lim.get("submitted") and len(lim.get("limit_id") or "") == 36,
        "limit: Account / Week / 1 / amount 2 / score 0 / Monday": (limit.get("limitUserType"), limit.get("limitDurationUnitType"), limit.get("limitDuration"),
                                                                     limit.get("limitQuantity"), limit.get("limitScore"), limit.get("limitBaseDayOfWeek")) == ("3", "5", "1", "2", "0", "2"),
        "limit: product 901 weight 1": (limit.get("goodsList[0].goodsId"), limit.get("goodsList[0].quantityWeight")) == ("901", "1"),
    }
    for k, ok in checks.items():
        print(("PASS " if ok else "FAIL ") + k)
    if not all(checks.values()):
        print("product:", {k: v for k, v in prod.items() if "List" in k or k.startswith("goods")})
        print("limit:", limit)
        print("goods result:", goods, "\nlimit result:", lim)
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
