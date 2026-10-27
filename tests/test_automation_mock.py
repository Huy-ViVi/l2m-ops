"""Test phần điền form trên một trang GIẢ LẬP form NC tool (Edge headless, không truy cập mạng).

    python tests/test_automation_mock.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("L2M_DATA_DIR", tempfile.mkdtemp(prefix="l2m-test-"))  # không đụng data/ thật hay CSDL chung

from playwright.sync_api import sync_playwright  # noqa: E402

from automation import nc_billing as nb  # noqa: E402
from automation.browser import KV_JS, TABLE_JS  # noqa: E402

FORM = """
<html><body>
<select id="appGroup"><option value="">--</option><option value="l2mkr">KR</option><option value="l2msa">NCV-Lineage2M (l2msa)</option></select>
<table>
<tr><th>Product name(admin)</th><td><input name="AdminName"></td></tr>
<tr><th>Product name(customer)</th><td><input name="CustomerName"></td></tr>
<tr><th>Product description</th><td><textarea name="Description"></textarea></td></tr>
<tr><th>Store Product Key</th><td><select name="PgCode" style="display:none"><option value="0">Select</option><option value="25">VNG Store</option></select><span class="select2">Select</span>
  <input name="StoreProductKey"></td></tr>
<tr><th>Payment Reputation Score</th><td><input name="Score"></td></tr>
<tr><th>Base price</th><td><input name="BasePrice"></td></tr>
<tr><th>Monetary base price</th><td><select name="Cur"><option>USD</option></select><input name="MonetaryPrice"></td></tr>
<tr><th>Purchase type</th><td><label><input type="radio" name="PurchaseType" value="1">General purchase</label><label><input type="radio" name="PurchaseType" value="2">Subscription</label></td></tr>
<tr><th>Need to delivery confirm</th><td><input type="radio" id="dc1" name="NeedDeliveryConfirm" value="true"><label for="dc1">Required</label>
  <input type="radio" id="dc0" name="NeedDeliveryConfirm" value="false" checked><label for="dc0">Not Required</label></td></tr>
</table>
<table id="items"><thead><tr><th>Item</th><th>Quantity</th></tr></thead><tbody>
<tr style="display:none"><td>template</td><td><input name="itemList[x].itemQuantity" class="itemQuantity"></td></tr>
</tbody></table>
<script>
window.clicked = [];
document.querySelectorAll('input[type=radio]').forEach(r => r.addEventListener('click', () => window.clicked.push(r.name + '=' + r.value)));
window.$ = function(){}; window.$.fn = {
  addGoodsItem: function(id, grp, name, type) {
    const tr = document.createElement('tr');
    tr.innerHTML = '<td>' + id + ' ' + name + '</td><td><input name="itemList[' + id + '].itemQuantity" class="itemQuantity"></td>';
    document.querySelector('#items tbody').appendChild(tr);
  }
};
</script>
</body></html>
"""


def main() -> int:
    plan = {"name": "Seal Growth Package", "description": "Seal Growth Package", "store_product_key": "com.ncv.l2m.web.item153",
            "reputation_score": 19.99, "price_usd": 19.99,
            "items": [{"item_id": 195, "item_name": "Pa'agrio's Seal Chest (Bound)", "quantity": 6},
                      {"item_id": 2, "item_name": "Diamonds", "quantity": 300}]}
    fields = nb.load_fields()["goods_new"]
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page()
        page.set_content(FORM)
        nb._select_app_group(page, "l2msa")
        values = {
            "admin_name": plan["name"], "customer_name": plan["name"], "description": plan["description"],
            "store_pg": "VNG Store", "store_key": plan["store_product_key"], "reputation_score": plan["reputation_score"],
            "base_price_cash": plan["price_usd"], "monetary_base_price": plan["price_usd"],
            "purchase_type": "General purchase", "delivery_confirm": "Required",
        }
        filled, missing = nb._fill_all(page, fields, values)
        for it in plan["items"]:
            page.evaluate("([id, grp, name, type]) => window.$.fn.addGoodsItem(id, grp, name, type)",
                          [it["item_id"], "l2msa", it["item_name"], nb.ITEM_TYPE_GAME])
            assert page.evaluate(nb.MARK_LAST_JS, ["quantity", "qty"])
            page.locator('[data-l2m-mark="qty"]').fill(str(it["quantity"]))
        got = page.evaluate("""() => Object.fromEntries([...document.querySelectorAll('input:not([type=radio]), select, textarea')]
                              .filter(e => e.name).map(e => [e.name, e.value]))""")
        radios = page.evaluate("() => Object.fromEntries([...document.querySelectorAll('input[type=radio]:checked')].map(r => [r.name, r.value]))")
        clicked = page.evaluate("() => window.clicked")
        checks = {
            "app group": page.locator("#appGroup").input_value() == "l2msa",
            "admin name": got["AdminName"] == plan["name"],
            "customer name": got["CustomerName"] == plan["name"],
            "description": got["Description"] == plan["name"],
            "PG = VNG Store (25)": got["PgCode"] == "25",
            "store key": got["StoreProductKey"] == plan["store_product_key"],
            "score": got["Score"] == "19.99",
            "base price": got["BasePrice"] == "19.99",
            "monetary price": got["MonetaryPrice"] == "19.99",
            "purchase type radio": radios.get("PurchaseType") == "1",
            "delivery confirm = Required": radios.get("NeedDeliveryConfirm") == "true",
            "radio dùng click thật (kích hoạt handler)": "NeedDeliveryConfirm=true" in clicked,
            "template ẩn không bị đụng": got["itemList[x].itemQuantity"] == "",
            "qty item 195": got["itemList[195].itemQuantity"] == "6",
            "qty item 2": got["itemList[2].itemQuantity"] == "300",
            "không có trường bị miss": not missing,
        }
        dump = page.evaluate(nb.INSPECT_JS)
        mapping = nb.calibrate(dump, fields)
        checks["calibrate store_key"] = mapping.get("store_key") == {"selector": '[name="StoreProductKey"]'}
        checks["calibrate store_pg"] = mapping.get("store_pg") == {"selector": '[name="PgCode"]'}
        checks["calibrate delivery_confirm"] = mapping.get("delivery_confirm") == {"selector": "#dc1"}
        kv = page.evaluate(KV_JS)
        checks["KV_JS đọc th/td"] = "Store Product Key" in kv["kv"] and "Seal" not in kv["kv"].get("Product name(admin)", "x")
        rows = page.evaluate(TABLE_JS)
        checks["TABLE_JS đọc bảng item"] = any("195" in r.get("Item", "") for r in rows)
        browser.close()
    failed = [k for k, ok in checks.items() if not ok]
    for k, ok in checks.items():
        print(("PASS " if ok else "FAIL ") + k)
    print(f"filled={filled} missing={missing}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
